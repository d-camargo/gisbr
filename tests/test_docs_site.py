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
    escritas = gerar(RAIZ, tmp_path, changelog_raiz=tmp_path / "CHANGELOG.md")
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
    gerar(RAIZ, tmp_path, changelog_raiz=tmp_path / "CHANGELOG.md")
    texto = (tmp_path / "referencia/fontes.md").read_text(encoding="utf-8")
    for fonte in _load_sources(RAIZ):
        assert "`%s`" % fonte["id"] in texto


def test_total_de_fontes_e_calculado(tmp_path):
    gerar(RAIZ, tmp_path, changelog_raiz=tmp_path / "CHANGELOG.md")
    texto = (tmp_path / "referencia/fontes.md").read_text(encoding="utf-8")
    sources = _load_sources(RAIZ)
    assert "**%d fontes**" % len(sources) in texto


def test_tabela_fontes_cabecalho_e_colunas(tmp_path):
    gerar(RAIZ, tmp_path, changelog_raiz=tmp_path / "CHANGELOG.md")
    pt = (tmp_path / "referencia/fontes.md").read_text(encoding="utf-8")
    en = (tmp_path / "referencia/fontes.en.md").read_text(encoding="utf-8")

    cab_pt = "| Fonte | `id` | Protocolo | Filtro | Escala máxima | UFs | Licença |"
    cab_en = "| Source | `id` | Protocol | Filter | Max. scale | UFs | License |"
    assert cab_pt in pt
    assert cab_en in en

    # Linhas de tabela devem ter 7 colunas (8 delimitadores '|')
    for texto, cab in ((pt, cab_pt), (en, cab_en)):
        for linha in texto.splitlines():
            if linha.startswith("|") and not linha.startswith("|---"):
                partes = [p.strip() for p in linha.strip().split("|")[1:-1]]
                assert len(partes) == 7, f"Linha com número incorreto de colunas: {linha}"


def test_tabela_fontes_escala_e_ufs_valores(tmp_path):
    gerar(RAIZ, tmp_path, changelog_raiz=tmp_path / "CHANGELOG.md")
    pt = (tmp_path / "referencia/fontes.md").read_text(encoding="utf-8")
    en = (tmp_path / "referencia/fontes.en.md").read_text(encoding="utf-8")

    # Escalas mapeadas em PT e EN
    assert "| Município |" in pt
    assert "| Municipality |" in en
    assert "| Estado |" in pt
    assert "| State |" in en
    assert "| Macrorregião |" in pt
    assert "| Macro-region |" in en
    assert "| Regional |" in pt
    assert "| Regional |" in en

    # Fonte com UF específica (der_mg_rodovias: ufs=['MG'], escala='estado')
    assert "| `der_mg_rodovias` | wfs | bbox + recorte | Estado | MG |" in pt
    assert "| `der_mg_rodovias` | wfs | bbox + clip | State | MG |" in en

    # Fonte de cobertura nacional (dnit_snv: sem ufs, escala='estado')
    assert "| `dnit_snv` | wfs | bbox + recorte | Estado | — |" in pt
    assert "| `dnit_snv` | wfs | bbox + clip | State | — |" in en

    # Fonte com base_rm (osm_vias: disponibilidade em RM com tag da release)
    assert (
        "| `osm_vias` | osm | bbox + recorte | "
        "município; RM (base pré-processada osm-20260929) | — |"
    ) in pt
    assert (
        "| `osm_vias` | osm | bbox + clip | "
        "municipality; metro region (pre-built base osm-20260929) | — |"
    ) in en


def test_eixo_desconhecido_deruba_o_gerador(tmp_path, monkeypatch):
    import tools.build_docs_site as gerador

    fonte_fantasma = [{"id": "fonte_fantasma", "eixo": "inexistente",
                       "nome": "Fonte fantasma", "protocolo": "wfs",
                       "filtro": {"tipo": "bbox"}, "licenca": "Publica"}]
    monkeypatch.setattr(gerador, "_load_sources", lambda raiz: fonte_fantasma)
    with pytest.raises(EixoDesconhecido) as excinfo:
        gerar(RAIZ, tmp_path, changelog_raiz=tmp_path / "CHANGELOG.md")
    assert "fonte_fantasma" in str(excinfo.value)


def test_todo_algoritmo_aparece(tmp_path):
    from tools.build_docs_site import _load_constants
    gerar(RAIZ, tmp_path, changelog_raiz=tmp_path / "CHANGELOG.md")
    texto = (tmp_path / "referencia/algoritmos.md").read_text(encoding="utf-8")
    v1, v2 = _load_constants(RAIZ)
    for funcao in sorted(v1):
        assert "`gisbr:%s`" % funcao in texto
    for funcao in sorted(v2):
        assert "`gisbr:%s_v2`" % funcao in texto
    assert "`gisbr:join_censo`" in texto
    assert "`gisbr:export_poi_gmns`" in texto
    assert "`gisbr:osm_network`" in texto


def test_changelog_traz_versao_corrente_primeiro(tmp_path):
    gerar(RAIZ, tmp_path, changelog_raiz=tmp_path / "CHANGELOG.md")
    texto = (tmp_path / "changelog.md").read_text(encoding="utf-8")
    parser = configparser.ConfigParser()
    with open(RAIZ / "gisbr" / "metadata.txt", encoding="utf-8") as fh:
        parser.read_file(fh)
    versao = parser["general"]["version"]
    # primeira seção "##" do changelog é a versão corrente do pacote
    secoes = [linha[3:] for linha in texto.splitlines()
              if linha.startswith("## ")]
    assert secoes[0] == versao
    # a versão corrente do pacote nesta rodada
    assert versao == "1.1.0"


def test_destino_alternativo(tmp_path):
    saida = tmp_path / "outro"
    escritas = gerar(RAIZ, saida, changelog_raiz=tmp_path / "CHANGELOG.md")
    assert len(escritas) == 5
    assert (saida / "changelog.md").exists()


def test_changelog_raiz_e_gerado(tmp_path):
    gerar(RAIZ, tmp_path, changelog_raiz=tmp_path / "CHANGELOG.md")
    # o arquivo gerado no destino alternativo traz o cabeçalho "não edite à mão"
    gerado = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert gerado.startswith(
        "# Changelog\n\n"
        "Generated from the `changelog` block of `gisbr/metadata.txt` by "
        "`tools/build_docs_site.py` — do not edit by hand.\n")
    # e o CHANGELOG.md commitado na raiz está em sincronia com o metadata.txt
    # (leitura only — no container do gate o repo entra montado read-only)
    caminho = RAIZ / "CHANGELOG.md"
    assert caminho.exists()
    texto = caminho.read_text(encoding="utf-8")
    assert texto.startswith(
        "# Changelog\n\n"
        "Generated from the `changelog` block of `gisbr/metadata.txt` by "
        "`tools/build_docs_site.py` — do not edit by hand.\n")
    assert texto == gerado
    parser = configparser.ConfigParser()
    with open(RAIZ / "gisbr" / "metadata.txt", encoding="utf-8") as fh:
        parser.read_file(fh)
    versao = parser["general"]["version"]
    assert ("## %s" % versao) in texto
