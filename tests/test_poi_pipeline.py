# -*- coding: utf-8 -*-
"""Testes para gisbr.core.poi_pipeline (_montar_camadas e integracao com QGIS)."""

import pytest

qgis_core = pytest.importorskip("qgis.core")
from qgis.core import QgsGeometry, QgsPointXY

from gisbr.core.poi_parser import AREA_M2_TO_FT2
from gisbr.core.poi_pipeline import _montar_camadas


def test_montar_camadas_sintetico(qgis_app):
    # Municipio: quadrado simples em graus (-44.0 a -43.0 lon, -20.0 a -19.0 lat)
    mun_polygon = [
        QgsPointXY(-44.0, -20.0),
        QgsPointXY(-44.0, -19.0),
        QgsPointXY(-43.0, -19.0),
        QgsPointXY(-43.0, -20.0),
        QgsPointXY(-44.0, -20.0),
    ]
    mun_geom = QgsGeometry.fromPolygonXY([mun_polygon])

    registros = [
        # (a) node dentro
        {
            "poi_id": 1,
            "osm_type": "node",
            "osm_id": 101,
            "name": "Node Dentro",
            "building": "",
            "amenity": "cafe",
            "way": "",
            "poi_type": "cafe",
            "aneis": [],
            "lon": -43.5,
            "lat": -19.5,
        },
        # (b) node fora
        {
            "poi_id": 2,
            "osm_type": "node",
            "osm_id": 102,
            "name": "Node Fora",
            "building": "",
            "amenity": "restaurant",
            "way": "",
            "poi_type": "restaurant",
            "aneis": [],
            "lon": -42.5,
            "lat": -19.5,
        },
        # (c) way de anel unico dentro
        {
            "poi_id": 3,
            "osm_type": "way",
            "osm_id": 201,
            "name": "Way Anel Unico Dentro",
            "building": "yes",
            "amenity": "",
            "way": "",
            "poi_type": "yes",
            "aneis": [
                [
                    (-43.6, -19.6),
                    (-43.6, -19.4),
                    (-43.4, -19.4),
                    (-43.4, -19.6),
                    (-43.6, -19.6),
                ]
            ],
            "lon": None,
            "lat": None,
        },
        # (d) relacao multi-anel dentro (outer + inner)
        {
            "poi_id": 4,
            "osm_type": "relation",
            "osm_id": 301,
            "name": "Relacao Multi-Anel Dentro",
            "building": "yes",
            "amenity": "school",
            "way": "",
            "poi_type": "school",
            "aneis": [
                [
                    (-43.8, -19.8),
                    (-43.8, -19.2),
                    (-43.2, -19.2),
                    (-43.2, -19.8),
                    (-43.8, -19.8),
                ],
                [
                    (-43.6, -19.6),
                    (-43.6, -19.4),
                    (-43.4, -19.4),
                    (-43.4, -19.6),
                    (-43.6, -19.6),
                ],
            ],
            "lon": None,
            "lat": None,
        },
        # (e) way cujo centroide cai fora
        {
            "poi_id": 5,
            "osm_type": "way",
            "osm_id": 202,
            "name": "Way Centroid Fora",
            "building": "yes",
            "amenity": "",
            "way": "",
            "poi_type": "yes",
            "aneis": [
                [
                    (-42.6, -19.6),
                    (-42.6, -19.4),
                    (-42.4, -19.4),
                    (-42.4, -19.6),
                    (-42.6, -19.6),
                ]
            ],
            "lon": None,
            "lat": None,
        },
    ]

    # Nenhuma excecao deve ser lancada (teste de regressao do TypeError)
    pois_layer, area_layer, por_tipo, building_yes = _montar_camadas(registros, mun_geom)

    # Assercoes de contagem e por_tipo
    assert pois_layer.featureCount() == 3
    assert area_layer.featureCount() == 2
    assert por_tipo == {"node": 1, "way": 1, "relation": 1}

    # Assercoes na camada de pontos
    features_pois = list(pois_layer.getFeatures())
    feats_by_poi_id = {f["poi_id"]: f for f in features_pois}
    assert set(feats_by_poi_id.keys()) == {1, 3, 4}

    # Node (a)
    feat_node = feats_by_poi_id[1]
    assert feat_node["osm_type"] == "node"
    assert feat_node["area"] == 0.0
    assert feat_node["area_ft2"] == 0.0
    assert feat_node["centroid_lon"] == pytest.approx(-43.5)
    assert feat_node["centroid_lat"] == pytest.approx(-19.5)
    pt_node = feat_node.geometry().asPoint()
    assert pt_node.x() == pytest.approx(feat_node["centroid_lon"])
    assert pt_node.y() == pytest.approx(feat_node["centroid_lat"])

    # Poligonos (c) e (d)
    features_area = list(area_layer.getFeatures())
    area_feats_by_poi_id = {f["poi_id"]: f for f in features_area}
    assert set(area_feats_by_poi_id.keys()) == {3, 4}

    for poi_id in (3, 4):
        f_poi = feats_by_poi_id[poi_id]
        f_area = area_feats_by_poi_id[poi_id]

        assert f_poi["area"] > 0.0
        assert f_poi["area_ft2"] == pytest.approx(f_poi["area"] * AREA_M2_TO_FT2)
        assert f_area["area"] == f_poi["area"]
        assert f_area["area_ft2"] == f_poi["area_ft2"]

        pt = f_poi.geometry().asPoint()
        assert pt.x() == pytest.approx(f_poi["centroid_lon"])
        assert pt.y() == pytest.approx(f_poi["centroid_lat"])
