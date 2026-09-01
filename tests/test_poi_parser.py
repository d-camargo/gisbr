# -*- coding: utf-8 -*-
"""Testes unitarios para gisbr.core.poi_parser (predicado osm2gmns).

Rodam SEM QGIS (o modulo e stdlib pura):
    python3 -m pytest tests/test_poi_parser.py -q
"""

import json

from gisbr.core.poi_parser import (
    AEROWAY_POI_SET,
    HIGHWAY_POI_SET,
    RAILWAY_POI_SET,
    build_poi_query,
    classifica_way,
    is_poi,
    parse_pois,
    poi_type,
)


def test_conjuntos_de_tags():
    assert HIGHWAY_POI_SET == {"bus_stop", "platform"}
    assert RAILWAY_POI_SET == {
        "depot", "station", "workshop", "halt", "interlocking",
        "junction", "spur_junction", "terminal", "platform",
    }
    assert AEROWAY_POI_SET == set()


def test_classifica_way():
    assert classifica_way({"highway": "bus_stop"}) == "bus_stop"
    assert classifica_way({"highway": "platform"}) == "platform"
    assert classifica_way({"railway": "station"}) == "station"
    assert classifica_way({"railway": "rail"}) == ""
    assert classifica_way({"highway": "residential"}) == ""
    assert classifica_way({}) == ""


def test_is_poi_building_amenity():
    assert is_poi({"building": "yes"}) is True
    assert is_poi({"amenity": "school"}) is True
    assert is_poi({"amenity": ""}) is False
    assert is_poi({}) is False


def test_is_poi_highway_railway():
    assert is_poi({"highway": "bus_stop"}) is True
    assert classifica_way({"highway": "bus_stop"}) == "bus_stop"
    assert is_poi({"highway": "residential"}) is False
    assert is_poi({"railway": "rail"}) is False
    assert is_poi({"railway": "station"}) is True


def test_poi_type_prefere_amenity():
    assert poi_type({"amenity": "school", "building": "yes"}) == "school"
    assert poi_type({"building": "yes"}) == "yes"
    assert poi_type({"highway": "bus_stop"}) == "bus_stop"
    assert poi_type({"highway": "residential"}) == ""


def test_build_poi_query_bbox_e_timeout():
    query = build_poi_query((-43.9, -19.9, -43.8, -19.8), timeout=60)
    assert "[out:json][timeout:60];" in query
    # bbox na ordem Overpass: sul, oeste, norte, leste
    bbox_str = "(-19.9,-43.9,-19.8,-43.8)"
    assert 'nwr["building"]' + bbox_str in query
    assert 'nwr["amenity"]' + bbox_str in query
    assert 'nwr["highway"~"^(bus_stop|platform)$"]' + bbox_str in query
    assert (
        'nwr["railway"~"^(depot|station|workshop|halt|interlocking|junction|'
        'spur_junction|terminal|platform)$"]' + bbox_str in query
    )
    assert query.endswith("out geom;")


def test_build_poi_query_timeout_default():
    assert "[out:json][timeout:180];" in build_poi_query((-44.0, -20.0, -43.0, -19.0))


# geometria fechada (primeiro ponto == ultimo, >= 4 pontos) em `out geom`
ANEL_QUADRADO = [
    {"lon": -43.90, "lat": -19.90},
    {"lon": -43.90, "lat": -19.85},
    {"lon": -43.85, "lat": -19.85},
    {"lon": -43.85, "lat": -19.90},
    {"lon": -43.90, "lat": -19.90},
]
ANEL_INTERNO = [
    {"lon": -43.89, "lat": -19.89},
    {"lon": -43.89, "lat": -19.86},
    {"lon": -43.86, "lat": -19.86},
    {"lon": -43.86, "lat": -19.89},
    {"lon": -43.89, "lat": -19.89},
]
LINHA_ABERTA = [
    {"lon": -43.90, "lat": -19.90},
    {"lon": -43.88, "lat": -19.88},
    {"lon": -43.86, "lat": -19.86},
]

PAYLOAD_SINTETICO = {
    "elements": [
        {
            "type": "node",
            "id": 101,
            "lat": -19.9,
            "lon": -43.9,
            "tags": {"amenity": "cafe", "name": "Cafe Exemplo"},
        },
        {
            "type": "way",
            "id": 201,
            "tags": {"building": "yes", "name": "Predio Exemplo"},
            "geometry": ANEL_QUADRADO,
        },
        {
            "type": "way",
            "id": 202,
            "tags": {"building": "yes"},
            "geometry": LINHA_ABERTA,
        },
        {
            "type": "relation",
            "id": 301,
            "tags": {"building": "yes", "name": "Conjunto Exemplo"},
            "members": [
                {"type": "way", "ref": 1, "role": "outer", "geometry": ANEL_QUADRADO},
                {"type": "way", "ref": 2, "role": "inner", "geometry": ANEL_INTERNO},
            ],
        },
        {
            "type": "relation",
            "id": 302,
            "tags": {"amenity": "school"},
            "members": [
                {"type": "way", "ref": 3, "role": "outer", "geometry": LINHA_ABERTA},
            ],
        },
        {
            "type": "node",
            "id": 102,
            "lat": -19.95,
            "lon": -43.95,
            "tags": {"highway": "residential"},
        },
    ]
}


def anel_esperado(pontos):
    return [(p["lon"], p["lat"]) for p in pontos]


def test_parse_pois_registros_e_descartadas():
    registros, descartadas = parse_pois(PAYLOAD_SINTETICO)

    assert len(registros) == 3
    assert descartadas == {"way_aberto": 1, "relacao_sem_anel_fechado": 1}

    # ordenados por (osm_type, osm_id): node < relation < way
    node, relation, way = registros

    assert node["osm_type"] == "node"
    assert node["osm_id"] == 101
    assert node["name"] == "Cafe Exemplo"
    assert node["amenity"] == "cafe"
    assert node["building"] == ""
    assert node["way"] == ""
    assert node["poi_type"] == "cafe"
    assert node["aneis"] == []
    assert node["lon"] == -43.9
    assert node["lat"] == -19.9
    assert node["poi_id"] == 1

    assert relation["osm_type"] == "relation"
    assert relation["osm_id"] == 301
    assert relation["poi_id"] == 2
    # apenas o membro outer fechado vira anel; o inner e ignorado
    assert relation["aneis"] == [anel_esperado(ANEL_QUADRADO)]
    assert relation["lon"] is None
    assert relation["lat"] is None

    assert way["osm_type"] == "way"
    assert way["osm_id"] == 201
    assert way["poi_id"] == 3
    assert way["aneis"] == [anel_esperado(ANEL_QUADRADO)]
    assert way["lon"] is None
    assert way["lat"] is None
    assert way["building"] == "yes"
    assert way["poi_type"] == "yes"


def test_parse_pois_aceita_json_string():
    via_dict, _ = parse_pois(PAYLOAD_SINTETICO)
    via_str, descartadas = parse_pois(json.dumps(PAYLOAD_SINTETICO))
    assert via_str == via_dict
    assert descartadas == {"way_aberto": 1, "relacao_sem_anel_fechado": 1}


def test_parse_pois_poi_id_estavel():
    regs1, desc1 = parse_pois(PAYLOAD_SINTETICO)
    regs2, desc2 = parse_pois(PAYLOAD_SINTETICO)
    assert [r["poi_id"] for r in regs1] == [r["poi_id"] for r in regs2] == [1, 2, 3]
    assert regs1 == regs2
    assert desc1 == desc2


def test_parse_pois_elemento_sem_poi_ignorado():
    # node sem tags de POI nao gera registro nem entra nas descartadas
    registros, descartadas = parse_pois({
        "elements": [
            {"type": "node", "id": 1, "lat": -19.9, "lon": -43.9, "tags": {}},
            {"type": "node", "id": 2, "lat": -19.9, "lon": -43.9},
        ]
    })
    assert registros == []
    assert descartadas == {"way_aberto": 0, "relacao_sem_anel_fechado": 0}
