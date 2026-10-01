# -*- coding: utf-8 -*-
"""Testes unitários para gisbr.core.rede_linhas (D10, etapas 1 a 6).

Rodam SEM QGIS (o módulo é stdlib pura):
    python3 -m pytest -q tests/test_rede_linhas.py tests/test_osm_topologia.py
"""

import math
from typing import Tuple

import pytest

from gisbr.core.osm_topologia import diagnostica
from gisbr.core.rede_linhas import (
    TOL_NO_M,
    TOL_SNAP_M,
    filtra_existentes,
    monta_rede,
)


def _m(x_m: float, y_m: float, lon0: float = -44.0, lat0: float = -20.0) -> Tuple[float, float]:
    """Converte deslocamentos métricos (x, y) em coordenadas (lon, lat) EPSG:4674."""
    r = 6371000.0
    phi0 = math.radians(lat0)
    lon = lon0 + math.degrees(x_m / (r * math.cos(phi0)))
    lat = lat0 + math.degrees(y_m / r)
    return (lon, lat)


def test_constantes_d10():
    """Valida as constantes de tolerância do D10."""
    assert TOL_NO_M == 1.0
    assert TOL_SNAP_M == 10.0


def test_duas_linhas_tocam_na_ponta_um_no_compartilhado_dois_arcos():
    """Duas linhas que se tocam exatamente na ponta -> 1 nó compartilhado, 2 arcos."""
    p0 = _m(0, 0)
    p1 = _m(50, 0)
    p2 = _m(100, 0)

    linhas = [
        {"fid": "l1", "coords": [p0, p1], "attrs": {"nome": "Rua 1"}},
        {"fid": "l2", "coords": [p1, p2], "attrs": {"nome": "Rua 2"}},
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    assert len(arcos) == 2
    assert len(nos) == 3
    # O nó intermediário é compartilhado (to_node de l1 == from_node de l2)
    assert arcos[0]["to_node"] == arcos[1]["from_node"]
    assert correcoes == []
    assert contagens["ponta_unificada"] == 0
    assert contagens["arcos"] == 2
    assert contagens["nos"] == 3


def test_pontas_a_meio_metro_unificadas():
    """Pontas a 0,5 m -> 1 nó compartilhado + correção ponta_unificada."""
    p0 = _m(0, 0)
    p1 = _m(50, 0)
    p1_deslocado = _m(50, 0.5)
    p2 = _m(100, 0.5)

    linhas = [
        {"fid": "l1", "coords": [p0, p1]},
        {"fid": "l2", "coords": [p1_deslocado, p2]},
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    assert len(arcos) == 2
    assert len(nos) == 3
    assert arcos[0]["to_node"] == arcos[1]["from_node"]

    # Correção registrada com tipo ponta_unificada
    assert contagens["ponta_unificada"] == 1
    unif = [c for c in correcoes if c["tipo"] == "ponta_unificada"]
    assert len(unif) == 1
    assert unif[0]["fid"] == "l2"
    assert "0.50 m" in unif[0]["detalhe"]


def test_ponta_a_6m_do_meio_quebra_em_3_arcos_e_conecta():
    """Ponta a 6 m do meio de outra linha -> a linha alvo é quebrada (3 arcos) + correção ponta_conectada."""
    # Linha alvo horizontal de 0 a 100 m
    p0 = _m(0, 0)
    p1 = _m(100, 0)
    # Linha incidente vertical a 6 m do meio (50, 0)
    p_snap = _m(50, 6)
    p_fim = _m(50, 50)

    linhas = [
        {"fid": "alvo", "coords": [p0, p1], "attrs": {"via": "Avenida"}},
        {"fid": "incidente", "coords": [p_snap, p_fim], "attrs": {"via": "Travessa"}},
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    # Linha alvo quebrada em 2 + incidente em 1 = 3 arcos
    assert len(arcos) == 3
    assert contagens["ponta_conectada"] == 1

    con = [c for c in correcoes if c["tipo"] == "ponta_conectada"]
    assert len(con) == 1
    assert con[0]["fid"] == "incidente"
    assert "6.00 m" in con[0]["detalhe"]

    # Todas as 3 vias se conectam no nó de junção
    no_juncao = con[0]["x"], con[0]["y"]
    # Verifica que existe um nó comum aos 3 arcos
    nos_arco0 = {arcos[0]["from_node"], arcos[0]["to_node"]}
    nos_arco1 = {arcos[1]["from_node"], arcos[1]["to_node"]}
    nos_arco2 = {arcos[2]["from_node"], arcos[2]["to_node"]}
    no_comum = (nos_arco0 & nos_arco1 & nos_arco2)
    assert len(no_comum) == 1

    # Diagnóstico veicular passa e forma 1 componente de 3 arcos
    diag = diagnostica(arcos, "veicular")
    assert diag["comp_tam"] == {0: 3}
    assert len(diag["ilhas"]) == 0
    # O nó comum tem grau 3
    assert diag["grau"][list(no_comum)[0]] == 3


def test_ponta_a_25m_nao_conecta():
    """Ponta a 25 m -> NÃO conecta (> TOL_SNAP_M = 10 m)."""
    p0 = _m(0, 0)
    p1 = _m(100, 0)
    p_longe = _m(50, 25)
    p_fim = _m(50, 60)

    linhas = [
        {"fid": "alvo", "coords": [p0, p1]},
        {"fid": "incidente", "coords": [p_longe, p_fim]},
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    assert len(arcos) == 2
    assert contagens["ponta_conectada"] == 0
    assert not any(c["tipo"] == "ponta_conectada" for c in correcoes)

    # Duas componentes desconexas
    diag = diagnostica(arcos, "veicular")
    assert len(diag["comp_tam"]) == 2
    assert len(diag["ilhas"]) == 1


def test_cruzamento_x_sem_vertice_comum_nao_quebra():
    """X sem vértice comum -> NÃO quebra (pode ser viaduto/trincheira)."""
    # Linha horizontal de (0, 50) a (100, 50)
    p0 = _m(0, 50)
    p1 = _m(100, 50)
    # Linha vertical de (50, 0) a (50, 100)
    q0 = _m(50, 0)
    q1 = _m(50, 100)

    linhas = [
        {"fid": "h", "coords": [p0, p1]},
        {"fid": "v", "coords": [q0, q1]},
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    assert len(arcos) == 2
    assert len(nos) == 4
    assert contagens["ponta_conectada"] == 0

    diag = diagnostica(arcos, "veicular")
    assert len(diag["comp_tam"]) == 2


def test_multiparte_vira_linhas_com_mesmos_attrs():
    """Multiparte -> partes viram linhas com os mesmos attrs."""
    p0, p1 = _m(0, 0), _m(20, 0)
    p2, p3 = _m(30, 0), _m(50, 0)

    linhas = [
        {
            "fid": "multi_1",
            "partes": [[p0, p1], [p2, p3]],
            "attrs": {"codigo": "BR-040", "jurisdicao": "Federal"},
        }
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    assert len(arcos) == 2
    assert contagens["multipartes_explodidas"] == 2
    for a in arcos:
        assert a["fid"] == "multi_1"
        assert a["attrs"]["codigo"] == "BR-040"
        assert a["attrs"]["jurisdicao"] == "Federal"


def test_parte_degenerada_descartada_e_contada():
    """Parte degenerada -> descartada + contada."""
    p0 = _m(0, 0)
    p1 = _m(20, 0)

    linhas = [
        # Menos de 2 pontos distintos
        {"fid": "deg_1", "partes": [[p0]]},
        {"fid": "deg_2", "partes": [[p0, p0]]},
        # Linha válida
        {"fid": "valida", "partes": [[p0, p1]]},
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    assert len(arcos) == 1
    assert arcos[0]["fid"] == "valida"
    assert contagens["geometria_degenerada"] == 2

    deg_corr = [c for c in correcoes if c["tipo"] == "geometria_degenerada"]
    assert len(deg_corr) == 2
    fids_deg = {c["fid"] for c in deg_corr}
    assert fids_deg == {"deg_1", "deg_2"}


def test_duas_linhas_identicas_colapsam_em_um_arco_com_coincidentes():
    """Duas linhas idênticas -> 1 arco com coincidentes='a;b'."""
    p0 = _m(0, 0)
    p1 = _m(50, 0)

    linhas = [
        {"fid": "a", "coords": [p0, p1]},
        {"fid": "b", "coords": [p0, p1]},
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    assert len(arcos) == 1
    assert arcos[0]["coincidentes"] == "a;b"
    assert contagens["coincidente_colapsado"] == 1

    coinc_corr = [c for c in correcoes if c["tipo"] == "coincidente_colapsado"]
    assert len(coinc_corr) == 1
    assert "a;b" in coinc_corr[0]["detalhe"]


def test_duas_linhas_identicas_sentido_oposto_colapsam():
    """Duas linhas com sentidos opostos colapsam (par de nós não ordenado)."""
    p0 = _m(0, 0)
    p1 = _m(50, 0)

    linhas = [
        {"fid": "ida", "coords": [p0, p1]},
        {"fid": "volta", "coords": [p1, p0]},
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    assert len(arcos) == 1
    assert arcos[0]["coincidentes"] == "ida;volta"
    assert contagens["coincidente_colapsado"] == 1


def test_saida_passa_por_diagnostica_com_componentes_corretas():
    """A saída passa por osm_topologia.diagnostica(arcos, 'veicular') sem erro e com componentes corretas."""
    # Componente 1: triângulo de 3 vias conectadas
    p0 = _m(0, 0)
    p1 = _m(50, 0)
    p2 = _m(25, 40)
    # Componente 2 (ilha): 1 via isolada
    q0 = _m(200, 200)
    q1 = _m(250, 200)

    linhas = [
        {"fid": "t1", "coords": [p0, p1]},
        {"fid": "t2", "coords": [p1, p2]},
        {"fid": "t3", "coords": [p2, p0]},
        {"fid": "isolada", "coords": [q0, q1]},
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    assert len(arcos) == 4
    diag = diagnostica(arcos, "veicular")

    # Componente principal (tamanho 3) e ilha (tamanho 1)
    assert len(diag["comp_tam"]) == 2
    assert diag["comp_tam"][0] == 3
    assert diag["comp_tam"][1] == 1
    assert len(diag["ilhas"]) == 1

    # No triângulo, todos os 3 nós têm grau 2 (sem pontas soltas)
    # Na ilha, os 2 nós têm grau 1 (2 pontas soltas)
    assert len(diag["pontas_soltas"]) == 2


def test_filtro_existentes_dnit_ds_superfi():
    """`ds_superfi` PLA sai e PAV/N_PAV ficam."""
    feicoes = [
        {"ds_superfi": "PLA", "nome": "Trecho 1"},
        {"ds_superfi": "PAV", "nome": "Trecho 2"},
        {"ds_superfi": "N_PAV", "nome": "Trecho 3"},
    ]
    excluir = {"campo": "ds_superfi", "valores": ["PLA"]}
    mantidas, removidas = filtra_existentes(feicoes, excluir)

    assert len(mantidas) == 2
    assert len(removidas) == 1
    assert [f["ds_superfi"] for f in mantidas] == ["PAV", "N_PAV"]
    assert [f["ds_superfi"] for f in removidas] == ["PLA"]


def test_filtro_existentes_minfra_tres_valores_e_desativada_fica():
    """Os 3 valores da MInfra (Planejada, Estudo, Em Obra) saem e Desativada fica."""
    feicoes = [
        {"tip_situac": "Planejada"},
        {"tip_situac": "Estudo"},
        {"tip_situac": "Em Obra"},
        {"tip_situac": "Desativada"},
        {"tip_situac": "Em Operação"},
    ]
    excluir = {"campo": "tip_situac", "valores": ["Planejada", "Estudo", "Em Obra"]}
    mantidas, removidas = filtra_existentes(feicoes, excluir)

    assert len(mantidas) == 2
    assert len(removidas) == 3
    assert [f["tip_situac"] for f in mantidas] == ["Desativada", "Em Operação"]
    assert [f["tip_situac"] for f in removidas] == ["Planejada", "Estudo", "Em Obra"]


def test_filtro_existentes_espacos_strip():
    """' PLA ' com espaços sai."""
    feicoes = [
        {"ds_superfi": " PLA "},
        {"ds_superfi": "PAV"},
    ]
    excluir = {"campo": "ds_superfi", "valores": ["PLA"]}
    mantidas, removidas = filtra_existentes(feicoes, excluir)

    assert len(mantidas) == 1
    assert len(removidas) == 1
    assert mantidas[0]["ds_superfi"] == "PAV"
    assert removidas[0]["ds_superfi"] == " PLA "


def test_filtro_existentes_campo_ausente_e_valor_nulo_ficam():
    """Campo ausente na feição ou valor nulo (None) -> fica."""
    feicoes = [
        {"outro_campo": "qualquer"},
        {"ds_superfi": None},
        {"ds_superfi": "PLA"},
    ]
    excluir = {"campo": "ds_superfi", "valores": ["PLA"]}
    mantidas, removidas = filtra_existentes(feicoes, excluir)

    assert len(mantidas) == 2
    assert len(removidas) == 1
    assert mantidas[0] == {"outro_campo": "qualquer"}
    assert mantidas[1] == {"ds_superfi": None}
    assert removidas[0]["ds_superfi"] == "PLA"


def test_filtro_existentes_excluir_none_mantem_tudo():
    """excluir=None mantém todas as feições."""
    feicoes = [
        {"ds_superfi": "PLA"},
        {"ds_superfi": "PAV"},
    ]
    mantidas, removidas = filtra_existentes(feicoes, None)

    assert len(mantidas) == 2
    assert len(removidas) == 0
    assert mantidas == feicoes


def test_filtro_existentes_suporta_chave_attrs():
    """Suporta feições com dicionário de atributos sob chave 'attrs'."""
    feicoes = [
        {"fid": 1, "attrs": {"ds_superfi": "PLA"}},
        {"fid": 2, "attrs": {"ds_superfi": "PAV"}},
    ]
    excluir = {"campo": "ds_superfi", "valores": ["PLA"]}
    mantidas, removidas = filtra_existentes(feicoes, excluir)

    assert len(mantidas) == 1
    assert len(removidas) == 1
    assert mantidas[0]["fid"] == 2
    assert removidas[0]["fid"] == 1


def test_linha_diagonal_longa_nao_explode_memoria_e_conecta_em_t():
    """Segmento diagonal de ~1 grau: o índice cresce com o comprimento, não com a bbox (regressão de OOM)."""
    # Linha alvo: diagonal (0, 0) -> (1, 1) em graus (~157 km)
    alvo = [(0.0, 0.0), (1.0, 1.0)]
    # Incidente: ponta ~5 m (perpendicular) ao lado do meio da diagonal, seguindo para o norte
    meio = (0.5, 0.5)
    p_snap = _m(0, 7, lon0=meio[0], lat0=meio[1])
    p_fim = _m(0, 57, lon0=meio[0], lat0=meio[1])

    linhas = [
        {"fid": "diagonal", "coords": alvo, "attrs": {"via": "Rodovia"}},
        {"fid": "incidente", "coords": [p_snap, p_fim], "attrs": {"via": "Travessa"}},
    ]
    arcos, nos, correcoes, contagens = monta_rede(linhas)

    # Diagonal quebrada em 2 + incidente em 1 = 3 arcos; 4 nós (2 pontas + 1 fim + 1 junção)
    assert len(arcos) == 3
    assert len(nos) == 4
    assert contagens["ponta_conectada"] == 1
    con = [c for c in correcoes if c["tipo"] == "ponta_conectada"]
    assert len(con) == 1
    assert con[0]["fid"] == "incidente"


def _graus(arcos):
    graus = {}
    for a in arcos:
        for n in (a["from_node"], a["to_node"]):
            graus[n] = graus.get(n, 0) + 1
    return graus


def test_cruzamento_duas_pontas_mesmo_pe_conectam_no_mesmo_no():
    """Duas pontas opostas com o mesmo pé em A -> um único nó de grau 4."""
    linhas = [
        {"fid": "A", "coords": [(0, 0), (0.001, 0)], "attrs": {}},
        {"fid": "B", "coords": [(0.0005, 0.001), (0.0005, 0.00003)], "attrs": {}},
        {"fid": "C", "coords": [(0.0005, -0.001), (0.0005, -0.00003)], "attrs": {}},
    ]
    arcos, nos, _correcoes, contagens = monta_rede(linhas)

    assert len(arcos) == 4
    graus = _graus(arcos)
    centro = [n for n, g in graus.items() if g == 4]
    assert len(centro) == 1
    c = centro[0]
    for fid in ("B", "C"):
        arco = next(a for a in arcos if a["fid"] == fid)
        assert c in (arco["from_node"], arco["to_node"])
    for n, g in graus.items():
        if g == 1:
            assert _haversine(nos[n], nos[c]) >= 1.0
    assert contagens["ponta_conectada"] == 2


def test_no_compartilhado_perto_de_linha_move_todas_as_linhas():
    """Nó compartilhado por B e C perto de A: ambas migram para o mesmo pé."""
    linhas = [
        {"fid": "A", "coords": [(0, 0), (0.001, 0)], "attrs": {}},
        {"fid": "B", "coords": [(0.0004, 0.001), (0.0005, 0.000045)], "attrs": {}},
        {"fid": "C", "coords": [(0.0006, 0.001), (0.0005, 0.000045)], "attrs": {}},
    ]
    arcos, _nos, _correcoes, contagens = monta_rede(linhas)

    graus = _graus(arcos)
    b = next(a for a in arcos if a["fid"] == "B")
    c = next(a for a in arcos if a["fid"] == "C")
    no_b = b["to_node"]
    assert c["to_node"] == no_b
    assert graus[no_b] == 4
    arcos_a = [a for a in arcos if a["fid"] == "A"]
    assert len(arcos_a) == 2
    assert {arcos_a[0]["to_node"], arcos_a[1]["from_node"]} == {no_b}
    assert contagens["nos"] == 5


def test_pontas_em_pes_distintos_criam_nos_distintos():
    """Pontas a ~30 m uma da outra em A -> dois nós internos distintos."""
    linhas = [
        {"fid": "A", "coords": [(0, 0), (0.001, 0)], "attrs": {}},
        {"fid": "B", "coords": [(0.0003, 0.001), (0.0003, 0.00003)], "attrs": {}},
        {"fid": "C", "coords": [(0.0006, 0.001), (0.0006, 0.00003)], "attrs": {}},
    ]
    arcos, _nos, _correcoes, contagens = monta_rede(linhas)

    assert len([a for a in arcos if a["fid"] == "A"]) == 3
    graus = _graus(arcos)
    internos = [n for n, g in graus.items() if g == 3]
    assert len(internos) == 2
    assert contagens["ponta_conectada"] == 2


def _haversine(p, q):
    from gisbr.core.rede_linhas import _haversine_m
    return _haversine_m(p[0], p[1], q[0], q[1])
