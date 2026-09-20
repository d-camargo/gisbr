# -*- coding: utf-8 -*-
"""Testes unitarios para gisbr.core.osm_topologia (topologia real do OSM).

Rodam SEM QGIS (o modulo e stdlib pura):
    python3 -m pytest tests/test_osm_topologia.py -q
"""

import pytest

from gisbr.core.osm_topologia import (
    classifica_modos,
    componentes,
    componentes_fortes,
    constroi_arcos,
    diagnostica,
    grau,
    sentido,
    velocidade_kmh,
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
    arcos, n_orfaos, descartados = constroi_arcos(ways, nodes_dict)

    assert n_orfaos == 0
    assert descartados == {}
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
    arcos, n_orfaos, descartados = constroi_arcos(ways, nodes_dict)

    assert n_orfaos == 1
    assert len(arcos) == 1
    assert arcos[0]["nodes"] == [1, 2, 3]
    assert descartados == {}


def test_arco_com_menos_de_2_nos_e_descartado():
    nodes_dict = _nodes_dict([1])
    ways = [_way(100, [1], {"highway": "residential"})]
    arcos, n_orfaos, descartados = constroi_arcos(ways, nodes_dict)
    assert arcos == []
    assert n_orfaos == 0
    assert descartados == {}


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
    arcos, _, _ = constroi_arcos(ways, nodes_dict)
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
    arcos, _, _ = constroi_arcos(ways, nodes_dict)
    g = grau(arcos)
    assert g == {1: 1, 3: 1}

    diag = diagnostica(arcos)
    assert set(diag["pontas_soltas"]) == {1, 3}


def test_grau_laco_soma_2():
    nodes_dict = _nodes_dict([1, 2, 3])
    # way fechado: 1-2-3-1 (from == to == 1)
    ways = [_way(1, [1, 2, 3, 1], {"highway": "residential"})]
    arcos, _, _ = constroi_arcos(ways, nodes_dict)
    assert len(arcos) == 1  # nao quebra no laço
    g = grau(arcos)
    assert g[1] == 2


def test_laco_way_fechado_nao_quebra():
    nodes_dict = _nodes_dict([1, 2, 3, 4])
    ways = [_way(1, [1, 2, 3, 4, 1], {"highway": "residential"})]
    arcos, _, _ = constroi_arcos(ways, nodes_dict)
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
    arcos, _, _ = constroi_arcos(ways, nodes_dict)
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
    arcos, n_orfaos, _ = constroi_arcos(ways, nodes_dict)
    assert n_orfaos == 0
    assert len(arcos) == n - 1

    node_scc = componentes_fortes(arcos)
    # oneway "no" -> bidirecional -> toda a cadeia e uma unica SCC
    assert len(set(node_scc.values())) == 1
    assert len(node_scc) == n


# --- classifica_modos ---------------------------------------------------

def test_classifica_modos_primary_ambos():
    assert classifica_modos({"highway": "primary"}) == {"veicular": True, "pedestre": True}


def test_classifica_modos_motorway_so_veicular():
    assert classifica_modos({"highway": "motorway"}) == {"veicular": True, "pedestre": False}


def test_classifica_modos_footway_so_pedestre():
    assert classifica_modos({"highway": "footway"}) == {"veicular": False, "pedestre": True}


def test_classifica_modos_construction_nenhum():
    assert classifica_modos({"highway": "construction"}) == {"veicular": False, "pedestre": False}


def test_classifica_modos_area_yes_nenhum():
    assert classifica_modos({"highway": "residential", "area": "yes"}) == {"veicular": False, "pedestre": False}


def test_classifica_modos_access_no_nenhum():
    assert classifica_modos({"highway": "residential", "access": "no"}) == {"veicular": False, "pedestre": False}


def test_classifica_modos_access_no_foot_yes_so_pedestre():
    assert classifica_modos({"highway": "residential", "access": "no", "foot": "yes"}) == \
        {"veicular": False, "pedestre": True}


def test_classifica_modos_motor_vehicle_no_em_residential_so_pedestre():
    assert classifica_modos({"highway": "residential", "motor_vehicle": "no"}) == \
        {"veicular": False, "pedestre": True}


def test_classifica_modos_access_private_em_service_segue_veicular():
    modos = classifica_modos({"highway": "service", "access": "private"})
    assert modos["veicular"] is True


def test_classifica_modos_highway_desconhecido_nenhum():
    assert classifica_modos({"highway": "algo_nunca_visto"}) == {"veicular": False, "pedestre": False}


def test_classifica_modos_vehicle_yes_nao_promove_footway():
    # override so restaura/nega um modo cuja base ja permite; nao promove
    # um highway fundamentalmente nao-veicular so por causa de vehicle=yes.
    assert classifica_modos({"highway": "footway", "vehicle": "yes"}) == \
        {"veicular": False, "pedestre": True}


def test_classifica_modos_busway_nenhum():
    # busway = faixa exclusiva de onibus/BRT, nao rede de carros — fica em
    # HIGHWAY_DESCARTE (medido em Contagem/RMBH: 33 mao_unica_sem_saida
    # espurios quando ainda contava como veicular).
    assert classifica_modos({"highway": "busway"}) == {"veicular": False, "pedestre": False}


# --- descartados na construcao de arcos ----------------------------------

def test_descartados_contados_por_highway():
    nodes_dict = _nodes_dict([1, 2, 3, 4, 5, 6, 7, 8])
    ways = [
        _way(1, [1, 2], {"highway": "residential"}),
        _way(2, [3, 4], {"highway": "construction"}),
        _way(3, [5, 6], {"highway": "construction"}),
        _way(4, [7, 8], {"highway": "platform"}),
    ]
    arcos, n_orfaos, descartados = constroi_arcos(ways, nodes_dict)
    assert len(arcos) == 1
    assert arcos[0]["highway"] == "residential"
    assert descartados == {"construction": 2, "platform": 1}


def test_arco_carrega_flags_veicular_pedestre():
    nodes_dict = _nodes_dict([1, 2, 3, 4])
    ways = [
        _way(1, [1, 2], {"highway": "residential"}),
        _way(2, [3, 4], {"highway": "footway"}),
    ]
    arcos, _, _ = constroi_arcos(ways, nodes_dict)
    por_way = {a["way_id"]: a for a in arcos}
    assert por_way[1]["veicular"] is True and por_way[1]["pedestre"] is True
    assert por_way[2]["veicular"] is False and por_way[2]["pedestre"] is True


# --- footway solto nao vira ilha na rede veicular -------------------------

def test_footway_solto_nao_vira_ilha_na_rede_veicular():
    nodes_dict = _nodes_dict([1, 2, 3, 4, 5])
    ways = [
        _way(1, [1, 2, 3], {"highway": "residential"}),
        # footway isolado: sem no compartilhado com a rede veicular
        _way(2, [4, 5], {"highway": "footway"}),
    ]
    arcos, _, _ = constroi_arcos(ways, nodes_dict)

    diag_v = diagnostica(arcos, "veicular")
    assert len(diag_v["comp_tam"]) == 1
    assert diag_v["ilhas"] == []

    # na rede pedestre o footway solto SEGUE sendo uma componente separada
    # (residential tambem eh pedestre, entao o footway forma ilha la)
    diag_p = diagnostica(arcos, "pedestre")
    assert len(diag_p["comp_tam"]) == 2
    assert len(diag_p["ilhas"]) == 1


# --- diagnostica(rede=...) -------------------------------------------------

def test_diagnostica_rede_invalida_levanta_valueerror():
    nodes_dict = _nodes_dict([1, 2])
    ways = [_way(1, [1, 2], {"highway": "residential"})]
    arcos, _, _ = constroi_arcos(ways, nodes_dict)
    with pytest.raises(ValueError):
        diagnostica(arcos, "invalida")


def test_diagnostica_pedestre_ignora_oneway_mao_unica_sempre_vazia():
    # mesmo grafo do teste de mao-unica-sem-saida veicular: na rede
    # pedestre o oneway e ignorado (tudo "ambos"), entao nao ha beco
    # sem saida.
    nodes_dict = _nodes_dict([1, 2, 3, 4])
    ways = [
        _way(1, [1, 2], {"highway": "residential", "oneway": "no"}),
        _way(2, [2, 4], {"highway": "residential", "oneway": "no"}),
        _way(3, [4, 1], {"highway": "residential", "oneway": "no"}),
        _way(4, [2, 3], {"highway": "residential", "oneway": "yes"}),
    ]
    arcos, _, _ = constroi_arcos(ways, nodes_dict)

    diag_v = diagnostica(arcos, "veicular")
    assert 3 in diag_v["mao_unica_sem_saida"]

    diag_p = diagnostica(arcos, "pedestre")
    assert diag_p["mao_unica_sem_saida"] == []


# --- velocidade_kmh (atributo de custo p/ roteirização, ex.: logis) -------

def test_velocidade_kmh_maxspeed_numerico():
    assert velocidade_kmh({"maxspeed": "60"}) == 60.0


def test_velocidade_kmh_maxspeed_mph_converte():
    # 50 mph * 1.60934 ~= 80.467
    assert velocidade_kmh({"maxspeed": "50 mph"}) == pytest.approx(80.467, abs=0.01)


def test_velocidade_kmh_maxspeed_inutilizavel_cai_no_highway():
    # "none"/vazio/lixo (sem digito) nao dao um maxspeed usavel -> tabela
    # por highway (aqui, "residential" -> 40.0)
    assert velocidade_kmh({"maxspeed": "none", "highway": "residential"}) == 40.0
    assert velocidade_kmh({"maxspeed": "", "highway": "residential"}) == 40.0
    assert velocidade_kmh({"maxspeed": "lixo", "highway": "residential"}) == 40.0
    assert velocidade_kmh({"highway": "residential"}) == 40.0


def test_velocidade_kmh_highway_conhecido_da_tabela():
    assert velocidade_kmh({"highway": "primary"}) == 70.0
    assert velocidade_kmh({"highway": "motorway"}) == 110.0


def test_velocidade_kmh_highway_fora_da_tabela_usa_default_40():
    assert velocidade_kmh({"highway": "cycleway"}) == 40.0
    assert velocidade_kmh({}) == 40.0


def test_constroi_arcos_guarda_maxspeed_cru_no_dict_do_arco():
    nodes_dict = _nodes_dict([1, 2])
    ways = [_way(1, [1, 2], {"highway": "residential", "maxspeed": "60"})]
    arcos, _, _ = constroi_arcos(ways, nodes_dict)
    assert len(arcos) == 1
    assert arcos[0]["maxspeed"] == "60"

    # way sem maxspeed -> string vazia, nao ausencia de chave
    ways_sem = [_way(2, [1, 2], {"highway": "residential"})]
    arcos_sem, _, _ = constroi_arcos(ways_sem, nodes_dict)
    assert arcos_sem[0]["maxspeed"] == ""
