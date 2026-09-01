# -*- coding: utf-8 -*-
"""Testes unitarios da linha do poi.csv (GMNS/osm2gmns) — gisbr.core.poi_parser.

A logica de exportacao do algoritmo `gisbr:export_poi_gmns` vive em
`linha_poi_csv` (funcao pura, stdlib), testavel SEM QGIS:
    python3 -m pytest tests/test_export_poi_gmns.py -q
"""

from gisbr.core.poi_parser import AREA_M2_TO_FT2, POI_CSV_COLUNAS, linha_poi_csv


def test_area_m2_to_ft2():
    assert AREA_M2_TO_FT2 == 10.7639


def test_poi_csv_colunas_ordem_exata():
    assert POI_CSV_COLUNAS == (
        "name", "poi_id", "osm_way_id", "osm_relation_id", "building",
        "amenity", "way", "geometry", "centroid", "area", "area_ft2",
    )


def test_linha_poi_csv_way_com_area():
    wkt = "POLYGON ((-43.9 -19.9, -43.9 -19.85, -43.85 -19.85, -43.9 -19.9))"
    attrs = {
        "poi_id": 3,
        "osm_type": "way",
        "osm_id": 201,
        "name": "Predio Exemplo",
        "building": "yes",
        "amenity": "",
        "way": "",
        "area": 12.3456789,
        "area_ft2": 12.3456789 * AREA_M2_TO_FT2,
        "centroid_lon": None,
        "centroid_lat": None,
    }
    linha = linha_poi_csv(attrs, wkt)

    assert tuple(linha.keys()) == POI_CSV_COLUNAS
    assert linha["name"] == "Predio Exemplo"
    assert linha["poi_id"] == 3
    assert linha["osm_way_id"] == "201"
    assert linha["osm_relation_id"] == ""
    assert linha["building"] == "yes"
    assert linha["amenity"] == ""
    assert linha["way"] == ""
    assert linha["geometry"] == wkt
    assert linha["centroid"] == ""
    assert linha["area"] == 12.3
    assert linha["area_ft2"] == round(12.3456789 * AREA_M2_TO_FT2, 1)


def test_linha_poi_csv_node_vazios_e_centroid():
    wkt = "POINT (-43.94 -19.92)"
    attrs = {
        "poi_id": 1,
        "osm_type": "node",
        "osm_id": 101,
        "name": "Cafe Exemplo",
        "building": "",
        "amenity": "cafe",
        "way": "",
        "area": None,
        "area_ft2": None,
        "centroid_lon": -43.94,
        "centroid_lat": -19.92,
    }
    linha = linha_poi_csv(attrs, wkt)

    assert set(linha) == set(POI_CSV_COLUNAS)
    assert linha["osm_way_id"] == ""
    assert linha["osm_relation_id"] == ""
    assert linha["centroid"] == "POINT (-43.9400000 -19.9200000)"
    assert linha["area"] == 0.0
    assert linha["area_ft2"] == 0.0
    assert linha["geometry"] == wkt


def test_linha_poi_csv_relation():
    attrs = {
        "poi_id": 2,
        "osm_type": "relation",
        "osm_id": 301,
        "name": "Conjunto Exemplo",
        "building": "yes",
        "amenity": "",
        "way": "",
        "area": 2500.06,
        "area_ft2": 26911.4,
        "centroid_lon": -43.87,
        "centroid_lat": -19.87,
    }
    linha = linha_poi_csv(attrs, "POLYGON ((-43.9 -19.9, -43.9 -19.85, -43.85 -19.85, -43.9 -19.9))")

    assert linha["osm_relation_id"] == "301"
    assert linha["osm_way_id"] == ""
    assert linha["centroid"] == "POINT (-43.8700000 -19.8700000)"


def test_linha_poi_csv_campos_ausentes_viram_vazio():
    attrs = {"poi_id": 7, "osm_type": "node", "osm_id": 1}
    linha = linha_poi_csv(attrs, "POINT (-1 -2)")

    assert linha["name"] == ""
    assert linha["building"] == ""
    assert linha["amenity"] == ""
    assert linha["way"] == ""
    assert linha["osm_way_id"] == ""
    assert linha["osm_relation_id"] == ""
    assert linha["centroid"] == ""
