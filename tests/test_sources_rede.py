# -*- coding: utf-8 -*-
"""Testes das chaves 'rede' e 'duplicidade' no catálogo de fontes (D9, D12, D13)."""

import pytest

from gisbr.core.sources import SOURCES

FONTES_REDE_ESPERADAS = {
    "dnit_snv",
    "minfra_ferrovias",
    "der_mg_rodovias",
    "go_malha_viaria",
    "pr_rodovias_der",
    "ibge_bc250_ferrovias",
}

TIPOS_REDE_VALIDOS = {"rodoviaria", "ferroviaria"}


def test_seis_fontes_tem_rede_tipo_valido_e_excluir_nao_vazio():
    """As 6 fontes do D9 têm rede.tipo válido e excluir não vazio (D9, D12)."""
    fontes_com_rede = [f for f in SOURCES if "rede" in f]
    ids_com_rede = {f["id"] for f in fontes_com_rede}

    assert ids_com_rede == FONTES_REDE_ESPERADAS, (
        f"Fontes com 'rede' divergem do esperado: {ids_com_rede} != {FONTES_REDE_ESPERADAS}"
    )

    for f in fontes_com_rede:
        fid = f["id"]
        cfg_rede = f["rede"]
        assert isinstance(cfg_rede, dict), f"rede em '{fid}' deve ser um dict"

        tipo = cfg_rede.get("tipo")
        assert tipo in TIPOS_REDE_VALIDOS, (
            f"Fonte '{fid}' tem tipo de rede inválido: {tipo!r} (esperado um de {TIPOS_REDE_VALIDOS})"
        )

        excluir = cfg_rede.get("excluir")
        assert isinstance(excluir, dict) and excluir, f"Fonte '{fid}' deve ter 'excluir' não vazio"

        campo = excluir.get("campo")
        assert isinstance(campo, str) and campo.strip(), (
            f"Fonte '{fid}' tem campo de exclusão inválido ou vazio: {campo!r}"
        )

        valores = excluir.get("valores")
        assert isinstance(valores, list) and len(valores) > 0, (
            f"Fonte '{fid}' deve ter lista de valores a excluir não vazia"
        )
        for val in valores:
            assert isinstance(val, str) and val.strip(), (
                f"Fonte '{fid}' tem valor a excluir inválido na lista: {val!r}"
            )


def test_toda_duplicidade_contra_aponta_para_fonte_com_rede_e_vem_antes():
    """Toda duplicidade.contra aponta para fonte existente com rede e vem antes no SOURCES (D9, D13)."""
    id_para_indice = {f["id"]: i for i, f in enumerate(SOURCES)}
    id_para_fonte = {f["id"]: f for f in SOURCES}

    fontes_com_duplicidade = [f for f in SOURCES if "duplicidade" in f]
    assert len(fontes_com_duplicidade) == 3, "Esperadas 3 fontes estaduais com duplicidade"

    fontes_dup_esperadas = {"der_mg_rodovias", "go_malha_viaria", "pr_rodovias_der"}
    assert {f["id"] for f in fontes_com_duplicidade} == fontes_dup_esperadas

    for f in fontes_com_duplicidade:
        fid = f["id"]
        dup = f["duplicidade"]
        assert isinstance(dup, dict), f"duplicidade em '{fid}' deve ser um dict"

        contra = dup.get("contra")
        assert contra in id_para_fonte, (
            f"Fonte '{fid}' declara duplicidade contra '{contra}', que não existe no SOURCES"
        )

        fonte_contra = id_para_fonte[contra]
        assert "rede" in fonte_contra, (
            f"Fonte alvo '{contra}' referenciada por '{fid}' não possui chave 'rede'"
        )

        idx_contra = id_para_indice[contra]
        idx_fonte = id_para_indice[fid]
        assert idx_contra < idx_fonte, (
            f"Fonte alvo '{contra}' (idx {idx_contra}) deve vir antes de '{fid}' (idx {idx_fonte}) no SOURCES"
        )

        assert dup.get("campo_jurisdicao") == "jurisdicao"
        assert dup.get("valor_federal") == "Federal"

    # Checa especificidades de campo_br
    der_mg = id_para_fonte["der_mg_rodovias"]["duplicidade"]
    assert der_mg.get("campo_br") == "codigo_rod"

    pr_der = id_para_fonte["pr_rodovias_der"]["duplicidade"]
    assert pr_der.get("campo_br") == "rod_num"

    go_malha = id_para_fonte["go_malha_viaria"]["duplicidade"]
    assert "campo_br" not in go_malha


def test_ibge_bc250_rodovias_nao_tem_rede():
    """ibge_bc250_rodovias não tem rede (D9)."""
    fonte_bc250_rod = next((f for f in SOURCES if f.get("id") == "ibge_bc250_rodovias"), None)
    assert fonte_bc250_rod is not None, "Fonte 'ibge_bc250_rodovias' não encontrada no SOURCES"
    assert "rede" not in fonte_bc250_rod, "Fonte 'ibge_bc250_rodovias' não deve ter chave 'rede'"
    assert "duplicidade" not in fonte_bc250_rod, "Fonte 'ibge_bc250_rodovias' não deve ter chave 'duplicidade'"
