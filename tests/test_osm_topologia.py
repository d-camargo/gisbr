# -*- coding: utf-8 -*-
"""Testes unitarios para gisbr.core.osm_topologia (topologia real do OSM).

Rodam SEM QGIS (o modulo e stdlib pura):
    python3 -m pytest tests/test_osm_topologia.py -q
"""

from gisbr.core.osm_topologia import (
    componentes,
    componentes_fortes,
    constroi_arcos,
    diagnostica,
    grau,
    sentido,
)


def _way(way_id, nodes, tags=None):
    return {"id": way_id, "nodes": nodes, "tags": tags or {}}


def _nodes_dict(ids):
    """node_id -> (lon, lat) sintetico, um ponto por id ao longo do eixo x."""
    return {n: (float(n), 0.0) for n in ids}


def test_t_no_meio_de_way_vira_3_arcos_e_1_componente():
    # way A: 1-2-3-4-5 ; way B parte do meio de A (node 3) ate o node 6
    nodes_dict = _nodes_dict([1, 2, 3, 4, 5, 6])
    ways = [
        _way(100, [1, 2, 3, 4, 5], {"highway": "residential"}),
        _way(200, [3, 6], {"highway": "residential"}),
    ]
    arcos, n_orfaos = constroi_arcos(ways, nodes_dict)

    assert n_orfaos == 0
    assert len(arcos) == 3
    # way A quebra em [1,2,3] e [3,4,5]; way B fica inteiro [3,6]
    segmentos = sorted(tuple(a["nodes"]) for a in arcos)
    assert segmentos == [(1, 2, 3), (3, 4, 5), (3, 6)]

    node_comp, comp_tam = componentes(arcos)
    assert len(comp_tam) == 1
    assert comp_tam[0] == 3
    assert len(set(node_comp.values())) == 1


def test_no_orfao_contado_e_descartado():
    nodes_dict = _nodes_dict([1, 2, 3])
    # node 99 nao existe em nodes_dict
    ways = [_way(100, [1, 99, 2, 3], {"highway": "residential"})]
    arcos, n_orfaos = constroi_arcos(ways, nodes_dict)

    assert n_orfaos == 1
    assert len(arcos) == 1
    assert arcos[0]["nodes"] == [1, 2, 3]


def test_arco_com_menos_de_2_nos_e_descartado():
    nodes_dict = _nodes_dict([1])
    ways = [_way(100, [1], {"highway": "residential"})]
    arcos, n_orfaos = constroi_arcos(ways, nodes_dict)
    assert arcos == []
    assert n_orfaos == 0


def test_duas_componentes_gera_1_ilha():
    nodes_dict = _nodes_dict([1, 2, 3, 4, 5, 6, 7])
    ways = [
        # componente principal: 3 arcos (via um no compartilhado no meio)
        _way(1, [1, 2, 3], {"highway": "residential"}),
        _way(2, [3, 4], {"highway": "residential"}),
        _way(3, [4, 5], {"highway": "residential"}),
        # ilha: isolada, 1 arco
        _way(4, [6, 7], {"highway": "residential"}),
    ]
    arcos, _ = constroi_arcos(ways, nodes_dict)
    diag = diagnostica(arcos)

    assert len(diag["comp_tam"]) == 2
    assert diag["comp_tam"][0] == 3  # principal
    assert diag["comp_tam"][1] == 1  # ilha
    assert len(diag["ilhas"]) == 1
    comp_id, n_arcos, representante = diag["ilhas"][0]
    assert comp_id == 1
    assert n_arcos == 1
    assert representante == 6


def test_grau_e_ponta_solta():
    nodes_dict = _nodes_dict([1, 2, 3])
    ways = [_way(1, [1, 2, 3], {"highway": "residential"})]
    arcos, _ = constroi_arcos(ways, nodes_dict)
    g = grau(arcos)
    assert g == {1: 1, 3: 1}

    diag = diagnostica(arcos)
    assert set(diag["pontas_soltas"]) == {1, 3}


def test_grau_laco_soma_2():
    nodes_dict = _nodes_dict([1, 2, 3])
    # way fechado: 1-2-3-1 (from == to == 1)
    ways = [_way(1, [1, 2, 3, 1], {"highway": "residential"})]
    arcos, _ = constroi_arcos(ways, nodes_dict)
    assert len(arcos) == 1  # nao quebra no laço
    g = grau(arcos)
    assert g[1] == 2


def test_laco_way_fechado_nao_quebra():
    nodes_dict = _nodes_dict([1, 2, 3, 4])
    ways = [_way(1, [1, 2, 3, 4, 1], {"highway": "residential"})]
    arcos, _ = constroi_arcos(ways, nodes_dict)
    assert len(arcos) == 1
    assert arcos[0]["nodes"] == [1, 2, 3, 4, 1]


def test_sentido_oneway_explicito():
    assert sentido({"oneway": "yes"}) == "direto"
    assert sentido({"oneway": "true"}) == "direto"
    assert sentido({"oneway": "1"}) == "direto"
    assert sentido({"oneway": "-1"}) == "inverso"
    assert sentido({"oneway": "reverse"}) == "inverso"
    assert sentido({"oneway": "no"}) == "ambos"
    assert sentido({"oneway": "false"}) == "ambos"
    assert sentido({"oneway": "0"}) == "ambos"


def test_sentido_rotatoria_implicita_oneway():
    assert sentido({"oneway": "", "junction": "roundabout", "highway": "residential"}) == "direto"
    assert sentido({"oneway": "", "junction": "circular", "highway": "residential"}) == "direto"
    assert sentido({"oneway": "", "junction": "", "highway": "motorway"}) == "direto"
    assert sentido({"oneway": "", "junction": "", "highway": "residential"}) == "ambos"


def test_beco_oneway_gera_mao_unica_sem_saida():
    # 1 -> 2 -> 3 (oneway "yes", so vai); 2 tambem liga a 4 nos dois sentidos
    # para manter tudo na mesma componente fraca. O beco 2->3 so pode ser
    # alcancado, nunca deixado: 3 fica fora da SCC principal.
    nodes_dict = _nodes_dict([1, 2, 3, 4])
    ways = [
        _way(1, [1, 2], {"highway": "residential", "oneway": "no"}),
        _way(2, [2, 4], {"highway": "residential", "oneway": "no"}),
        _way(3, [4, 1], {"highway": "residential", "oneway": "no"}),
        _way(4, [2, 3], {"highway": "residential", "oneway": "yes"}),
    ]
    arcos, _ = constroi_arcos(ways, nodes_dict)
    diag = diagnostica(arcos)

    # tudo numa unica componente fraca
    assert len(diag["comp_tam"]) == 1
    # node 3 so e alcancavel, nao tem saida -> fora da scc principal
    assert 3 in diag["mao_unica_sem_saida"]
    assert diag["scc"][3] != diag["scc"][1]


def test_componentes_fortes_tarjan_iterativo_cadeia_5000_nos():
    n = 5000
    nodes_dict = _nodes_dict(range(1, n + 1))
    # cadeia de 4999 ways de 2 nos cada (1-2, 2-3, ..., 4999-5000): stressa
    # a profundidade da DFS do Tarjan sem estourar o limite de recursao.
    ways = [
        _way(i, [i, i + 1], {"highway": "residential", "oneway": "no"})
        for i in range(1, n)
    ]
    arcos, n_orfaos = constroi_arcos(ways, nodes_dict)
    assert n_orfaos == 0
    assert len(arcos) == n - 1

    node_scc = componentes_fortes(arcos)
    # oneway "no" -> bidirecional -> toda a cadeia e uma unica SCC
    assert len(set(node_scc.values())) == 1
    assert len(node_scc) == n
