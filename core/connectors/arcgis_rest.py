# -*- coding: utf-8 -*-
"""Conector ArcGIS REST (FeatureServer/MapServer) do diagnostico.

Consulta a operacao /query da layer (f=geojson) pela pilha de rede do QGIS;
filtro por `where` (campo municipal) OU por bbox (esriGeometryEnvelope).
Retorna QgsVectorLayer (so MONTA; gravar/adicionar e do motor).
"""
from datetime import datetime
import tempfile
import urllib.parse

from qgis.core import QgsVectorLayer, QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

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


def fetch_layer(endpoint, layer_id, layer_name, srs="EPSG:4674", where=None, bbox=None):
    url = build_url(endpoint, layer_id, srs=srs, where=where, bbox=bbox)
    erro = None
    try:
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent", _UA.encode("utf-8"))
        blocking = QgsBlockingNetworkRequest()
        blocking.get(req, True)
        reply = blocking.reply()
        data = bytes(reply.content())
        if data:
            layer = _layer_from_geojson_bytes(data, layer_name)
            if layer.isValid():
                return _stamp(layer, "ArcGIS REST (GeoJSON)")
            erro = "GeoJSON recebido, mas o GDAL nao abriu a camada."
        else:
            erro = reply.errorString() or "resposta vazia"
    except Exception as exc:
        erro = "{}: {}".format(type(exc).__name__, exc)
    layer = QgsVectorLayer("/vsicurl/" + url, layer_name, "ogr")
    if layer.isValid():
        return _stamp(layer, "ArcGIS REST (GeoJSON/vsicurl)")
    return _invalid(layer_name, "Falha ArcGIS ({}/{}). {}".format(endpoint, layer_id, erro or ""))
