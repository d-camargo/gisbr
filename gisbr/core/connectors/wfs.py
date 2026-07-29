# -*- coding: utf-8 -*-
"""Conector WFS do diagnostico.

Baixa feicoes de servicos WFS oficiais usando a pilha de rede do QGIS
(QgsBlockingNetworkRequest) — robusta a SSL/proxy do GeoServer (padrao
herdado do desafio-2). Saida GeoJSON (outputFormat application/json);
fallback GDAL /vsicurl/. Filtro por CQL_FILTER (campo municipal) OU bbox.

So MONTA a camada (QgsVectorLayer). Gravar no GeoPackage e adicionar ao
projeto e do motor (core/diagnostico.py, T-010).
"""
from datetime import datetime
import json
import re
import tempfile
import urllib.parse

from qgis.core import QgsVectorLayer, QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from ..ssl_support import configure_request

_UA = "GisBR-QGIS/0.2 (diagnostico Plano Diretor)"


def _stamp(layer, fonte):
    layer.setCustomProperty("data_extracao", datetime.now().strftime("%Y-%m-%d"))
    layer.setCustomProperty("fonte", fonte)
    return layer


def _invalid(layer_name, msg):
    layer = QgsVectorLayer("", layer_name, "ogr")
    layer.error_msg = msg
    return layer


def _layer_from_geojson_bytes(data, layer_name):
    tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    tmp.write(data)
    tmp.close()
    return QgsVectorLayer(tmp.name, layer_name, "ogr")


def _detecta_erro_http_200(data):
    """Detecta se a resposta HTTP 200 contem payload de erro (XML Exception, JSON error, HTML).
    Retorna a mensagem de erro formatada, ou None se nao for erro.
    """
    if not data:
        return None

    # 1. XML Exception Report (GeoServer / MapServer / OGC WFS)
    if b"<ServiceException" in data or b"<ows:Exception" in data or b"<ExceptionReport" in data:
        m_txt = re.search(rb'<ows:ExceptionText>(.*?)</ows:ExceptionText>', data, re.DOTALL | re.IGNORECASE)
        if m_txt:
            msg = m_txt.group(1).decode("utf-8", errors="replace").strip()
            return "Excecao WFS (OGC): {}".format(msg)

        m_sec = re.search(rb'<ServiceException[\s>][^>]*>(.*?)</ServiceException>', data, re.DOTALL | re.IGNORECASE)
        if m_sec:
            msg = m_sec.group(1).decode("utf-8", errors="replace").strip()
            return "Excecao WFS (ServiceException): {}".format(msg)

        m_code = re.search(rb'code="([^"]+)"', data)
        if m_code:
            code = m_code.group(1).decode("utf-8", errors="replace").strip()
            return "Excecao WFS (codigo: {})".format(code)

        return "Excecao WFS em formato XML recebida do servidor."

    # 2. JSON error (GeoServer / WFS JSON exception)
    stripped = data.strip()
    if stripped.startswith(b"{") and stripped.endswith(b"}"):
        try:
            obj = json.loads(data.decode("utf-8", errors="replace"))
            if isinstance(obj, dict):
                if "exceptions" in obj and isinstance(obj["exceptions"], list) and obj["exceptions"]:
                    exc_item = obj["exceptions"][0]
                    if isinstance(exc_item, dict):
                        text = exc_item.get("text") or exc_item.get("code") or str(exc_item)
                        return "Excecao WFS (JSON): {}".format(text)
                    return "Excecao WFS (JSON): {}".format(exc_item)
                if "error" in obj:
                    err = obj["error"]
                    if isinstance(err, dict):
                        msg = err.get("message") or err.get("code") or str(err)
                    else:
                        msg = str(err)
                    return "Erro no servico (JSON): {}".format(msg)
        except (ValueError, TypeError):
            pass

    # 3. HTML Error page
    if stripped.lower().startswith((b"<html", b"<!doctype html")):
        m_title = re.search(rb'<title>(.*?)</title>', data, re.DOTALL | re.IGNORECASE)
        if m_title:
            title = m_title.group(1).decode("utf-8", errors="replace").strip()
            return "Pagina de erro HTML ({})".format(title)
        return "Resposta HTML recebida em vez de GeoJSON."

    return None


_RE_MATCHED = re.compile(rb'"numberMatched"\s*:\s*"?(\d+)')
_RE_RETURNED = re.compile(rb'"numberReturned"\s*:\s*"?(\d+)')
_RE_TOTAL = re.compile(rb'"totalFeatures"\s*:\s*"?(\d+)')


def _int_do_geojson(regex, data):
    achado = regex.search(data)
    return int(achado.group(1)) if achado else None


def _marca_truncado(layer, recebidas, total, feedback):
    layer.setCustomProperty("truncado", "{} de {}".format(recebidas, total))
    if feedback is not None:
        feedback.pushWarning(
            "Aviso: '{}' veio truncada pelo servico: {} de {} feicoes.".format(
                layer.name(), recebidas, total)
        )


def _checa_truncamento(layer, data, feedback):
    """Sinaliza quando o WFS devolveu menos feicoes do que casou com o filtro.

    GeoServer emite numberMatched/numberReturned (WFS 2.0) ou totalFeatures
    (WFS 1.x) no GeoJSON; sem esses campos nao da pra saber e nada e marcado.
    """
    total = _int_do_geojson(_RE_MATCHED, data)
    if total is None:
        total = _int_do_geojson(_RE_TOTAL, data)
    if total is None:
        return
    recebidas = _int_do_geojson(_RE_RETURNED, data)
    if recebidas is None:
        recebidas = layer.featureCount()
    if recebidas < 0 or recebidas >= total:
        return
    _marca_truncado(layer, recebidas, total, feedback)


def build_url(endpoint, type_name, srs="EPSG:4674",
              output_format="application/json", cql_filter=None, bbox=None,
              version="2.0.0"):
    """Monta a URL GetFeature. Use cql_filter OU bbox (cql tem prioridade).

    bbox: tupla (minx, miny, maxx, maxy) em graus EPSG:4674.
    ATENCAO (a validar no QGIS): em WFS 2.0.0 a ordem de eixo pode ser
    lat,lon; usamos a forma curta 'EPSG:4674' (lon,lat na maioria dos
    GeoServer). Se algum servico desalinhar, inverter para miny,minx,maxy,maxx.
    """
    params = {
        "service": "WFS",
        "version": version,
        "request": "GetFeature",
        "typeNames": type_name,
        "srsName": srs,
        "outputFormat": output_format,
    }
    if cql_filter:
        params["CQL_FILTER"] = cql_filter
    elif bbox:
        minx, miny, maxx, maxy = bbox
        params["bbox"] = "{},{},{},{},{}".format(minx, miny, maxx, maxy, srs)
    sep = "&" if "?" in endpoint else "?"
    return endpoint + sep + urllib.parse.urlencode(params)


def fetch_layer(endpoint, type_name, layer_name, srs="EPSG:4674",
                output_format="application/json", cql_filter=None, bbox=None,
                version="2.0.0", feedback=None):
    """Retorna um QgsVectorLayer do WFS (filtrado), ou um layer invalido com
    .error_msg em caso de falha. NAO levanta excecao."""
    url = build_url(endpoint, type_name, srs=srs, output_format=output_format,
                    cql_filter=cql_filter, bbox=bbox, version=version)

    # 1) Pilha de rede do QGIS (respeita SSL/proxy do app)
    erro = None
    try:
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent", _UA.encode("utf-8"))
        configure_request(req)
        blocking = QgsBlockingNetworkRequest()
        blocking.get(req, True)
        reply = blocking.reply()
        data = bytes(reply.content())
        if data:
            msg_erro = _detecta_erro_http_200(data)
            if msg_erro:
                # o servidor respondeu; /vsicurl/ pediria a mesma URL e falharia igual
                return _invalid(layer_name, "Falha WFS ({}, host: {}): {}".format(
                    type_name, QUrl(url).host(), msg_erro))
            layer = _layer_from_geojson_bytes(data, layer_name)
            if layer.isValid():
                _checa_truncamento(layer, data, feedback)
                return _stamp(layer, "WFS GeoJSON")
            erro = "GeoJSON recebido, mas o GDAL nao abriu a camada."
        else:
            erro = reply.errorString() or "resposta vazia"
    except Exception as exc:
        erro = "{}: {}".format(type(exc).__name__, exc)

    # 2) Fallback GDAL /vsicurl/
    layer = QgsVectorLayer("/vsicurl/" + url, layer_name, "ogr")
    if layer.isValid():
        return _stamp(layer, "WFS GeoJSON/vsicurl")

    host = QUrl(url).host()
    return _invalid(layer_name, "Falha WFS ({}, host: {}): {}".format(type_name, host, erro or "resposta vazia/invalida"))
