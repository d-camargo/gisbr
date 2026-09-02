# -*- coding: utf-8 -*-
"""Testes do catalogo do censobr (gisbr.core.catalog_censo)."""

import json
import pytest

pytest.importorskip("qgis.core")

import gisbr.core.catalog_censo as catalog_censo
from gisbr.core.catalog_censo import (
    _versao_tupla,
    available_datasets,
    available_datasets_por_ano,
    available_years,
    download_metadata,
    select,
)


@pytest.fixture(autouse=True)
def clean_catalog_censo_cache(tmp_path, monkeypatch):
    catalog_censo._CACHE = None
    monkeypatch.setattr(catalog_censo, "cache_dir", lambda: tmp_path)
    yield
    catalog_censo._CACHE = None


FAKE_RELEASES = [
    {
        "tag_name": "v0.5.0",
        "assets": [
            {
                "name": "2010_tracts_DomicilioRenda_v0.5.0.parquet",
                "browser_download_url": "https://example.com/2010_tracts_DomicilioRenda_v0.5.0.parquet",
                "size": 1000,
            },
            {
                "name": "2010_tracts_PessoaRenda_v0.5.0.parquet",
                "browser_download_url": "https://example.com/2010_tracts_PessoaRenda_v0.5.0.parquet",
                "size": 1500,
            },
        ],
    },
    {
        "tag_name": "v0.10.0",
        "assets": [
            {
                "name": "2010_tracts_DomicilioRenda_v0.10.0.parquet",
                "browser_download_url": "https://example.com/2010_tracts_DomicilioRenda_v0.10.0.parquet",
                "size": 1200,
            },
            {
                "name": "2022_tracts_DomicilioRenda_v0.10.0.parquet",
                "browser_download_url": "https://example.com/2022_tracts_DomicilioRenda_v0.10.0.parquet",
                "size": 2000,
            },
        ],
    },
]


def test_versao_tupla():
    assert _versao_tupla("v0.5.0") == (0, 5, 0)
    assert _versao_tupla("v0.10.0") == (0, 10, 0)
    assert _versao_tupla("v0.10.0") > _versao_tupla("v0.5.0")
    assert _versao_tupla("v0.5.0-alpha") == (0, 5, 0)
    assert _versao_tupla("") == (0,)


def test_download_metadata_dedup_and_version(monkeypatch):
    fake_bytes = json.dumps(FAKE_RELEASES).encode("utf-8")
    monkeypatch.setattr(catalog_censo, "fetch_bytes", lambda url: fake_bytes)

    rows = download_metadata()
    # Deduplicacao mantendo a versao mais alta (v0.10.0 > v0.5.0)
    row_dom_2010 = select(2010, "DomicilioRenda")
    assert row_dom_2010["version"] == "v0.10.0"
    assert row_dom_2010["file_name"] == "2010_tracts_DomicilioRenda_v0.10.0.parquet"
    assert row_dom_2010["size"] == 1200
    assert "size" in row_dom_2010

    # Atributo size presente em todas as rows
    for r in rows:
        assert "size" in r
        assert isinstance(r["size"], int)


def test_available_years_and_datasets(monkeypatch):
    fake_bytes = json.dumps(FAKE_RELEASES).encode("utf-8")
    monkeypatch.setattr(catalog_censo, "fetch_bytes", lambda url: fake_bytes)

    assert available_years() == [2010, 2022]
    assert available_datasets(2010) == ["DomicilioRenda", "PessoaRenda"]
    assert available_datasets(2022) == ["DomicilioRenda"]

    por_ano = available_datasets_por_ano()
    assert por_ano == {
        2010: ["DomicilioRenda", "PessoaRenda"],
        2022: ["DomicilioRenda"],
    }
