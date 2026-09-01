# -*- coding: utf-8 -*-
"""Conector OSM/Overpass do diagnostico.

Scaffold minimo para consultas Overpass sem dependencias externas.
"""
import json
from pathlib import Path
import re

from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply

from ..ssl_support import configure_request

_OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
_OVERPASS_URL = _OVERPASS_ENDPOINTS[0]
_UA = "GisBR-QGIS/0.3 (diagnostico Plano Diretor)"
_OVERPASS_TIMEOUT = 180


class OverpassError(Exception):
    pass


def _validate_timeout(timeout):
    try:
        t = int(timeout)
        if t <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Timeout deve ser um inteiro positivo.")
    return max(10, min(600, t))


def _validar_payload(raw_bytes, host):
    if isinstance(raw_bytes, bytes):
        raw_str = raw_bytes.decode("utf-8", errors="replace")
    else:
        raw_str = str(raw_bytes)

    stripped = raw_str.strip()
    if stripped.startswith("<"):
        p_matches = re.findall(r'<p>(.*?)</p>', stripped, flags=re.DOTALL | re.IGNORECASE)
        texto = None
        for p in p_matches:
            cleaned = re.sub(r'<.*?>', '', p).strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)
            if "error" in cleaned.lower():
                texto = cleaned
                break
        if not texto:
            if p_matches:
                texto = re.sub(r'\s+', ' ', re.sub(r'<.*?>', '', p_matches[0])).strip()
            else:
                texto = re.sub(r'\s+', ' ', re.sub(r'<.*?>', '', stripped[:200])).strip()
        raise OverpassError("Overpass (host: {}): erro do servidor — {}".format(host, texto))

    try:
        payload = json.loads(raw_str)
    except (json.JSONDecodeError, ValueError) as e:
        snippet = raw_str[:200]
        raise OverpassError(
            "Erro ao decodificar JSON do Overpass: {}. Resposta crua (snippet): {}".format(e, snippet)
        )

    if not isinstance(payload, dict):
        raise OverpassError("resposta sem 'elements'")

    remark = payload.get("remark")
    if isinstance(remark, str) and remark:
        remark_lower = remark.lower()
        if any(term in remark_lower for term in ["error", "runtime error", "out of memory"]):
            raise OverpassError(remark)

    if "elements" not in payload:
        raise OverpassError("resposta sem 'elements'")

    return payload


def build_query(bbox, timeout=_OVERPASS_TIMEOUT):
    """Monta uma query Overpass QL para vias e nos associados."""
    t = _validate_timeout(timeout)
    minx, miny, maxx, maxy = bbox
    bbox_txt = "{},{},{},{}".format(miny, minx, maxy, maxx)
    return (
        "[out:json][timeout:{timeout}];"
        "(way[\"highway\"]({bbox});>;);"
        "out body;"
    ).format(timeout=t, bbox=bbox_txt)


def _post_overpass(query, timeout=_OVERPASS_TIMEOUT):
    """Envia requisição POST para a API do Overpass.

    O timeout do socket/transferência é definido como ms = (t + 60) * 1000 ms,
    maior do que o timeout da query (t segundos), para acomodar o tempo que a
    requisição pode passar na fila do Overpass antes da execução iniciar.
    O timeout padrão do QgsNetworkAccessManager (NAM do QGIS = 60000 ms)
    causaria cancelamento prematuro em servidores sob alta carga.
    """
    t = _validate_timeout(timeout)
    ms = (t + 60) * 1000
    erros = []

    for url_str in _OVERPASS_ENDPOINTS:
        url_obj = QUrl(url_str)
        host = url_obj.host()
        req = QNetworkRequest(url_obj)
        if hasattr(QNetworkRequest.Attribute, "TransferTimeoutAttribute"):
            req.setAttribute(QNetworkRequest.Attribute.TransferTimeoutAttribute, ms)
        req.setRawHeader(b"User-Agent", _UA.encode("utf-8"))
        req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/x-www-form-urlencoded")
        configure_request(req)
        payload = "data={}".format(QUrl.toPercentEncoding(query).data().decode("utf-8"))
        blocking = QgsBlockingNetworkRequest()
        if hasattr(blocking, "setTimeout"):
            blocking.setTimeout(ms)
        res = blocking.post(req, payload.encode("utf-8"), True)
        reply = blocking.reply()

        err_msg = None
        if res != QgsBlockingNetworkRequest.ErrorCode.NoError:
            err_msg = blocking.errorMessage()
            if reply:
                err_msg = err_msg or reply.errorString()
            err_msg = err_msg or "Erro de rede no Overpass"
        elif reply and reply.error() != QNetworkReply.NetworkError.NoError:
            err_msg = reply.errorString() or "Erro de rede do Overpass"

        if err_msg:
            erros.append((host, err_msg))
            continue

        data = bytes(reply.content()) if reply else b""
        if not data:
            erros.append((host, "resposta vazia do servidor"))
            continue

        return data, host

    msg_falhas = "; ".join("{} ({})".format(h, m) for h, m in erros)
    raise OverpassError("Overpass falhou em todos os endpoints: {}".format(msg_falhas))


def _fetch_json(query, timeout, cache_path=None, feedback=None):
    """POST no Overpass com a query dada; em falha, cai para o cache local."""
    t = _validate_timeout(timeout)
    try:
        data, host = _post_overpass(query, timeout=t)
        return _validar_payload(data, host)
    except OverpassError:
        if cache_path:
            path = Path(cache_path)
            if path.exists():
                try:
                    payload = load_overpass_cache(cache_path)
                    if payload is not None:
                        if feedback is not None:
                            feedback.pushWarning(
                                "Aviso: Falha na consulta do Overpass. Usando dados antigos do cache local: {}".format(cache_path)
                            )
                        return payload
                except (OSError, ValueError) as cache_exc:
                    if feedback is not None:
                        feedback.pushWarning(
                            "Aviso: o cache local do Overpass existe mas nao pode ser lido "
                            "({}): {}".format(cache_path, cache_exc)
                        )
        raise


def overpass_cache_key(code_muni, bbox, filters=None):
    payload = {
        "code_muni": str(code_muni),
        "bbox": list(bbox),
        "filters": filters or {},
    }
    return "osm_overpass_{}.json".format(
        json.dumps(payload, sort_keys=True, separators=(",", ":"))
    )


def save_overpass_cache(payload, cache_path):
    if not isinstance(payload, dict) or "elements" not in payload:
        raise ValueError("Payload invalido para cache: falta 'elements'.")

    remark = payload.get("remark")
    if isinstance(remark, str) and remark:
        remark_lower = remark.lower()
        if any(term in remark_lower for term in ["error", "runtime error", "out of memory"]):
            raise ValueError("Payload invalido para cache: remark de erro ({}).".format(remark))

    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def load_overpass_cache(cache_path):
    path = Path(cache_path)
    if not path.exists():
        return None
    try:
        raw_text = path.read_text(encoding="utf-8")
        return _validar_payload(raw_text, host="cache")
    except (OverpassError, OSError, ValueError):
        # Payload que nao passa pelo portao (D2/D3) ou arquivo ilegivel:
        # trata-se como cache inexistente — quem chama decide (e loga) o aviso.
        return None


def fetch_overpass_json(bbox, timeout=_OVERPASS_TIMEOUT, cache_path=None, feedback=None):
    """Consulta o Overpass e devolve o JSON parseado."""
    t = _validate_timeout(timeout)
    query = build_query(bbox, timeout=t)
    return _fetch_json(query, timeout=t, cache_path=cache_path, feedback=feedback)


def fetch_poi_json(bbox, timeout=_OVERPASS_TIMEOUT, cache_path=None, feedback=None):
    """Consulta POIs no Overpass (predicado osm2gmns) e devolve o JSON parseado.

    Gêmeo de `fetch_overpass_json`: mesma query de rede, mesmo tratamento de
    `OverpassError` com fallback para o cache local.
    """
    from .. import poi_parser

    t = _validate_timeout(timeout)
    query = poi_parser.build_poi_query(bbox, timeout=t)
    return _fetch_json(query, timeout=t, cache_path=cache_path, feedback=feedback)

