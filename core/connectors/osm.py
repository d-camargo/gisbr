# -*- coding: utf-8 -*-
"""Conector OSM/Overpass do diagnostico.

Scaffold minimo para consultas Overpass sem dependencias externas.
"""
import json
from pathlib import Path

from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
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
    t = _validate_timeout(timeout)
    req = QNetworkRequest(QUrl(_OVERPASS_URL))
    req.setRawHeader(b"User-Agent", _UA.encode("utf-8"))
    req.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
    payload = "data={}".format(QUrl.toPercentEncoding(query).data().decode("utf-8"))
    blocking = QgsBlockingNetworkRequest()
    res = blocking.post(req, payload.encode("utf-8"), True)
    reply = blocking.reply()
    if res != QgsBlockingNetworkRequest.NoError:
        err_msg = blocking.errorMessage()
        if reply:
            err_msg = err_msg or reply.errorString()
        raise OverpassError(err_msg or "Erro de rede no Overpass")
    if reply and reply.error() != QNetworkReply.NoError:
        raise OverpassError(reply.errorString() or "Erro de rede do Overpass")
    data = bytes(reply.content())
    if not data:
        raise OverpassError(reply.errorString() or "resposta vazia do Overpass")
    return data


def fetch_overpass_json(bbox, timeout=_OVERPASS_TIMEOUT, cache_path=None, feedback=None):
    """Consulta o Overpass e devolve o JSON parseado."""
    t = _validate_timeout(timeout)
    query = build_query(bbox, timeout=t)
    try:
        data = _post_overpass(query, timeout=t)
        raw_str = data.decode("utf-8")
        try:
            return json.loads(raw_str)
        except json.JSONDecodeError as e:
            snippet = raw_str[:200]
            raise OverpassError(
                "Erro ao decodificar JSON do Overpass: {}. Resposta crua (snippet): {}".format(e, snippet)
            )
    except OverpassError as e:
        if cache_path:
            path = Path(cache_path)
            if path.exists():
                try:
                    payload = load_overpass_cache(cache_path)
                    if payload is not None:
                        if feedback is not None:
                            feedback.pushInfo(
                                "Aviso: Falha na consulta do Overpass. Usando cache local: {}".format(cache_path)
                            )
                        return payload
                except Exception:
                    pass
        raise e


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
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def load_overpass_cache(cache_path):
    path = Path(cache_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
