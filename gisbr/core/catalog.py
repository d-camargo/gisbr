# -*- coding: utf-8 -*-
"""Catalogo: download + parse do metadado v1.7.0 e selecao por geo/ano/simplificado.

Espelha select_metadata / select_year / select_simplified do geobr, mas usando
o modulo ``csv`` da stdlib (sem pandas).
"""

import csv
import io
from pathlib import Path

from .constants import METADATA_URL
from .downloader import fetch, cache_dir

# Cache em memoria (por sessao) do metadado parseado.
_METADATA_CACHE = None

# Colunas esperadas no CSV v1.7.0.
_COLUMNS = ("geo", "year", "code", "download_path", "code_abbrev")


def _metadata_disk_path():
    return cache_dir() / "metadata_1.7.0_gpkg.csv"


def download_metadata(force_refresh=False, feedback=None):
    """Baixa (ou le do cache) o metadado e devolve lista de dicts.

    Cacheia em memoria por sessao e em disco. A coluna ``code_abbrev`` aparece
    no header real do CSV; tratamos tambem ``code_abrev`` por seguranca.
    """
    global _METADATA_CACHE
    if _METADATA_CACHE is not None and not force_refresh:
        return _METADATA_CACHE

    disk = _metadata_disk_path()
    text = None
    if disk.exists() and disk.stat().st_size > 0 and not force_refresh:
        text = disk.read_text(encoding="utf-8")
    else:
        if force_refresh and disk.exists():
            try:
                disk.unlink()
            except Exception:
                pass
        try:
            path = fetch(METADATA_URL, feedback=feedback)
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            vendor_path = Path(__file__).parent / "data" / "metadata_1.7.0_gpkg.csv"
            if vendor_path.exists():
                text = vendor_path.read_text(encoding="utf-8")
                if feedback is not None:
                    from qgis.PyQt.QtCore import QCoreApplication
                    feedback.pushWarning(
                        QCoreApplication.translate(
                            "Catalog",
                            "Offline metadata copy used as fallback. Data might be outdated. (Error: {error})"
                        ).format(error=exc)
                    )
            else:
                raise exc

    rows = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        # normaliza chave de sigla (header pode variar)
        abbrev = row.get("code_abbrev", row.get("code_abrev", ""))
        rows.append(
            {
                "geo": (row.get("geo") or "").strip(),
                "year": (row.get("year") or "").strip(),
                "code": (row.get("code") or "").strip(),
                "download_path": (row.get("download_path") or "").strip(),
                "code_abbrev": (abbrev or "").strip(),
            }
        )
    _METADATA_CACHE = rows
    return rows


def _rows_for_geo(geo, feedback=None):
    rows = [r for r in download_metadata(feedback=feedback) if r["geo"] == geo]
    if not rows:
        unique = sorted({r["geo"] for r in download_metadata(feedback=feedback)})
        raise ValueError(
            f"A geografia '{geo}' nao existe no metadado. "
            f"Disponiveis: {', '.join(unique)}"
        )
    return rows


def available_years(geo, feedback=None):
    """Anos disponiveis (ordenados) para uma geografia."""
    years = sorted({int(r["year"]) for r in _rows_for_geo(geo, feedback=feedback) if r["year"].isdigit()})
    return years


def select_year(geo, year=None, feedback=None):
    """Valida/escolhe o ano. Se ``year`` for None, usa o mais recente."""
    years = available_years(geo, feedback=feedback)
    if not years:
        raise ValueError(f"Nenhum ano disponivel para '{geo}'.")
    if year is None:
        return max(years)
    year = int(year)
    if year not in years:
        raise ValueError(
            f"Ano {year} indisponivel para '{geo}'. "
            f"Anos: {', '.join(map(str, years))}"
        )
    return year


def _is_simplified(row):
    return "simplified" in row["download_path"]


def select(geo, year=None, simplified=True, feedback=None):
    """Filtra o metadado por geo + ano + simplificado.

    Retorna lista de rows (dicts). Pode haver varias rows quando a geografia
    e fatiada por UF (ex.: municipality).
    """
    year = select_year(geo, year, feedback=feedback)
    base = [
        r
        for r in _rows_for_geo(geo, feedback=feedback)
        if r["year"].isdigit() and int(r["year"]) == year
    ]
    rows = [r for r in base if _is_simplified(r) == bool(simplified)]
    if not rows:
        # Geografias de pontos (escolas, sedes, saude...) muitas vezes nao tem
        # versao simplificada (ou vice-versa). Cai para a variante existente.
        rows = [r for r in base if _is_simplified(r) != bool(simplified)]
    if not rows:
        raise ValueError(
            f"Nenhum arquivo para geo='{geo}', ano={year}, "
            f"simplified={simplified}."
        )
    return rows


def narrow_by_uf(rows, uf_code, uf_abbrev):
    """Reduz as rows do metadado a uma UF (quando a geografia e fatiada).

    Espelha o filtro do geobr: ``str(code)[:2] in row['code']`` OU sigla em
    ``row['code_abbrev']``. Se nenhuma row casar (geografia nacional unica),
    devolve as rows originais inalteradas.
    """
    if uf_code is None:
        return rows
    prefix = str(uf_code)
    matched = [
        r
        for r in rows
        if prefix in str(r["code"]) or (uf_abbrev and uf_abbrev == r["code_abbrev"])
    ]
    return matched if matched else rows
