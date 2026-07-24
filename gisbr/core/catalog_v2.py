# -*- coding: utf-8 -*-
"""Catalogo v2 (Parquet) — lista e filtra os assets do release geobr_prep_data.

Espelha download_metadata_v2 / select_metadata_v2 do geobr Python, mas com
``json`` da stdlib (sem pandas) e via QgsBlockingNetworkRequest. NAO le Parquet
aqui: apenas resolve nome/URL do arquivo. A leitura efetiva (gated pelo driver)
fica no algoritmo.
"""

import json
import re

from .constants import (
    GEOBR_DATA_RELEASE,
    GEOBR_V2_API_LATEST,
    GEOBR_V2_API_RELEASES,
)
from .downloader import fetch_bytes, cache_dir

# Cache de sessao do metadado v2 parseado.
_METADATA_V2_CACHE = None


def _parse_assets(assets):
    """Extrai linhas {file_name, download_url, geo, year, simplified} dos assets."""
    rows = []
    for asset in assets:
        fname = asset.get("name", "")
        if not fname.endswith(".parquet"):
            continue
        url = asset.get("browser_download_url", "")
        # geo = primeiro segmento antes de "_"
        geo = fname.split("_", 1)[0]
        m = re.search(r"(\d+)", fname)
        year = int(m.group(1)) if m else None
        simplified = "simplified" in fname.lower()
        rows.append(
            {
                "file_name": fname,
                "download_url": url,
                "geo": geo,
                "year": year,
                "simplified": simplified,
            }
        )
    return rows


def _metadata_disk_path():
    return cache_dir() / "metadata_geobr_v2.json"


def download_metadata_v2(force_refresh=False):
    """Baixa (ou le do cache) a lista de assets .parquet do release v2.

    Tenta o release 'latest'; se vazio, varre todos os releases e usa a tag
    ``GEOBR_DATA_RELEASE`` (v2.0.0). Cacheia em disco como JSON.
    """
    global _METADATA_V2_CACHE
    if _METADATA_V2_CACHE is not None and not force_refresh:
        return _METADATA_V2_CACHE

    disk = _metadata_disk_path()
    if disk.exists() and disk.stat().st_size > 0 and not force_refresh:
        _METADATA_V2_CACHE = json.loads(disk.read_text(encoding="utf-8"))
        return _METADATA_V2_CACHE

    # 1) release latest
    data = json.loads(fetch_bytes(GEOBR_V2_API_LATEST).decode("utf-8"))
    rows = _parse_assets(data.get("assets", []))

    # 2) fallback: varre releases e acha a tag fixa v2.0.0
    if not rows:
        releases = json.loads(fetch_bytes(GEOBR_V2_API_RELEASES).decode("utf-8"))
        for rel in releases:
            if rel.get("tag_name") == GEOBR_DATA_RELEASE:
                rows = _parse_assets(rel.get("assets", []))
                break

    if not rows:
        raise ValueError(
            "Nao foi possivel listar os assets .parquet do geobr_prep_data "
            f"({GEOBR_DATA_RELEASE})."
        )

    disk.write_text(json.dumps(rows), encoding="utf-8")
    _METADATA_V2_CACHE = rows
    return rows


def _rows_for_geo(geo):
    rows = [r for r in download_metadata_v2() if r["geo"] == geo]
    if not rows:
        unique = sorted({r["geo"] for r in download_metadata_v2()})
        raise ValueError(
            f"A geografia v2 '{geo}' nao existe. Disponiveis: {', '.join(unique)}"
        )
    return rows


def available_years(geo):
    return sorted({r["year"] for r in _rows_for_geo(geo) if r["year"] is not None})


def select(geo, year=None, simplified=True, zone=None):
    """Filtra o metadado v2 por geo + ano + simplificado (+ zone p/ setores 2000).

    Retorna lista de rows (normalmente 1). ``zone`` ('rural'/'urbano') filtra
    os setores censitarios de 2000, que vem fatiados por zona no v2.
    """
    years = available_years(geo)
    if not years:
        raise ValueError(f"Nenhum ano disponivel para v2 '{geo}'.")
    year = int(max(years)) if year is None else int(year)
    if year not in years:
        raise ValueError(
            f"Ano {year} indisponivel para v2 '{geo}'. "
            f"Anos: {', '.join(map(str, years))}"
        )

    rows = [
        r
        for r in _rows_for_geo(geo)
        if r["year"] == year and r["simplified"] == bool(simplified)
    ]
    if zone:
        rows = [r for r in rows if zone in r["file_name"]]
    if not rows:
        raise ValueError(
            f"Nenhum arquivo v2 para geo='{geo}', ano={year}, "
            f"simplified={simplified}" + (f", zone={zone}" if zone else "") + "."
        )
    return rows
