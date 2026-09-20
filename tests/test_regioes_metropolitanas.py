# -*- coding: utf-8 -*-
"""Testes unitários para o leitor de composição de Regiões Metropolitanas (gisbr.core.regioes_metropolitanas).

Rodam SEM QGIS (o módulo é stdlib pura):
    python3 -m pytest -q tests/test_regioes_metropolitanas.py
"""

import os
import pytest
from gisbr.core.regioes_metropolitanas import (
    RegioesMetropolitanasError,
    codes,
    listar_por_uf,
    listar_todas,
    por_id,
    reset_cache,
)


def setup_function():
    """Garante cache limpo a cada teste."""
    reset_cache()


def test_total_entidades():
    """Valida o total de 84 entidades (RMs / Colares / RIDE) no catálogo."""
    todas = listar_todas()
    assert len(todas) == 84


def test_mg_regioes_metropolitanas():
    """Valida que MG possui 4 entidades, incluindo os dois 'Colar' e ordenação por nome."""
    rms_mg = listar_por_uf("MG")
    assert len(rms_mg) == 4

    nomes = [rm["nome"] for rm in rms_mg]
    ids = [rm["id"] for rm in rms_mg]

    # Verifica se a lista está estritamente ordenada por nome
    assert nomes == sorted(nomes)

    # Verifica os dois Colares em MG (04502 e 04602)
    colar_names = [n for n in nomes if "Colar" in n]
    assert len(colar_names) == 2
    assert "Colar Metropolitano" in colar_names
    assert "Colar Metropolitano de Belo Horizonte" in colar_names
    assert "04502" in ids
    assert "04602" in ids


def test_rm_belo_horizonte():
    """Valida RM de Belo Horizonte (04501) com 34 municípios e Belo Horizonte (3106200) entre eles."""
    rm_bh = por_id("04501")
    assert rm_bh is not None
    assert rm_bh["id"] == "04501"
    assert rm_bh["nome"] == "Região Metropolitana de Belo Horizonte"
    assert rm_bh["uf"] == "MG"

    # Verifica que possui 34 municípios
    municipios = rm_bh["municipios"]
    assert len(municipios) == 34

    # Verifica que codes("04501") retorna 34 códigos de 7 dígitos
    codigos_muni = codes("04501")
    assert len(codigos_muni) == 34
    assert all(isinstance(c, str) and len(c) == 7 for c in codigos_muni)

    # Verifica se Belo Horizonte (3106200) está presente
    assert "3106200" in codigos_muni
    muni_tuples = [m for m in municipios if m[0] == "3106200"]
    assert len(muni_tuples) == 1
    assert muni_tuples[0][1] == "Belo Horizonte"

    # Testa buscar com int (ex: 4501)
    assert por_id(4501) == rm_bh


def test_uf_sem_rm():
    """Valida que UF sem RM (ex: AC) devolve lista vazia."""
    rms_ac = listar_por_uf("AC")
    assert rms_ac == []

    rms_invalida = listar_por_uf("XX")
    assert rms_invalida == []


def test_por_id_e_codes_inexistentes():
    """Valida retorno de None e lista vazia para IDs inexistentes."""
    assert por_id("99999") is None
    assert por_id(None) is None
    assert codes("99999") == []


def test_arquivo_ausente_levanta_erro(tmp_path):
    """Valida que arquivo ausente levanta erro com a causa (e NÃO lista vazia)."""
    caminho_inexistente = str(tmp_path / "nao_existe.csv")

    with pytest.raises(RegioesMetropolitanasError) as exc_info:
        listar_por_uf("MG", csv_path=caminho_inexistente)

    assert "não encontrado" in str(exc_info.value)


def test_arquivo_corrompido_levanta_erro(tmp_path):
    """Valida que arquivo ilegível/sem cabeçalho levanta erro."""
    csv_corrompido = tmp_path / "corrompido.csv"
    csv_corrompido.write_text("linha1;sem;cabecalho;valido\n1;2;3;4;5\n", encoding="utf-8")

    with pytest.raises(RegioesMetropolitanasError) as exc_info:
        listar_por_uf("MG", csv_path=str(csv_corrompido))

    assert "Cabeçalho inválido" in str(exc_info.value) or "Nenhum cabeçalho" in str(exc_info.value)
