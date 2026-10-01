# -*- coding: utf-8 -*-
"""Testes unitários para o leitor de composição de Macrorregiões de Saúde (gisbr.core.macro_saude).

Rodam SEM QGIS (o módulo é stdlib pura):
    python3 -m pytest -q tests/test_macro_saude.py
"""

import pytest

from gisbr.core.macro_saude import (
    MacroSaudeError,
    listar,
    municipios,
    nome,
    reset_cache,
)


def setup_function():
    """Garante cache limpo a cada teste."""
    reset_cache()


@pytest.fixture
def csv_minimo(tmp_path):
    """Fixture com CSV mínimo cobrindo comentários e cabeçalho."""
    arquivo = tmp_path / "macro_saude_minimo.csv"
    conteudo = (
        "# Comentário de origem da base\n"
        "# Data de extração: 2026-10-01\n"
        "code_muni;nome_muni;sigla_uf;id_macsaud;nome_macsaud;id_regsaud;nome_regsaud\n"
        "3106200;Belo Horizonte;MG;3103;Centro;31016;Região Central\n"
        "3118601;Contagem;MG;3103;Centro;31016;Região Central\n"
        "3550308;São Paulo;SP;3501;Grande São Paulo;35001;Região SP\n"
    )
    arquivo.write_text(conteudo, encoding="utf-8")
    return str(arquivo)


def test_listar_mg_tem_16_itens_ordenados_por_nome():
    """Valida que listar('MG') tem 16 itens, ordenados por nome."""
    itens = listar("MG")
    assert len(itens) == 16

    nomes = [n for _, n in itens]
    assert nomes == sorted(nomes)

    ids = [mid for mid, _ in itens]
    assert "3103" in ids
    assert ("3103", "Centro") in itens

    # Suporta minúsculo e código UF numérico
    assert listar("mg") == itens
    assert listar(31) == itens


def test_municipios_3103_contem_belo_horizonte():
    """Valida que municipios('3103') contém ('3106200', 'Belo Horizonte')."""
    munis = municipios("3103")
    assert ("3106200", "Belo Horizonte") in munis
    assert len(munis) == 100
    assert all(isinstance(code, str) and isinstance(n, str) for code, n in munis)

    # Suporta ID como int
    assert municipios(3103) == munis


def test_nome_3103_retorna_centro():
    """Valida que nome('3103') == 'Centro'."""
    assert nome("3103") == "Centro"
    assert nome(3103) == "Centro"


def test_id_inexistente_retorna_lista_vazia_ou_none():
    """Valida que ID inexistente retorna lista vazia em municipios e None em nome."""
    assert municipios("9999") == []
    assert municipios(None) == []
    assert municipios("") == []

    assert nome("9999") is None
    assert nome(None) is None
    assert nome("") is None


def test_csv_ausente_lanca_macro_saude_error(tmp_path):
    """Valida que CSV ausente lança MacroSaudeError."""
    caminho_inexistente = str(tmp_path / "inexistente.csv")

    with pytest.raises(MacroSaudeError) as exc_info:
        listar("MG", csv_path=caminho_inexistente)
    assert "não encontrado" in str(exc_info.value)

    with pytest.raises(MacroSaudeError) as exc_info:
        municipios("3103", csv_path=caminho_inexistente)
    assert "não encontrado" in str(exc_info.value)

    with pytest.raises(MacroSaudeError) as exc_info:
        nome("3103", csv_path=caminho_inexistente)
    assert "não encontrado" in str(exc_info.value)


def test_fixture_csv_minimo_com_comentarios_e_cabecalho(csv_minimo):
    """Valida leitura de CSV mínimo com linhas de comentário e cabeçalho."""
    itens_mg = listar("MG", csv_path=csv_minimo)
    assert itens_mg == [("3103", "Centro")]

    munis_3103 = municipios("3103", csv_path=csv_minimo)
    assert munis_3103 == [("3106200", "Belo Horizonte"), ("3118601", "Contagem")]

    assert nome("3103", csv_path=csv_minimo) == "Centro"
    assert nome("3501", csv_path=csv_minimo) == "Grande São Paulo"


def test_csv_cabecalho_invalido(tmp_path):
    """Valida que CSV com cabeçalho incorreto lança MacroSaudeError."""
    arquivo = tmp_path / "invalido.csv"
    arquivo.write_text("# Comentário\ncoluna_errada;nome\n1;2\n", encoding="utf-8")

    with pytest.raises(MacroSaudeError) as exc_info:
        listar("MG", csv_path=str(arquivo))
    assert "Cabeçalho inválido" in str(exc_info.value)


def test_listar_todas_e_uf_inexistente():
    """Valida listagem geral sem filtro de UF e com UF inexistente."""
    todas = listar()
    assert len(todas) == 121
    nomes = [n for _, n in todas]
    assert nomes == sorted(nomes)

    assert listar("XX") == []
