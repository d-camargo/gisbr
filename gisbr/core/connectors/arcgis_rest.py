# -*- coding: utf-8 -*-
"""Conector ArcGIS REST (FeatureServer/MapServer) do diagnostico.

Consulta a operacao /query da layer (f=geojson) pela pilha de rede do QGIS;
filtro por `where` (campo municipal) OU por bbox (esriGeometryEnvelope).
Retorna QgsVectorLayer (so MONTA; gravar/adicionar e do motor).
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
    """Detecta se a resposta HTTP 200 do ArcGIS REST contem payload de erro (JSON error ou HTML).
    Retorna a mensagem de erro formatada, ou None se nao for erro.
    """
    if not data:
        return None

    stripped = data.strip()
    if stripped.startswith(b"{") and stripped.endswith(b"}"):
        try:
            obj = json.loads(data.decode("utf-8", errors="replace"))
            if isinstance(obj, dict) and "error" in obj:
                err = obj["error"]
                if isinstance(err, dict):
                    msg = err.get("message") or str(err)
                    details = err.get("details")
                    if details and isinstance(details, list):
                        msg = "{}: {}".format(msg, details[0])
                    codigo = err.get("code")
                    if codigo is not None:
                        msg = "codigo {}: {}".format(codigo, msg)
                else:
                    msg = str(err)
                return "Erro ArcGIS REST (HTTP 200): {}".format(msg)
        except (ValueError, TypeError):
            pass

    if stripped.lower().startswith((b"<html", b"<!doctype html")):
        m_title = re.search(rb'<title>(.*?)</title>', data, re.DOTALL | re.IGNORECASE)
        if m_title:
            title = m_title.group(1).decode("utf-8", errors="replace").strip()
            return "Pagina de erro HTML ({})".format(title)
        return "Resposta HTML recebida em vez de GeoJSON."

    return None


def _get_bytes(url):
    req = QNetworkRequest(QUrl(url))
    req.setRawHeader(b"User-Agent", _UA.encode("utf-8"))
    configure_request(req)
    blocking = QgsBlockingNetworkRequest()
    blocking.get(req, True)
    return bytes(blocking.reply().content())


_MAX_RECORD_COUNT = {}


def _max_record_count(endpoint, layer_id, feedback=None):
    """maxRecordCount da layer (consulta ?f=json), memoizado por URL.

    Devolve None quando o servico nao informa — ai nao da pra inferir corte.
    """
    url = "{}/{}?f=json".format(endpoint.rstrip("/"), layer_id)
    if url in _MAX_RECORD_COUNT:
        return _MAX_RECORD_COUNT[url]
    limite = None
    try:
        data = _get_bytes(url)
        if data:
            limite = json.loads(data.decode("utf-8", "replace")).get("maxRecordCount")
            limite = int(limite) if limite else None
    except (ValueError, TypeError, AttributeError, OSError) as exc:
        if feedback is not None:
            feedback.pushInfo(
                "Aviso: nao consegui ler o maxRecordCount de {} ({}: {}); "
                "sem checagem de truncamento.".format(url, type(exc).__name__, exc)
            )
    _MAX_RECORD_COUNT[url] = limite
    return limite


def _checa_truncamento(layer, endpoint, layer_id, feedback):
    """Sinaliza corte no maxRecordCount (f=geojson nao traz exceededTransferLimit).

    Como o servico nao diz quantas feicoes casaram, o total fica em aberto.
    """
    limite = _max_record_count(endpoint, layer_id, feedback)
    if not limite:
        return
    recebidas = layer.featureCount()
    if recebidas < limite:
        return
    layer.setCustomProperty("truncado", "{} de mais (maxRecordCount={})".format(recebidas, limite))
    if feedback is not None:
        feedback.pushWarning(
            "Aviso: '{}' bateu no limite do servico ({} feicoes, maxRecordCount={}); "
            "o resultado pode estar truncado.".format(layer.name(), recebidas, limite)
        )


def build_url(endpoint, layer_id, srs="EPSG:4674", where=None, bbox=None):
    wkid = srs.split(":")[-1]
    params = {"outFields": "*", "f": "geojson", "outSR": wkid,
              "where": where or "1=1"}
    if bbox is not None:
        minx, miny, maxx, maxy = bbox
        params["geometry"] = "{},{},{},{}".format(minx, miny, maxx, maxy)
        params["geometryType"] = "esriGeometryEnvelope"
        params["inSR"] = wkid
        params["spatialRel"] = "esriSpatialRelIntersects"
    base = "{}/{}/query".format(endpoint.rstrip("/"), layer_id)
    return base + "?" + urllib.parse.urlencode(params)


def fetch_layer(endpoint, layer_id, layer_name, srs="EPSG:4674", where=None,
                bbox=None, feedback=None):
    url = build_url(endpoint, layer_id, srs=srs, where=where, bbox=bbox)
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
                return _invalid(layer_name, "Falha ArcGIS ({}/{}, host: {}): {}".format(
                    endpoint, layer_id, QUrl(url).host(), msg_erro))
            layer = _layer_from_geojson_bytes(data, layer_name)
            if layer.isValid():
                _checa_truncamento(layer, endpoint, layer_id, feedback)
                return _stamp(layer, "ArcGIS REST (GeoJSON)")
            erro = "GeoJSON recebido, mas o GDAL nao abriu a camada."
        else:
            erro = reply.errorString() or "resposta vazia"
    except Exception as exc:
        erro = "{}: {}".format(type(exc).__name__, exc)
    layer = QgsVectorLayer("/vsicurl/" + url, layer_name, "ogr")
    if layer.isValid():
        return _stamp(layer, "ArcGIS REST (GeoJSON/vsicurl)")
    host = QUrl(url).host()
    return _invalid(layer_name, "Falha ArcGIS ({}/{}, host: {}): {}".format(endpoint, layer_id, host, erro or "resposta vazia/invalida"))
