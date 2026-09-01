# -*- coding: utf-8 -*-
"""Pipeline de POIs OSM municipal: Overpass → camadas de POI (pontos + áreas).

Gêmeo do `core/osm_pipeline.py` (vias) para Points of Interest, no predicado
do osm2gmns (D2). Diferenças de projeto em relação ao pipeline de vias:

- duas camadas com `poi_id` compartilhado (D4): `osm_pois_<code_muni>`
  (Point — a camada canônica, equivalente do poi.csv) e
  `osm_pois_area_<code_muni>` (Polygon — footprint de way/relation);
- área em m² por elipsoide GRS80 (SIRGAS 2000) via QgsDistanceArea (D9);
- recorte por CENTRÓIDE dentro do município, com geometry engine preparado —
  nunca `native:clip`, que cortaria a footprint e corromperia `area` (D6);
- as camadas retornadas são relidas do GeoPackage: atributo Python em
  QgsVectorLayer não persiste (docs/osm-municipal-pattern.md).
"""
import os
from pathlib import Path

from qgis.core import (QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
                       QgsPointXY, QgsFields, QgsDistanceArea)

from . import poi_parser, qgis_compat
from .connectors import osm
from .osm_pipeline import _municipio_poligono, _bbox_da_camada

_POI_FIELDS = [
    ("poi_id", "long"), ("osm_type", "string"), ("osm_id", "long"),
    ("name", "string"), ("building", "string"), ("amenity", "string"),
    ("way", "string"), ("poi_type", "string"), ("area", "double"),
    ("area_ft2", "double"), ("centroid_lon", "double"), ("centroid_lat", "double"),
]


def _uri(geometry_type, layer_name):
    campos = "".join("&field={}:{}".format(nome, tipo) for nome, tipo in _POI_FIELDS)
    return "{}?crs=EPSG:4674{}".format(geometry_type, campos)


def _fields():
    fields = QgsFields()
    for nome, tipo in _POI_FIELDS:
        fields.append(QgsField(nome, qgis_compat.field_type(tipo)))
    return fields


def _medidor_area():
    d = QgsDistanceArea()
    d.setEllipsoid("GRS80")  # elipsoide do SIRGAS 2000 (D9)
    return d


def _geometria_municipio(municipio):
    geoms = [f.geometry() for f in municipio.getFeatures()
             if f.geometry() and not f.geometry().isEmpty()]
    if not geoms:
        return None
    if len(geoms) == 1:
        return geoms[0]
    return geoms[0].unaryUnion(geoms[1:])


def build_osm_municipal_pois(code_muni, nome_muni, gpkg_path, force=False, feedback=None):
    """Constrói as camadas de POIs OSM do município e grava no GeoPackage."""
    def log(msg):
        if feedback is not None:
            feedback.pushInfo(msg)

    vazio = {"raw_cache": None,
             "layers": {"osm_pois": None, "osm_pois_area": None}}

    municipio = _municipio_poligono(code_muni, nome_muni)
    if municipio is None:
        return dict(vazio, metadata={"code_muni": str(code_muni), "nome_muni": nome_muni,
                                     "erro": "nao foi possivel resolver o municipio"})

    mun_geom = _geometria_municipio(municipio)
    if mun_geom is None:
        return dict(vazio, metadata={"code_muni": str(code_muni), "nome_muni": nome_muni,
                                     "erro": "municipio sem geometria"})

    bbox = _bbox_da_camada(municipio)
    cache_dir = Path(os.path.dirname(gpkg_path) or ".")
    cache_path = cache_dir / "osm_poi_{}.json".format(code_muni)
    payload = None
    if cache_path.exists() and not force:
        payload = osm.load_overpass_cache(cache_path)
        if payload is not None:
            log("OSM POI: cache reutilizado")
    if payload is None:
        log("OSM POI: consultando Overpass")
        try:
            payload = osm.fetch_poi_json(bbox, timeout=180, cache_path=cache_path, feedback=feedback)
            osm.save_overpass_cache(payload, cache_path)
        except osm.OverpassError as e:
            log("Erro no Overpass: {}".format(e))
            return dict(vazio, metadata={"code_muni": str(code_muni), "nome_muni": nome_muni,
                                         "erro": str(e)})

    registros, descartadas = poi_parser.parse_pois(payload)
    if not registros:
        log("OSM POI: nenhum POI retornado pelo Overpass no bbox do municipio")
        return dict(vazio, metadata={"code_muni": str(code_muni), "nome_muni": nome_muni,
                                     "erro": "nenhum POI retornado pelo Overpass",
                                     "sem_pois": True, "bbox": bbox})

    # Filtro por centróide DENTRO do município (D6) — engine preparado: o loop
    # ingênuo de contains sobre ~10^5 POIs seria O(n) por chamada.
    engine = QgsGeometry.createGeometryEngine(mun_geom.constGet())
    engine.prepareGeometry()
    medidor = _medidor_area()

    base_meta = {"code_muni": str(code_muni), "nome_muni": nome_muni, "bbox": bbox,
                 "total_baixa": len(registros), "descartadas": descartadas}

    pois_layer = QgsVectorLayer(_uri("Point", "osm_pois"), "osm_pois", "memory")
    area_layer = QgsVectorLayer(_uri("Polygon", "osm_pois_area"), "osm_pois_area", "memory")
    campos = _fields()
    pois_layer.startEditing()
    area_layer.startEditing()

    por_tipo = {"node": 0, "way": 0, "relation": 0}
    building_yes = 0
    for reg in registros:
        # geometria: anel(is) para way/relation; ponto para node
        if reg["aneis"]:
            if len(reg["aneis"]) == 1:
                geom = QgsGeometry.fromPolygonXY([[QgsPointXY(lon, lat) for lon, lat in reg["aneis"][0]]])
            else:
                geom = QgsGeometry.fromMultiPolygonXY(
                    [[[QgsPointXY(lon, lat) for lon, lat in anel] for anel in reg["aneis"]]])
            centro = geom.centroid()
            if centro.isEmpty() or not engine.contains(centro.asPoint()):
                continue
            area_m2 = sum(medidor.measurePolygon([QgsPointXY(lon, lat) for lon, lat in anel])
                          for anel in reg["aneis"])
            c = centro.asPoint()
            centroid_lon, centroid_lat = c.x(), c.y()
            feat_area = QgsFeature(campos)
            feat_area.setGeometry(geom)
        else:
            ponto = QgsPointXY(reg["lon"], reg["lat"])
            if not engine.contains(ponto):
                continue
            geom = QgsGeometry.fromPointXY(ponto)
            area_m2 = 0.0
            centroid_lon, centroid_lat = reg["lon"], reg["lat"]
            feat_area = None

        atributos = {
            "poi_id": reg["poi_id"], "osm_type": reg["osm_type"], "osm_id": reg["osm_id"],
            "name": reg["name"], "building": reg["building"], "amenity": reg["amenity"],
            "way": reg["way"], "poi_type": reg["poi_type"], "area": area_m2,
            "area_ft2": area_m2 * poi_parser.AREA_M2_TO_FT2,
            "centroid_lon": centroid_lon, "centroid_lat": centroid_lat,
        }
        feat_poi = QgsFeature(campos)
        feat_poi.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(centroid_lon, centroid_lat)))
        for nome, valor in atributos.items():
            feat_poi[nome] = valor
        pois_layer.addFeature(feat_poi)
        if feat_area is not None:
            for nome, valor in atributos.items():
                feat_area[nome] = valor
            area_layer.addFeature(feat_area)

        por_tipo[reg["osm_type"]] = por_tipo.get(reg["osm_type"], 0) + 1
        if reg["building"] == "yes":
            building_yes += 1

    pois_layer.commitChanges()
    area_layer.commitChanges()

    total = pois_layer.featureCount()
    if total == 0:
        log("OSM POI: nenhum POI com centroide dentro do municipio")
        return dict(vazio, metadata=dict(base_meta, erro="nenhum POI dentro do municipio",
                                         sem_pois=True))

    log("OSM POI: {} POIs no municipio (node: {}, way: {}, relation: {})".format(
        total, por_tipo.get("node", 0), por_tipo.get("way", 0), por_tipo.get("relation", 0)))
    log("OSM POI: {} POIs com building=yes".format(building_yes))
    if descartadas.get("way_aberto"):
        log("OSM POI: descartadas {} ways abertos (sem anel fechado)".format(descartadas["way_aberto"]))
    if descartadas.get("relacao_sem_anel_fechado"):
        log("OSM POI: descartadas {} relacoes sem anel outer fechado".format(
            descartadas["relacao_sem_anel_fechado"]))

    # grava no GeoPackage e RELÊ as camadas de lá (atributo de memory não persiste)
    from .diagnostico import _grava_gpkg
    ok_pois, msg_pois = _grava_gpkg(pois_layer, gpkg_path, "osm_pois_{}".format(code_muni))
    ok_area, msg_area = True, ""
    area_criada = area_layer.featureCount() > 0
    if area_criada:
        ok_area, msg_area = _grava_gpkg(area_layer, gpkg_path, "osm_pois_area_{}".format(code_muni))
    if not ok_pois or not ok_area:
        return dict(vazio, metadata=dict(
            base_meta, erro="gravar GeoPackage: {}".format(msg_pois if not ok_pois else msg_area)))

    pois_gpkg = QgsVectorLayer("{}|layername=osm_pois_{}".format(gpkg_path, code_muni),
                               "osm_pois - {}".format(nome_muni or code_muni), "ogr")
    layers = {"osm_pois": pois_gpkg if pois_gpkg.isValid() else None, "osm_pois_area": None}
    if area_criada:
        area_gpkg = QgsVectorLayer("{}|layername=osm_pois_area_{}".format(gpkg_path, code_muni),
                                   "osm_pois_area - {}".format(nome_muni or code_muni), "ogr")
        layers["osm_pois_area"] = area_gpkg if area_gpkg.isValid() else None

    log("OSM POI: gravados {} pontos e {} areas em {}".format(
        pois_layer.featureCount(), area_layer.featureCount(), gpkg_path))

    return {
        "raw_cache": str(cache_path),
        "layers": layers,
        "metadata": dict(base_meta,
                         total_municipio=total,
                         por_osm_type=por_tipo,
                         building_yes=building_yes,
                         area_layer_criada=area_criada,
                         gpkg_ok=True),
    }
