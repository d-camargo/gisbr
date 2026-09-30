# -*- coding: utf-8 -*-
"""Testes de escala máxima, filtro por UF e cobertura estadual no catálogo (D4, D5, D6)."""

import pytest
from gisbr.core.sources import SOURCES
from gisbr.core.constants import UF_ABBREV_TO_CODE

ESCALAS_VALIDAS = {"municipio", "regional", "estado", "macrorregiao"}


def test_toda_fonte_tem_escala_max_valida():
    """1. Toda fonte do catálogo deve declarar escala_max com valor permitido (D4)."""
    assert len(SOURCES) > 0
    for fonte in SOURCES:
        fid = fonte.get("id")
        assert "escala_max" in fonte, f"Fonte '{fid}' não possui a chave 'escala_max'"
        escala = fonte["escala_max"]
        assert escala in ESCALAS_VALIDAS, (
            f"Fonte '{fid}' tem escala_max inválida: {escala!r} "
            f"(esperado um de {ESCALAS_VALIDAS})"
        )


def test_invariante_d6():
    """2. Invariante do D6: toda fonte com filtro CQL (cql_codigo/cql_nome)

    e escala_max em estado ou macrorregiao deve ter a chave filtro['uf'].
    """
    cql_tipos = {"cql_codigo", "cql_nome"}
    escalas_agregadas = {"estado", "macrorregiao"}
    fontes_encontradas = []

    for fonte in SOURCES:
        filtro = fonte.get("filtro") or {}
        tipo_filtro = filtro.get("tipo")
        escala = fonte.get("escala_max")

        if tipo_filtro in cql_tipos and escala in escalas_agregadas:
            fid = fonte["id"]
            fontes_encontradas.append(fid)
            assert "uf" in filtro, (
                f"Fonte '{fid}' (tipo={tipo_filtro}, escala={escala}) viola "
                "o invariante do D6: falta filtro['uf']"
            )
            cfg_uf = filtro["uf"]
            assert isinstance(cfg_uf, dict), f"filtro['uf'] de '{fid}' deve ser dict"
            assert "campo" in cfg_uf and isinstance(cfg_uf["campo"], str) and cfg_uf["campo"], (
                f"filtro['uf']['campo'] ausente ou vazio na fonte '{fid}'"
            )
            assert cfg_uf.get("modo") in {"sigla", "prefixo"}, (
                f"filtro['uf']['modo'] de '{fid}' deve ser 'sigla' ou 'prefixo', "
                f"recebeu: {cfg_uf.get('modo')!r}"
            )

    # As 4 fontes medidas no D6 devem estar presentes
    quatro_esperadas = {
        "minfra_ferrovias",
        "icmbio_embargos",
        "ibge_areas_urbanizadas",
        "ibge_aglomerados_subnormais",
    }
    assert set(fontes_encontradas) == quatro_esperadas


def test_ufs_lista_de_siglas_validas():
    """3. 'ufs', quando existe, deve ser uma lista não-vazia de siglas válidas de UFs (D5)."""
    fontes_com_ufs = 0
    for fonte in SOURCES:
        if "ufs" in fonte:
            fid = fonte["id"]
            ufs = fonte["ufs"]
            assert isinstance(ufs, list), f"'ufs' na fonte '{fid}' deve ser uma lista"
            assert len(ufs) > 0, f"'ufs' na fonte '{fid}' não pode ser vazia"
            for sigla in ufs:
                assert sigla in UF_ABBREV_TO_CODE, (
                    f"Sigla '{sigla}' na fonte '{fid}' não é uma UF brasileira válida"
                )
            fontes_com_ufs += 1

    # der_mg_rodovias deve ter ufs == ["MG"]
    der = next((f for f in SOURCES if f["id"] == "der_mg_rodovias"), None)
    assert der is not None
    assert der.get("ufs") == ["MG"]


def test_fontes_osm_sao_municipio():
    """4. Fontes com protocolo OSM devem ter escala_max == 'municipio' (D4)."""
    osm_fontes = [f for f in SOURCES if f.get("protocolo") == "osm"]
    assert len(osm_fontes) >= 2
    for fonte in osm_fontes:
        fid = fonte["id"]
        assert fonte.get("escala_max") == "municipio", (
            f"Fonte OSM '{fid}' deve ter escala_max == 'municipio', "
            f"mas tem {fonte.get('escala_max')!r}"
        )
