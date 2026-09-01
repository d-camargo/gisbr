#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera as páginas derivadas do site de documentação do GisBR.

Três páginas saem do CÓDIGO, nunca digitadas (decisão D3 do plano da rodada 9):

* ``referencia/fontes.md`` + ``.en.md``  <- ``gisbr/core/sources.py`` (SOURCES)
* ``referencia/algoritmos.md`` + ``.en.md`` <- ``gisbr/core/constants.py``
  (GEO_BY_FUNCTION / GEO_BY_FUNCTION_V2) + a linha do ``join_censo``
* ``changelog.md``                     <- ``gisbr/metadata.txt`` (configparser,
  o mesmo parser do plugins.qgis.org)

Stdlib pura, sem QGIS: é a condição do runner do GitHub Actions. As páginas
geradas NÃO vão para o git (D4) — rode este script antes de qualquer
``mkdocs build`` / ``mkdocs serve`` (o Makefile e o workflow fazem isso).

Uso:

    python3 tools/build_docs_site.py            # gera em docs/
    python3 tools/build_docs_site.py -d /tmp/x  # gera em outro diretório
"""
import argparse
import configparser
import importlib.util
import re
from pathlib import Path

# Mapa dos eixos (D5): os rótulos oficiais moram em gui/diagnostico_dock.py,
# que importa PyQGIS e não roda no CI; duplicar 8 strings é aceitável,
# duplicar SILENCIOSAMENTE não é — eixo fora daqui derruba o build.
EIXOS = {
    "transportes": (1, "Transportes", "Transport"),
    "saneamento": (2, "Drenagem e Saneamento", "Drainage and Sanitation"),
    "demografia": (3, "Demografia", "Demographics"),
    "ambiental": (4, "Ambiental", "Environment"),
    "educacao": (5, "Educação", "Education"),
    "saude": (6, "Saúde", "Health"),
    "urbano": (7, "Urbano", "Urban"),
    "pol-admin": (8, "Político-administrativo", "Administrative"),
    # contexto: fora da contagem de eixos, como no painel
    "contexto": (None, "Contexto", "Context"),
}


class EixoDesconhecido(Exception):
    """SOURCES ganhou um eixo que o gerador (e o site) não conhece."""


# ---------------------------------------------------------------------------
# Carregamento (por caminho: não depende do CWD nem de pacote instalado)
# ---------------------------------------------------------------------------

def _load_module(caminho):
    spec = importlib.util.spec_from_file_location(caminho.stem, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _load_sources(raiz):
    return _load_module(raiz / "gisbr" / "core" / "sources.py").SOURCES


def _load_constants(raiz):
    modulo = _load_module(raiz / "gisbr" / "core" / "constants.py")
    return modulo.GEO_BY_FUNCTION, modulo.GEO_BY_FUNCTION_V2


def _load_metadata(raiz):
    parser = configparser.ConfigParser()
    with open(raiz / "gisbr" / "metadata.txt", encoding="utf-8") as fh:
        parser.read_file(fh)
    return parser["general"]["version"], parser["general"]["changelog"]


# ---------------------------------------------------------------------------
# Fontes (referencia/fontes.md / .en.md)
# ---------------------------------------------------------------------------

_FILTRO_PT = {
    "cql_codigo": "código IBGE (CQL)",
    "cql_nome": "nome do município (CQL)",
    "bbox": "bbox + recorte",
    "code": "código IBGE",
}
_FILTRO_EN = {
    "cql_codigo": "IBGE code (CQL)",
    "cql_nome": "municipality name (CQL)",
    "bbox": "bbox + clip",
    "code": "IBGE code",
}


def _tipo_filtro(fonte, mapa):
    if fonte["protocolo"] == "geobr":
        return mapa[fonte["recorte"]]
    if fonte["protocolo"] == "osm":
        return mapa["bbox"]
    filtro = fonte.get("filtro") or {}
    return mapa[filtro.get("tipo", "bbox")]


def _render_fontes(sources, lang):
    en = lang == "en"
    total = len(sources)
    por_eixo = {}
    for fonte in sources:
        if fonte["eixo"] not in EIXOS:
            raise EixoDesconhecido(
                "eixo %r (fonte %r) não está no mapa EIXOS de "
                "tools/build_docs_site.py — atualize o mapa no mesmo passo "
                "em que criar o eixo" % (fonte["eixo"], fonte["id"]))
        por_eixo.setdefault(fonte["eixo"], []).append(fonte)

    ordenados = sorted(
        (e for e in por_eixo if EIXOS[e][0] is not None),
        key=lambda e: EIXOS[e][0])

    linhas = []
    cab = ("# Data sources\n\n"
           if en else "# Fontes de dados\n\n")
    cab += (
        "Catalog of the Master Plan diagnostic: **%d sources** across "
        "**%d axes**, plus the satellite basemap (context, outside the "
        "axes).\n\n"
        % (total, len(ordenados))
        if en else
        "Catálogo do diagnóstico de Plano Diretor: **%d fontes** em **%d "
        "eixos**, além do basemap de satélite (contexto, fora dos eixos).\n\n"
        % (total, len(ordenados)))
    cab += ("This page is generated from `gisbr/core/sources.py` — do not "
            "edit; change the catalog instead.\n"
            if en else
            "Esta página é gerada de `gisbr/core/sources.py` — não edite; "
            "altere o catálogo.\n")
    linhas.append(cab)

    for eixo in list(ordenados) + [
            e for e in por_eixo if EIXOS[e][0] is None]:
        num, nome_pt, nome_en = EIXOS[eixo]
        titulo = ("%s. %s" % (num, nome_en if en else nome_pt)) if num else (
            nome_en if en else nome_pt)
        linhas.append("\n## %s\n\n" % titulo)
        linhas.append(("| Source | `id` | Protocol | Filter | License |\n"
                       "|---|---|---|---|---|\n"
                       if en else
                       "| Fonte | `id` | Protocolo | Filtro | Licença |\n"
                       "|---|---|---|---|---|\n"))
        fmap = _FILTRO_EN if en else _FILTRO_PT
        for fonte in por_eixo[eixo]:
            linhas.append("| %s | `%s` | %s | %s | %s |\n" % (
                fonte["nome"], fonte["id"], fonte["protocolo"],
                _tipo_filtro(fonte, fmap),
                fonte.get("licenca", "—")))
    return "".join(linhas)


# ---------------------------------------------------------------------------
# Algoritmos (referencia/algoritmos.md / .en.md)
# ---------------------------------------------------------------------------

def _render_algoritmos(v1, v2, lang):
    en = lang == "en"
    linhas = []
    linhas.append(
        "# Algorithms\n\n" if en else "# Algoritmos\n\n")
    total = len(v1) + len(v2) + 2
    linhas.append(
        "The `gisbr` Processing provider ships **%d algorithms**: %d "
        "`read_*` (legacy GeoPackage backend, v1.7.0), %d `read_*_v2` "
        "(Parquet backend, v2.0.0), `join_censo` (censobr) and `export_poi_gmns` (diagnostic).\n\n"
        % (total, len(v1), len(v2))
        if en else
        "O provedor de Processamento `gisbr` traz **%d algoritmos**: %d "
        "`read_*` (backend legado GeoPackage, v1.7.0), %d `read_*_v2` "
        "(backend Parquet, v2.0.0), `join_censo` (censobr) e `export_poi_gmns` (diagnóstico).\n\n"
        % (total, len(v1), len(v2)))
    linhas.append(
        "This page is generated from `gisbr/core/constants.py` — do not "
        "edit.\n" if en else
        "Esta página é gerada de `gisbr/core/constants.py` — não edite.\n")

    linhas.append(
        "\n## Geografias (GPKG / v1.7.0) — %d\n\n"
        "| Algorithm | Geography (metadata token) |\n|---|---|\n"
        % len(v1)
        if en else
        "\n## Geografias (GPKG / v1.7.0) — %d\n\n"
        "| Algoritmo | Geografia (token do metadado) |\n|---|---|\n"
        % len(v1))
    for funcao in sorted(v1):
        linhas.append("| `gisbr:%s` | `%s` |\n" % (funcao, v1[funcao]))

    linhas.append(
        "\n## Geografias (Parquet / v2.0.0) — %d\n\n"
        "| Algorithm | Geography (metadata token) |\n|---|---|\n"
        % len(v2)
        if en else
        "\n## Geografias (Parquet / v2.0.0) — %d\n\n"
        "| Algoritmo | Geografia (token do metadado) |\n|---|---|\n"
        % len(v2))
    for funcao in sorted(v2):
        linhas.append("| `gisbr:%s_v2` | `%s` |\n" % (funcao, v2[funcao]))

    linhas.append(
        "\n## Censo (censobr) — 1\n\n"
        "| Algorithm |\n|---|\n| `gisbr:join_censo` |\n"
        if en else
        "\n## Censo (censobr) — 1\n\n"
        "| Algoritmo |\n|---|\n| `gisbr:join_censo` |\n")

    linhas.append(
        "\n## Diagnóstico — 1\n\n"
        "| Algorithm | Description |\n|---|---|\n| `gisbr:export_poi_gmns` | Export POIs to GMNS (csv) |\n"
        if en else
        "\n## Diagnóstico — 1\n\n"
        "| Algoritmo | Descrição |\n|---|---|\n| `gisbr:export_poi_gmns` | Exporta POIs para o padrão GMNS (csv) |\n")
    return "".join(linhas)


# ---------------------------------------------------------------------------
# Changelog (docs/changelog.md) — em inglês, como está no pacote publicado
# ---------------------------------------------------------------------------

_VERSAO_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _parse_changelog(texto):
    """metadata.txt changelog -> [(versao_tuple, versao, corpo), ...]."""
    secoes, atual = [], None
    for linha in texto.splitlines():
        linha = linha.strip()
        m = _VERSAO_RE.match(linha)
        if m:
            if atual:
                secoes.append(atual)
            atual = (tuple(int(g) for g in m.groups()), linha, [])
        elif atual is not None and linha:
            atual[2].append(linha)
        elif atual is not None and not linha:
            atual[2].append("")
    if atual:
        secoes.append(atual)
    secoes.sort(key=lambda s: s[0], reverse=True)
    return secoes


def _render_changelog(texto):
    linhas = ["# Histórico de versões\n\n"]
    linhas.append(
        "Gerado do `changelog` de `gisbr/metadata.txt` — o mesmo texto "
        "publicado no repositório oficial do QGIS (em inglês).\n")
    for _, versao, corpo in _parse_changelog(texto):
        linhas.append("\n## %s\n\n" % versao)
        linhas.append("\n".join(corpo).strip())
        linhas.append("\n")
    return "".join(linhas)


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

def gerar(raiz, destino):
    """Gera as 6 páginas derivadas. Retorna a lista do que foi escrito."""
    raiz, destino = Path(raiz), Path(destino)
    sources = _load_sources(raiz)
    v1, v2 = _load_constants(raiz)
    _version, changelog = _load_metadata(raiz)

    paginas = {
        "referencia/fontes.md": _render_fontes(sources, "pt"),
        "referencia/fontes.en.md": _render_fontes(sources, "en"),
        "referencia/algoritmos.md": _render_algoritmos(v1, v2, "pt"),
        "referencia/algoritmos.en.md": _render_algoritmos(v1, v2, "en"),
        "changelog.md": _render_changelog(changelog),
    }
    escritas = []
    for pagina, conteudo in paginas.items():
        caminho = destino / pagina
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
        escritas.append(pagina)
    return escritas


def main(argv=None):
    raiz_padrao = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Gera as páginas derivadas do site de documentação "
                    "do GisBR (fontes, algoritmos, changelog).")
    parser.add_argument("-d", "--destino", default=None,
                        help="diretório destino (padrão: <raiz>/docs)")
    args = parser.parse_args(argv)

    destino = Path(args.destino) if args.destino else raiz_padrao / "docs"
    escritas = gerar(raiz_padrao, destino)
    print("%d páginas geradas em %s: %s"
          % (len(escritas), destino, ", ".join(escritas)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
