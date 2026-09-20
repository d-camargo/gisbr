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


def _engine_poligono(wkt):
    from qgis.core import QgsGeometry

    geom = QgsGeometry.fromWkt(wkt)
    engine = QgsGeometry.createGeometryEngine(geom.constGet())
    engine.prepareGeometry()
    return engine


def _engine_tudo_dentro():
    """Engine de um polígono grande o bastante para conter qualquer
    coordenada sintética destes testes — nada fica de fora por recorte."""
    return _engine_poligono("POLYGON((-1 -1, 1 -1, 1 1, -1 1, -1 -1))")


def _arco(arc_id, way_id, from_node, to_node, nodes, coords, **extra):
    base = {
        "arc_id": arc_id, "way_id": way_id, "seq": 0,
        "from_node": from_node, "to_node": to_node,
        "nodes": nodes, "coords": coords,
        "highway": "residential", "name": "", "oneway": "",
        "junction": "", "bridge": "", "tunnel": "", "layer": "",
        "veicular": True, "pedestre": True,
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


def test_monta_problemas_marca_campo_rede_veicular(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    nodes_dict = {1: (0.0, 0.0), 2: (0.02, 0.0)}
    arcos = [_arco(1, 100, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]])]
    diag = diagnostica(arcos, "veicular")

    # Por padrão (incluir_pontas_soltas=False) ponta_solta NAO aparece —
    # beco sem saída é o normal da malha, não erro; as duas pontas do arco
    # viram "nao listadas", nao problemas.
    problemas, nao_listadas = osm_pipeline._monta_problemas(
        arcos, diag, nodes_dict, _engine_tudo_dentro(), "veicular")

    assert problemas == []
    assert nao_listadas == 2

    problemas_com, nao_listadas_com = osm_pipeline._monta_problemas(
        arcos, diag, nodes_dict, _engine_tudo_dentro(), "veicular", incluir_pontas_soltas=True)
    assert problemas_com  # ponta_solta nos dois extremos
    assert all(p["rede"] == "veicular" for p in problemas_com)
    assert any(p["tipo"] == "ponta_solta" for p in problemas_com)
    assert nao_listadas_com == 0


def test_monta_problemas_pedestre_nao_emite_nem_conta_ponta_solta(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # mesmo arco solto (grau 1 nas duas pontas, sem nada por perto) — na
    # rede veicular vira ponta_solta (com incluir_pontas_soltas=True); na
    # rede pedestre NAO (becos de calçada são a norma) — nem sequer conta
    # como "nao listada".
    nodes_dict = {1: (0.0, 0.0), 2: (0.02, 0.0)}
    arcos = [_arco(1, 100, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]])]

    diag_v = diagnostica(arcos, "veicular")
    problemas_v, nao_listadas_v = osm_pipeline._monta_problemas(
        arcos, diag_v, nodes_dict, _engine_tudo_dentro(), "veicular", incluir_pontas_soltas=True)
    assert any(p["tipo"] == "ponta_solta" for p in problemas_v)
    assert nao_listadas_v == 0

    diag_p = diagnostica(arcos, "pedestre")
    problemas_p, nao_listadas_p = osm_pipeline._monta_problemas(
        arcos, diag_p, nodes_dict, _engine_tudo_dentro(), "pedestre", incluir_pontas_soltas=True)
    assert not any(p["tipo"] == "ponta_solta" for p in problemas_p)
    assert all(p["rede"] == "pedestre" for p in problemas_p)
    assert nao_listadas_p == 0


# --- regressão do bug do closestSegmentWithContext (falsos positivos a 0,0 m) ---

def test_ponta_quase_conectada_arco_real_fora_da_tolerancia_nao_detectada(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # Caso real (Contagem/RMBH, node 8229947406 x arco way_id=24452 — o
    # mesmo par citado na revisão): closestSegmentWithContext(pt) devolvia
    # (0.0, pt, 3, 1) — o próprio ponto de busca como "mais próximo" —
    # embora a distância REAL até a geometria (`geom.nearestPoint`) seja
    # ~10,97 m, acima da tolerância de 10 m. É uma via de 4 vértices (não
    # um segmento reto de 2 pontos) — o bug não reproduz num segmento
    # simples, só numa polilinha com vértices intermediários.
    nodes_dict = {
        8229947409: (-43.9570636, -19.9420286),
        8229947408: (-43.9570056, -19.9418199),
        8229947407: (-43.9568699, -19.9418504),
        12162980953: (-43.9568914, -19.9419404),
        8229947406: (-43.9569149, -19.9420370),  # ponta (grau 1)
        999999999: (-43.9000000, -19.9000000),   # outra ponta do arco solto, bem longe
    }
    arco_real_nodes = [8229947409, 8229947408, 8229947407, 12162980953]
    arcos = [
        _arco(1, 24452, 8229947409, 12162980953, arco_real_nodes,
              [nodes_dict[n] for n in arco_real_nodes], highway="secondary"),
        _arco(2, 200, 8229947406, 999999999, [8229947406, 999999999],
              [nodes_dict[8229947406], nodes_dict[999999999]]),
    ]
    diag = diagnostica(arcos)
    assert diag["grau"][8229947406] == 1

    resultados = osm_pipeline.ponta_quase_conectada(arcos, diag, nodes_dict)
    achados = {r["node_id"] for r in resultados}
    assert 8229947406 not in achados


def test_ponta_quase_conectada_distancia_5m_no_intervalo_esperado(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # mesmo cenário do teste de undershoot (~5 m) — hoje nenhum teste
    # checava o VALOR da distância reportada, só que ficava <= tolerância
    # (o que o bug do closestSegmentWithContext também "passava", sempre
    # com 0,0 m). Aqui exigimos que o valor fique num intervalo plausível.
    nodes_dict = {
        1: (0.0, 0.0),
        2: (0.02, 0.0),
        3: (0.01, 5.0 / _M_POR_GRAU),
        4: (0.01, 0.02),
    }
    arcos = [
        _arco(1, 100, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]]),
        _arco(2, 200, 3, 4, [3, 4], [nodes_dict[3], nodes_dict[4]]),
    ]
    diag = diagnostica(arcos)

    resultados = osm_pipeline.ponta_quase_conectada(arcos, diag, nodes_dict)
    achados = {r["node_id"]: r for r in resultados}
    assert 3 in achados
    assert 3.0 <= achados[3]["distancia_m"] <= 7.0


# --- mao_unica_sem_saida vs mao_unica_borda (_monta_problemas) -----------

def test_monta_problemas_mao_unica_sem_saida_dentro_do_poligono(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # beco classico: 1<->2<->4<->1 (bidirecional) + 2->3 (oneway "yes", so
    # vai). Node 3 fica fora da SCC principal — mas toda a SCC {3} esta
    # dentro do poligono, entao deve sair como "sem_saida" (alta), nao
    # "borda".
    nodes_dict = {
        1: (0.0, 0.0), 2: (0.001, 0.0), 3: (0.002, 0.0), 4: (0.0005, 0.001),
    }
    arcos = [
        _arco(1, 1, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]], oneway="no"),
        _arco(2, 2, 2, 4, [2, 4], [nodes_dict[2], nodes_dict[4]], oneway="no"),
        _arco(3, 3, 4, 1, [4, 1], [nodes_dict[4], nodes_dict[1]], oneway="no"),
        _arco(4, 4, 2, 3, [2, 3], [nodes_dict[2], nodes_dict[3]], oneway="yes"),
    ]
    diag = diagnostica(arcos, "veicular")
    assert 3 in diag["mao_unica_sem_saida"]

    engine = _engine_poligono("POLYGON((-0.01 -0.01, 0.01 -0.01, 0.01 0.01, -0.01 0.01, -0.01 -0.01))")
    problemas, _nao_listadas = osm_pipeline._monta_problemas(arcos, diag, nodes_dict, engine, "veicular")

    # node 3 e a representante do grupo (SCC {3}, tamanho 1) — o mao_unica
    # aparece uma vez, com "1 nós" no detalhe; grau 1 nao gera ponta_solta
    # (default incluir_pontas_soltas=False), entao so o mao_unica aparece
    # para o node 3.
    mao_unica = [p for p in problemas if p["node_id"] == 3 and p["tipo"].startswith("mao_unica")]
    assert len(mao_unica) == 1
    assert mao_unica[0]["tipo"] == "mao_unica_sem_saida"
    assert mao_unica[0]["severidade"] == "alta"
    assert mao_unica[0]["detalhe"] == "1 nós"
    assert not any(p["tipo"] == "mao_unica_borda" for p in problemas)


def test_monta_problemas_mao_unica_borda_quando_scc_sai_do_poligono(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # mesmo triangulo principal (1,2,4), mas o beco agora e um par 5<->6
    # (bidirecional, so alcancavel de 2 via oneway "yes" 2->5) formando
    # uma SCC {5,6} propria. node5 fica DENTRO do poligono; node6 fica
    # FORA — o oneway "atravessa a borda" e a volta pode estar fora do
    # bbox consultado, entao node5 deve sair como "mao_unica_borda"
    # (baixa), nao "mao_unica_sem_saida" (alta); node6 nem aparece (fora
    # do poligono).
    nodes_dict = {
        1: (0.0, 0.0), 2: (0.001, 0.0), 4: (0.0005, 0.001),
        5: (0.002, 0.0), 6: (0.003, 0.0),
    }
    arcos = [
        _arco(1, 1, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]], oneway="no"),
        _arco(2, 2, 2, 4, [2, 4], [nodes_dict[2], nodes_dict[4]], oneway="no"),
        _arco(3, 3, 4, 1, [4, 1], [nodes_dict[4], nodes_dict[1]], oneway="no"),
        _arco(4, 4, 2, 5, [2, 5], [nodes_dict[2], nodes_dict[5]], oneway="yes"),
        _arco(5, 5, 5, 6, [5, 6], [nodes_dict[5], nodes_dict[6]], oneway="no"),
    ]
    diag = diagnostica(arcos, "veicular")
    assert 5 in diag["mao_unica_sem_saida"]
    assert 6 in diag["mao_unica_sem_saida"]
    assert diag["scc"][5] == diag["scc"][6]

    # poligono pequeno: exclui node6 (lon 0.003), inclui o resto
    engine = _engine_poligono("POLYGON((-0.01 -0.01, 0.0025 -0.01, 0.0025 0.01, -0.01 0.01, -0.01 -0.01))")
    problemas, _nao_listadas = osm_pipeline._monta_problemas(arcos, diag, nodes_dict, engine, "veicular")

    por_no = {p["node_id"]: p for p in problemas if p["node_id"] in (5, 6)}
    assert 6 not in por_no  # fora do poligono, nunca vira representante
    assert 5 in por_no  # representante do grupo {5, 6} (unico dentro do poligono)
    assert por_no[5]["tipo"] == "mao_unica_borda"
    assert por_no[5]["severidade"] == "baixa"
    assert por_no[5]["detalhe"] == "2 nós"
    assert not any(p["tipo"] == "mao_unica_sem_saida" for p in problemas)


def test_monta_problemas_mao_unica_um_ponto_por_grupo_de_3(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # beco com 3 nos na mesma armadilha (SCC propria): 2->3->5->6->3 (ciclo
    # 3<->5<->6), alcancavel a partir do triangulo principal (1,2,4) mas sem
    # volta para ele. A armadilha e do grupo, nao de cada no — sai UM ponto
    # para o grupo inteiro (nao um por no), com "3 nós" no detalhe.
    nodes_dict = {
        1: (0.0, 0.0), 2: (0.001, 0.0), 4: (0.0005, 0.001),
        3: (0.002, 0.0), 5: (0.003, 0.0), 6: (0.0025, 0.001),
    }
    arcos = [
        _arco(1, 1, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]], oneway="no"),
        _arco(2, 2, 2, 4, [2, 4], [nodes_dict[2], nodes_dict[4]], oneway="no"),
        _arco(3, 3, 4, 1, [4, 1], [nodes_dict[4], nodes_dict[1]], oneway="no"),
        _arco(4, 4, 2, 3, [2, 3], [nodes_dict[2], nodes_dict[3]], oneway="yes"),
        _arco(5, 5, 3, 5, [3, 5], [nodes_dict[3], nodes_dict[5]], oneway="no"),
        _arco(6, 6, 5, 6, [5, 6], [nodes_dict[5], nodes_dict[6]], oneway="no"),
        _arco(7, 7, 6, 3, [6, 3], [nodes_dict[6], nodes_dict[3]], oneway="no"),
    ]
    diag = diagnostica(arcos, "veicular")
    assert {3, 5, 6} <= set(diag["mao_unica_sem_saida"])
    assert diag["scc"][3] == diag["scc"][5] == diag["scc"][6]

    problemas, _nao_listadas = osm_pipeline._monta_problemas(
        arcos, diag, nodes_dict, _engine_tudo_dentro(), "veicular")

    mao_unica = [p for p in problemas if p["tipo"] == "mao_unica_sem_saida"]
    assert len(mao_unica) == 1
    assert mao_unica[0]["node_id"] == 3  # menor node_id do grupo {3, 5, 6}
    assert mao_unica[0]["detalhe"] == "3 nós"
    assert mao_unica[0]["severidade"] == "alta"


# --- severidade de ponta_quase_conectada estratificada por distância -----

def test_monta_problemas_ponta_quase_conectada_severidade_por_distancia(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    # via principal (node1->node2) com DUAS pontas soltas quase conectadas:
    # node3 a ~2 m (<= TOL_PONTA_ALTA_M=3 -> severidade alta) e node5 a
    # ~8 m (> 3 e <= TOL_PONTA_M=10 -> severidade media). Tipo continua
    # "ponta_quase_conectada" nos dois casos.
    nodes_dict = {
        1: (0.0, 0.0),
        2: (0.02, 0.0),
        3: (0.01, 2.0 / _M_POR_GRAU),
        4: (0.01, 0.02),
        5: (0.015, 8.0 / _M_POR_GRAU),
        6: (0.015, 0.02),
    }
    arcos = [
        _arco(1, 100, 1, 2, [1, 2], [nodes_dict[1], nodes_dict[2]]),
        _arco(2, 200, 3, 4, [3, 4], [nodes_dict[3], nodes_dict[4]]),
        _arco(3, 300, 5, 6, [5, 6], [nodes_dict[5], nodes_dict[6]]),
    ]
    diag = diagnostica(arcos, "veicular")

    problemas, _nao_listadas = osm_pipeline._monta_problemas(
        arcos, diag, nodes_dict, _engine_tudo_dentro(), "veicular")
    por_no = {p["node_id"]: p for p in problemas if p["node_id"] in (3, 5)}

    assert por_no[3]["tipo"] == "ponta_quase_conectada"
    assert por_no[3]["severidade"] == "alta"

    assert por_no[5]["tipo"] == "ponta_quase_conectada"
    assert por_no[5]["severidade"] == "media"
