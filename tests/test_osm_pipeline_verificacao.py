# -*- coding: utf-8 -*-
"""Testes das verificações geométricas de gisbr.core.osm_pipeline.

`ponta_quase_conectada` e `cruzamento_sem_no` exigem QGIS (QgsGeometry,
QgsSpatialIndex, QgsDistanceArea) — pula se `qgis_app` vier None
(ver tests/conftest.py).
"""

import pytest

from gisbr.core.osm_topologia import diagnostica
from gisbr.core import osm_pipeline

# Trabalha perto do equador para a conversão m<->grau ficar simples
# (111320 m por grau, sem o fator cos(lat)).
_M_POR_GRAU = 111320.0


def _arco(arc_id, way_id, from_node, to_node, nodes, coords, **extra):
    base = {
        "arc_id": arc_id, "way_id": way_id, "seq": 0,
        "from_node": from_node, "to_node": to_node,
        "nodes": nodes, "coords": coords,
        "highway": "residential", "name": "", "oneway": "",
        "junction": "", "bridge": "", "tunnel": "", "layer": "",
    }
    base.update(extra)
    return base


def test_ponta_quase_conectada_undershoot_5m_detectado(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # via principal: node 1 -> node 2, reta longa no eixo x (lat = 0)
    nodes_dict = {
        1: (0.0, 0.0),
        2: (0.02, 0.0),
        # ponta solta a ~5 m (perpendicular) do meio da via principal
        3: (0.01, 5.0 / _M_POR_GRAU),
        4: (0.01, 0.02),
    }
    arcos = [
        _arco(1, 100, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]]),
        # arco "solto": node 3 (quase conectado) -> node 4 (longe de tudo)
        _arco(2, 200, 3, 4, [3, 4], [nodes_dict[3], nodes_dict[4]]),
    ]
    diag = diagnostica(arcos)
    assert diag["grau"][3] == 1

    resultados = osm_pipeline.ponta_quase_conectada(arcos, diag, nodes_dict)
    achados = {r["node_id"]: r for r in resultados}
    assert 3 in achados
    assert achados[3]["arc_id"] == 1
    assert achados[3]["distancia_m"] <= osm_pipeline.TOL_PONTA_M
    assert "arco 1 (way 100)" in achados[3]["detalhe"]


def test_ponta_quase_conectada_50m_nao_detectado(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    nodes_dict = {
        1: (0.0, 0.0),
        2: (0.02, 0.0),
        # ponta solta a ~50 m da via principal (bem acima da tolerancia de 10 m)
        3: (0.01, 50.0 / _M_POR_GRAU),
        4: (0.01, 0.02),
    }
    arcos = [
        _arco(1, 100, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]]),
        _arco(2, 200, 3, 4, [3, 4], [nodes_dict[3], nodes_dict[4]]),
    ]
    diag = diagnostica(arcos)
    assert diag["grau"][3] == 1

    resultados = osm_pipeline.ponta_quase_conectada(arcos, diag, nodes_dict)
    achados = {r["node_id"] for r in resultados}
    assert 3 not in achados


def test_ponta_quase_conectada_ignora_arco_incidente_no_proprio_no(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # node 2 e ponta de grau 1 (arco 1-2); o unico arco proximo dele e o
    # proprio arco em que ele e extremidade, entao nao deve ser reportado.
    nodes_dict = {1: (0.0, 0.0), 2: (0.02, 0.0)}
    arcos = [_arco(1, 100, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]])]
    diag = diagnostica(arcos)
    assert diag["grau"][1] == 1
    assert diag["grau"][2] == 1

    resultados = osm_pipeline.ponta_quase_conectada(arcos, diag, nodes_dict)
    assert resultados == []


def test_cruzamento_sem_no_detectado(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # duas diagonais que se cruzam no meio, sem no_id compartilhado
    nodes_dict = {1: (0.0, 0.0), 2: (0.02, 0.02), 3: (0.0, 0.02), 4: (0.02, 0.0)}
    arcos = [
        _arco(1, 100, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]]),
        _arco(2, 200, 3, 4, [3, 4], [nodes_dict[3], nodes_dict[4]]),
    ]
    resultados = osm_pipeline.cruzamento_sem_no(arcos)
    assert len(resultados) == 1
    assert resultados[0]["arc_a"] == 1 and resultados[0]["arc_b"] == 2
    assert resultados[0]["detalhe"] == "arcos 1 x 2"
    assert resultados[0]["x"] == pytest.approx(0.01)
    assert resultados[0]["y"] == pytest.approx(0.01)


def test_cruzamento_sem_no_ignora_bridge(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    nodes_dict = {1: (0.0, 0.0), 2: (0.02, 0.02), 3: (0.0, 0.02), 4: (0.02, 0.0)}
    arcos = [
        _arco(1, 100, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]], bridge="yes"),
        _arco(2, 200, 3, 4, [3, 4], [nodes_dict[3], nodes_dict[4]]),
    ]
    resultados = osm_pipeline.cruzamento_sem_no(arcos)
    assert resultados == []


def test_cruzamento_sem_no_ignora_no_compartilhado(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # arcos que se tocam exatamente no no compartilhado (node 2 == node 3):
    # nao e cruzamento sem no, e o ponto de intersecao coincide com o no.
    nodes_dict = {1: (0.0, 0.0), 2: (0.01, 0.01), 4: (0.02, 0.0)}
    arcos = [
        _arco(1, 100, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]]),
        _arco(2, 200, 2, 4, [2, 4], [nodes_dict[2], nodes_dict[4]]),
    ]
    resultados = osm_pipeline.cruzamento_sem_no(arcos)
    assert resultados == []
