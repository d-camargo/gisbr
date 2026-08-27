# -*- coding: utf-8 -*-
"""Testes do gerador do site de documentação (tools/build_docs_site.py).

Rodam SEM QGIS (usa apenas stdlib e pytest):
    python3 -m pytest tests/test_docs_site.py -q
"""
import configparser
from pathlib import Path

import pytest

from tools.build_docs_site import (
    EixoDesconhecido,
    _load_sources,
    gerar,
)

RAIZ = Path(__file__).resolve().parent.parent


def test_gera_os_seis_arquivos(tmp_path):
    escritas = gerar(RAIZ, tmp_path)
    assert sorted(escritas) == [
        "changelog.md",
        "referencia/algoritmos.en.md",
        "referencia/algoritmos.md",
        "referencia/fontes.en.md",
        "referencia/fontes.md",
    ]
    for pagina in escritas:
        assert (tmp_path / pagina).exists()


def test_toda_fonte_aparece_por_id(tmp_path):
    gerar(RAIZ, tmp_path)
    texto = (tmp_path / "referencia/fontes.md").read_text(encoding="utf-8")
    for fonte in _load_sources(RAIZ):
        assert "`%s`" % fonte["id"] in texto


def test_total_de_fontes_e_calculado(tmp_path):
    gerar(RAIZ, tmp_path)
    texto = (tmp_path / "referencia/fontes.md").read_text(encoding="utf-8")
    sources = _load_sources(RAIZ)
    assert "**%d fontes**" % len(sources) in texto


def test_eixo_desconhecido_deruba_o_gerador(tmp_path, monkeypatch):
    import tools.build_docs_site as gerador

    fonte_fantasma = [{"id": "fonte_fantasma", "eixo": "inexistente",
                       "nome": "Fonte fantasma", "protocolo": "wfs",
                       "filtro": {"tipo": "bbox"}, "licenca": "Publica"}]
    monkeypatch.setattr(gerador, "_load_sources", lambda raiz: fonte_fantasma)
    with pytest.raises(EixoDesconhecido) as excinfo:
        gerar(RAIZ, tmp_path)
    assert "fonte_fantasma" in str(excinfo.value)


def test_todo_algoritmo_aparece(tmp_path):
    from tools.build_docs_site import _load_constants
    gerar(RAIZ, tmp_path)
    texto = (tmp_path / "referencia/algoritmos.md").read_text(encoding="utf-8")
    v1, v2 = _load_constants(RAIZ)
    for funcao in v1:
        assert "`gisbr:%s`" % funcao in texto
    for funcao in v2:
        assert "`gisbr:%s_v2`" % funcao in texto
    assert "`gisbr:join_censo`" in texto


def test_changelog_traz_versao_corrente_primeiro(tmp_path):
    gerar(RAIZ, tmp_path)
    texto = (tmp_path / "changelog.md").read_text(encoding="utf-8")
    parser = configparser.ConfigParser()
    with open(RAIZ / "gisbr" / "metadata.txt", encoding="utf-8") as fh:
        parser.read_file(fh)
    versao = parser["general"]["version"]
    # primeira seção "##" do changelog é a versão corrente do pacote
    secoes = [linha[3:] for linha in texto.splitlines()
              if linha.startswith("## ")]
    assert secoes[0] == versao
    assert versao == "0.6.0"  # D8: a rodada do site não bumpa o plugin


def test_destino_alternativo(tmp_path):
    saida = tmp_path / "outro"
    escritas = gerar(RAIZ, saida)
    assert len(escritas) == 5
    assert (saida / "changelog.md").exists()
