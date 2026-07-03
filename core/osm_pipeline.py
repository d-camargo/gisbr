# -*- coding: utf-8 -*-
"""Scaffold de pipeline OSM municipal do diagnostico.

Ainda nao grava GeoPackage nem materializa topologia completa.
"""
import os
from pathlib import Path

from qgis.core import QgsVectorLayer

from .connectors import osm


def _resolve_layer(out, layer_name):
    if isinstance(out, str):
        return QgsVectorLayer(out, layer_name, "ogr")
    return out


def _municipio_poligono(code_muni, nome_muni=None):
    import processing
    out = processing.run("gisbr:read_municipality", {
        "CODE": str(code_muni),
        "SIMPLIFIED": True,
        "OUTPUT": "TEMPORARY_OUTPUT",
    })["OUTPUT"]
    layer = _resolve_layer(out, "municipio")
    if layer is None or not layer.isValid():
        return None
    return layer


def _bbox_da_camada(layer):
    extent = layer.extent()
    return (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())


def build_osm_municipal_network(code_muni, nome_muni, gpkg_path, force=False, feedback=None):
    """Scaffold executavel da rede OSM municipal."""
    def log(msg):
        if feedback is not None:
            feedback.pushInfo(msg)

    municipio = _municipio_poligono(code_muni, nome_muni)
    if municipio is None:
        return {"raw_cache": None, "layers": {"osm_links_raw": None, "osm_links": None, "osm_nodes": None},
                "metadata": {"code_muni": str(code_muni), "nome_muni": nome_muni, "erro": "nao foi possivel resolver o municipio"}}

    bbox = _bbox_da_camada(municipio)
    cache_dir = Path(os.path.dirname(gpkg_path) or ".")
    cache_path = cache_dir / "osm_overpass_{}.json".format(code_muni)
    payload = None
    if cache_path.exists() and not force:
        payload = osm.load_overpass_cache(cache_path)
        if payload is not None:
            log("OSM: cache reutilizado")
    if payload is None:
        log("OSM: consultando Overpass")
        payload = osm.fetch_overpass_json(bbox, timeout=180)
        osm.save_overpass_cache(payload, cache_path)

    return {
        "raw_cache": str(cache_path),
        "layers": {"osm_links_raw": None, "osm_links": None, "osm_nodes": None},
        "metadata": {
            "code_muni": str(code_muni),
            "nome_muni": nome_muni,
            "bbox": bbox,
            "municipio_layer": municipio.name(),
            "topologia": "pendente",
        },
    }
