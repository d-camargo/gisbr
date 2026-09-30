# -*- coding: utf-8 -*-
"""Testes unitários para o leitor de composição da Divisão Regional (gisbr.core.divisao_regional).

Rodam SEM QGIS (o módulo é stdlib pura):
    python3 -m pytest -q tests/test_divisao_regional.py
"""

import pytest

from gisbr.core.divisao_regional import (
    DivisaoRegionalError,
    listar,
    municipios,
    nome,
    reset_cache,
)


def setup_function():
    """Garante cache limpo a cada teste."""
    reset_cache()


def test_micro_e_meso_mg_existem():
    """Valida que microrregiões e mesorregiões de MG existem e estão ordenadas por nome."""
    micros_mg = listar("micro", sigla_uf="MG")
    mesos_mg = listar("meso", sigla_uf="MG")

    assert len(micros_mg) == 66
    assert len(mesos_mg) == 12

    nomes_micro = [n for _, n in micros_mg]
    nomes_meso = [n for _, n in mesos_mg]

    assert nomes_micro == sorted(nomes_micro)
    assert nomes_meso == sorted(nomes_meso)

    ids_micro = [i for i, _ in micros_mg]
    ids_meso = [i for i, _ in mesos_mg]

    # Microrregião de Belo Horizonte (31030) e Mesorregião Metropolitana de BH (3107)
    assert "31030" in ids_micro
    assert "3107" in ids_meso


def test_contagem_em_meso_e_micro_bh():
    """Valida que Contagem (3118601) está na meso de BH e na micro de BH."""
    # Meso Metropolitana de BH: id 3107
    assert nome("meso", "3107") == "Metropolitana de Belo Horizonte"
    munis_meso = municipios("meso", "3107")
    codes_meso = [code for code, _ in munis_meso]
    assert "3118601" in codes_meso
    assert ("3118601", "Contagem") in munis_meso

    # Micro Belo Horizonte: id 31030
    assert nome("micro", "31030") == "Belo Horizonte"
    munis_micro = municipios("micro", "31030")
    codes_micro = [code for code, _ in munis_micro]
    assert "3118601" in codes_micro
    assert ("3118601", "Contagem") in munis_micro


def test_municipios_uf_mg():
    """Valida que municipios('uf', 'MG') retorna 853 municípios."""
    munis_mg = municipios("uf", "MG")
    assert len(munis_mg) == 853
    assert all(code.startswith("31") for code, _ in munis_mg)
    assert ("3118601", "Contagem") in munis_mg

    # Teste case-insensitive e código numérico
    assert municipios("uf", "mg") == munis_mg
    assert municipios("uf", 31) == munis_mg


def test_municipios_macro_3():
    """Valida que municipios('macro', '3') tem apenas municípios das UFs 31, 32, 33 e 35 (Sudeste)."""
    assert nome("macro", "3") == "Sudeste"
    munis_macro3 = municipios("macro", "3")

    # Sudeste: MG (31), ES (32), RJ (33), SP (35)
    ufs_presentes = {code[:2] for code, _ in munis_macro3}
    assert ufs_presentes == {"31", "32", "33", "35"}

    # Total esperado para a macrorregião Sudeste
    assert len(munis_macro3) == 1668

    # Também acessível pelo nome da região
    assert municipios("macro", "Sudeste") == munis_macro3


def test_csv_ausente_lanca_excecao(tmp_path):
    """Valida que arquivo CSV inexistente lança DivisaoRegionalError."""
    caminho_inexistente = str(tmp_path / "nao_existe.csv")

    with pytest.raises(DivisaoRegionalError) as exc_info:
        listar("micro", "MG", csv_path=caminho_inexistente)
    assert "não encontrado" in str(exc_info.value)

    with pytest.raises(DivisaoRegionalError) as exc_info:
        municipios("uf", "MG", csv_path=caminho_inexistente)
    assert "não encontrado" in str(exc_info.value)


def test_csv_corrompido_lanca_excecao(tmp_path):
    """Valida que arquivo sem cabeçalho válido lança DivisaoRegionalError."""
    csv_corrompido = tmp_path / "corrompido.csv"
    csv_corrompido.write_text("linha1;sem;cabecalho\n1;2;3\n", encoding="utf-8")

    with pytest.raises(DivisaoRegionalError) as exc_info:
        listar("meso", csv_path=str(csv_corrompido))
    assert "Cabeçalho inválido" in str(exc_info.value) or "Nenhum cabeçalho" in str(exc_info.value)


def test_listar_todas_e_macro():
    """Valida listagem geral sem filtro de UF."""
    macros = listar("macro")
    assert len(macros) == 5
    nomes_macro = [n for _, n in macros]
    assert nomes_macro == sorted(nomes_macro)
    assert "Sudeste" in nomes_macro

    mesos = listar("meso")
    assert len(mesos) == 137

    micros = listar("micro")
    assert len(micros) == 558


def test_tipos_invalidos():
    """Valida que tipos regionais não suportados levantam ValueError."""
    with pytest.raises(ValueError):
        listar("inexistente")

    with pytest.raises(ValueError):
        municipios("inexistente", "123")

    with pytest.raises(ValueError):
        nome("inexistente", "123")


def test_consultas_inexistentes():
    """Valida comportamento para IDs não encontrados ou None."""
    assert municipios("micro", "99999") == []
    assert municipios("uf", "XX") == []
    assert municipios("macro", None) == []

    assert nome("micro", "99999") == ""
    assert nome("meso", None) == ""
    assert nome("uf", "MG") == "Minas Gerais"
    assert nome("uf", "XX") == ""
