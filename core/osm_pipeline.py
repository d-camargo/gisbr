# -*- coding: utf-8 -*-
"""Pipeline OSM municipal: JSON → geometrias (links/nós).

Converte resultado Overpass em camadas QgsVectorLayer de segments de vias
e nós de extremidade, recortadas ao polígono municipal.
"""
import os
from pathlib import Path

from qgis.core import (QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
                       QgsPoint, QgsLineString, QgsFields, QgsProject)
from qgis.PyQt.QtCore import QVariant

from .connectors import osm


def _parse_osm_ways(payload):
    """Extrai ways com tag highway do JSON Overpass."""
    if not payload or "elements" not in payload:
        return []
    ways = [e for e in payload["elements"] if e.get("type") == "way" and "tags" in e and "highway" in e["tags"]]
    return ways


def _way_to_linestring(way_osm, nodes_dict):
    """Converte way OSM em QgsLineString (EPSG:4674 lon,lat)."""
    # ponytail: way já vem com node refs, precisa coordenadas do nodes_dict
    coords = []
    for node_id in way_osm.get("nodes", []):
        if node_id in nodes_dict:
            lon, lat = nodes_dict[node_id]
            coords.append(QgsPoint(lon, lat))
    return QgsLineString(coords) if len(coords) >= 2 else None


def _build_nodes_dict(payload):
    """Cria mapa node_id → (lon, lat) do JSON Overpass."""
    nodes_dict = {}
    if payload and "elements" in payload:
        for el in payload["elements"]:
            if el.get("type") == "node" and "lat" in el and "lon" in el:
                nodes_dict[el["id"]] = (el["lon"], el["lat"])
    return nodes_dict


def _create_links_layer(ways, nodes_dict, layer_name="osm_links_raw"):
    """Cria QgsVectorLayer de LineString a partir de ways."""
    fields = QgsFields()
    fields.append(QgsField("way_id", QVariant.LongLong))
    fields.append(QgsField("highway", QVariant.String))
    fields.append(QgsField("name", QVariant.String))
    fields.append(QgsField("oneway", QVariant.String))
    
    layer = QgsVectorLayer(f"LineString?crs=EPSG:4674&field=way_id:long&field=highway:string&field=name:string&field=oneway:string", layer_name, "memory")
    layer.startEditing()
    
    for way in ways:
        geom = _way_to_linestring(way, nodes_dict)
        if geom is None:
            continue
        feat = QgsFeature(fields)
        feat.setGeometry(QgsGeometry(geom))
        feat["way_id"] = way.get("id", 0)
        feat["highway"] = way.get("tags", {}).get("highway", "")
        feat["name"] = way.get("tags", {}).get("name", "")
        feat["oneway"] = way.get("tags", {}).get("oneway", "no")
        layer.addFeature(feat)
    
    layer.commitChanges()
    return layer


def _extract_nodes_from_layer(layer):
    """Extrai pontos de extremidade de LineStringLayer, deduplica."""
    nodes_set = set()
    for feat in layer.getFeatures():
        geom = feat.geometry()
        if geom and geom.type() == 1:  # LineString
            coord_list = geom.asPolyline()
            if coord_list:
                nodes_set.add((coord_list[0].x(), coord_list[0].y()))
                if len(coord_list) > 1:
                    nodes_set.add((coord_list[-1].x(), coord_list[-1].y()))
    return list(nodes_set)


def _create_nodes_layer(nodes_set, layer_name="osm_nodes"):
    """Cria QgsVectorLayer de Points a partir de conjuto (lon,lat)."""
    layer = QgsVectorLayer(f"Point?crs=EPSG:4674&field=node_id:long&field=x:double&field=y:double", layer_name, "memory")
    layer.startEditing()
    
    fields = QgsFields()
    fields.append(QgsField("node_id", QVariant.LongLong))
    fields.append(QgsField("x", QVariant.Double))
    fields.append(QgsField("y", QVariant.Double))
    
    for i, (lon, lat) in enumerate(sorted(nodes_set)):
        feat = QgsFeature(fields)
        feat.setGeometry(QgsGeometry(QgsPoint(lon, lat)))
        feat["node_id"] = i
        feat["x"] = lon
        feat["y"] = lat
        layer.addFeature(feat)
    
    layer.commitChanges()
    return layer


def _recorta_poligono(layer, poligono, layer_name):
    """Recorta layer pelo polígono (nativo:clip)."""
    import processing
    try:
        out = processing.run("native:clip", {
            "INPUT": layer, "OVERLAY": poligono, "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]
        if isinstance(out, str):
            return QgsVectorLayer(out, layer_name, "ogr")
        return out
    except Exception:
        return None


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
    """Constrói camadas de links/nós OSM do município."""
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

    # Extrair ways e nós
    ways = _parse_osm_ways(payload)
    nodes_dict = _build_nodes_dict(payload)
    log(f"OSM: {len(ways)} ways encontrados, {len(nodes_dict)} nós")

    # Criar camada raw
    osm_links_raw = _create_links_layer(ways, nodes_dict, "osm_links_raw")
    if osm_links_raw.featureCount() == 0:
        log("OSM: nenhum way com highway encontrado no bbox")
        return {"raw_cache": str(cache_path), "layers": {"osm_links_raw": None, "osm_links": None, "osm_nodes": None},
                "metadata": {"code_muni": str(code_muni), "nome_muni": nome_muni, "bbox": bbox, "municipio_layer": municipio.name()}}

    log(f"OSM: {osm_links_raw.featureCount()} links no bbox")

    # Recortar pelo polígono
    osm_links = _recorta_poligono(osm_links_raw, municipio, "osm_links")
    if osm_links is None or not osm_links.isValid():
        log("OSM: falha ao recortar pelo polígono municipal")
        return {"raw_cache": str(cache_path), "layers": {"osm_links_raw": osm_links_raw, "osm_links": None, "osm_nodes": None},
                "metadata": {"code_muni": str(code_muni), "nome_muni": nome_muni, "bbox": bbox, "municipio_layer": municipio.name()}}

    log(f"OSM: {osm_links.featureCount()} links dentro do município")

    # Gerar nós de extremidade
    nodes_set = _extract_nodes_from_layer(osm_links)
    osm_nodes = _create_nodes_layer(nodes_set, "osm_nodes")
    log(f"OSM: {osm_nodes.featureCount()} nós de extremidade (deduplicados)")

    return {
        "raw_cache": str(cache_path),
        "layers": {"osm_links_raw": osm_links_raw, "osm_links": osm_links, "osm_nodes": osm_nodes},
        "metadata": {
            "code_muni": str(code_muni),
            "nome_muni": nome_muni,
            "bbox": bbox,
            "municipio_layer": municipio.name(),
            "links_raw": osm_links_raw.featureCount(),
            "links_clipped": osm_links.featureCount(),
            "nodes": osm_nodes.featureCount(),
        },
    }
