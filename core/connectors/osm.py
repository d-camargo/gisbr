# -*- coding: utf-8 -*-
"""Conector OSM/Overpass do diagnostico.

Scaffold minimo para consultas Overpass sem dependencias externas.
"""
import json
from pathlib import Path

from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_UA = "GisBR-QGIS/0.3 (diagnostico Plano Diretor)"
_OVERPASS_TIMEOUT = 180


def build_query(bbox):
    """Monta uma query Overpass QL para vias e nos associados."""
    minx, miny, maxx, maxy = bbox
    bbox_txt = "{},{},{},{}".format(miny, minx, maxy, maxx)
    return (
        "[out:json][timeout:{timeout}];"
        "(way[\"highway\"]({bbox});>;);"
        "out body;"
    ).format(timeout=_OVERPASS_TIMEOUT, bbox=bbox_txt)


def _post_overpass(query, timeout=180):
    req = QNetworkRequest(QUrl(_OVERPASS_URL))
    req.setRawHeader(b"User-Agent", _UA.encode("utf-8"))
    req.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
    payload = "data={}".format(QUrl.toPercentEncoding(query).data().decode("utf-8"))
    blocking = QgsBlockingNetworkRequest()
    blocking.post(req, payload.encode("utf-8"), True)
    reply = blocking.reply()
    data = bytes(reply.content())
    if not data:
        raise RuntimeError(reply.errorString() or "resposta vazia do Overpass")
    return data


def fetch_overpass_json(bbox, timeout=180):
    """Consulta o Overpass e devolve o JSON parseado."""
    query = build_query(bbox)
    data = _post_overpass(query, timeout=timeout)
    return json.loads(data.decode("utf-8"))


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
