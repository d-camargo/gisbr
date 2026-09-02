# -*- coding: utf-8 -*-
"""Catalogo do censobr (dados tabulares do Censo, nivel setor censitario).

Lista os assets `*_tracts_*` dos releases do repo ipea/censobr e resolve
ano + dataset -> URL do .parquet. Esses arquivos carregam a chave `code_tract`,
feita justamente para o join com a geometria de setores do geobr.

Mesmo padrao do catalog_v2: API de releases do GitHub + json da stdlib.
"""

import json
import re

from .downloader import fetch_bytes, cache_dir

CENSOBR_RELEASES_API = "https://api.github.com/repos/ipea/censobr/releases"

# 2010_tracts_DomicilioRenda_v0.6.0.parquet -> (ano, dataset, versao)
_TRACT_RE = re.compile(r"^(\d{4})_tracts_(.+?)_(v[\d.]+)\.parquet$")

_CACHE = None


def _versao_tupla(v_str):
    """Converte string de versao (ex: 'v0.5.0', 'v0.10.0') em tupla numerica.

    Componentes nao inteiros sao convertidos para 0.
    """
    if not v_str:
        return (0,)
    clean = v_str.lstrip("vV")
    parts = clean.split(".")
    res = []
    for p in parts:
        try:
            res.append(int(p))
        except ValueError:
            res.append(0)
    return tuple(res)


def _disk_path():
    return cache_dir() / "metadata_censobr_tracts.json"


def download_metadata(force_refresh=False):
    """Lista os datasets de setor (tracts) do censobr. Retorna lista de dicts.

    Varre todos os releases e, em caso de (ano, dataset) repetido entre versoes,
    mantem a versao mais alta. Cacheia em memoria e em disco.
    """
    global _CACHE
    if _CACHE is not None and not force_refresh:
        return _CACHE

    disk = _disk_path()
    if disk.exists() and disk.stat().st_size > 0 and not force_refresh:
        _CACHE = json.loads(disk.read_text(encoding="utf-8"))
        return _CACHE

    releases = json.loads(fetch_bytes(CENSOBR_RELEASES_API).decode("utf-8"))
    best = {}
    for rel in releases:
        for asset in rel.get("assets", []):
            m = _TRACT_RE.match(asset.get("name", ""))
            if not m:
                continue
            year, dataset, version = int(m.group(1)), m.group(2), m.group(3)
            key = f"{year}|{dataset}"
            if key not in best or _versao_tupla(version) > _versao_tupla(
                best[key]["version"]
            ):
                best[key] = {
                    "file_name": asset.get("name", ""),
                    "download_url": asset.get("browser_download_url", ""),
                    "year": year,
                    "dataset": dataset,
                    "version": version,
                    "size": asset.get("size", 0),
                }
    rows = list(best.values())
    if not rows:
        raise ValueError("Nenhum dataset de setor (tracts) encontrado no censobr.")

    disk.write_text(json.dumps(rows), encoding="utf-8")
    _CACHE = rows
    return rows


def available_years():
    return sorted({r["year"] for r in download_metadata()})


def available_datasets(year):
    return sorted(r["dataset"] for r in download_metadata() if r["year"] == int(year))


def available_datasets_por_ano():
    """Retorna dict {ano: [datasets]} com os datasets disponiveis por ano."""
    res = {}
    for r in download_metadata():
        res.setdefault(r["year"], []).append(r["dataset"])
    for year in res:
        res[year] = sorted(res[year])
    return res


def select(year, dataset):
    """Resolve (ano, dataset) -> row do censobr. Erro amigavel se nao existir."""
    rows = [
        r
        for r in download_metadata()
        if r["year"] == int(year) and r["dataset"] == dataset
    ]
    if not rows:
        ds = available_datasets(year)
        if not ds:
            raise ValueError(
                f"Ano {year} indisponivel no censobr (tracts). "
                f"Anos: {', '.join(map(str, available_years()))}."
            )
        raise ValueError(
            f"Dataset '{dataset}' indisponivel para {year}. "
            f"Disponiveis: {', '.join(ds)}."
        )
    return rows[0]
