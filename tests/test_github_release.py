# -*- coding: utf-8 -*-
"""Testes do conector de GitHub Releases (gisbr.core.connectors.github_release).

Rodam SEM rede (com _fetch_to_cache monkeypatchado em tmp_path):
    python3 -m pytest -q tests/test_github_release.py

Cobrem os casos exigidos no passo 1 do plano da rodada 22: url_asset,
entrada_rm (id presente, id ausente, status="falhou"), fetch_asset com sha
correto/errado e fetch_manifest com schema_version incompatível.
"""

import hashlib
import json
from pathlib import Path

import pytest

from gisbr.core.connectors import github_release
from gisbr.core.connectors.github_release import (
    DownloadError,
    entrada_rm,
    fetch_asset,
    fetch_manifest,
    url_asset,
)

BASE = {"repo": "d-camargo/gisbr_base", "tag": "osm-20260929", "manifest": "manifest.json"}


def test_url_asset():
    assert url_asset(BASE, "osm_vias_rm04501.gpkg.zip") == (
        "https://github.com/d-camargo/gisbr_base/releases/download/"
        "osm-20260929/osm_vias_rm04501.gpkg.zip"
    )
    # o repo não pode ganhar barra extra vindo de catálogo mal formado
    base_suja = dict(BASE, repo="/d-camargo/gisbr_base/")
    assert url_asset(base_suja, "manifest.json") == (
        "https://github.com/d-camargo/gisbr_base/releases/download/"
        "osm-20260929/manifest.json"
    )


def test_entrada_rm():
    manifest = {
        "schema_version": 1,
        "rms": {
            "04501": {"status": "ok", "asset": "osm_vias_rm04501.gpkg.zip", "sha256": "ab" * 32},
            "04601": {"status": "timeout", "asset": "osm_vias_rm04601.gpkg.zip"},
        },
    }

    # id presente com status ok -> (entrada, None)
    entrada, motivo = entrada_rm(manifest, "04501", tag="osm-20260929")
    assert motivo is None
    assert entrada["status"] == "ok"
    assert entrada["asset"] == "osm_vias_rm04501.gpkg.zip"

    # id ausente -> (None, motivo citando a base)
    entrada, motivo = entrada_rm(manifest, "99999", tag="osm-20260929")
    assert entrada is None
    assert motivo == "RM 99999 não está na base osm-20260929"

    # status != ok -> (None, motivo citando o status)
    entrada, motivo = entrada_rm(manifest, "04601", tag="osm-20260929")
    assert entrada is None
    assert motivo == "RM 04601 falhou na montagem da base osm-20260929 (status=timeout)"


def test_fetch_asset_sha(tmp_path, monkeypatch):
    test_file = tmp_path / "osm_vias_rm99999.gpkg.zip"
    conteudo = b"conteudo binario simulado de geopackage 12345"
    test_file.write_bytes(conteudo)

    chamadas = []

    def mock_fetch(file_id, urls, feedback=None):
        chamadas.append((file_id, urls))
        return test_file

    monkeypatch.setattr(github_release, "_fetch_to_cache", mock_fetch)

    # sha correto: devolve o Path e o arquivo permanece
    sha_correto = hashlib.sha256(conteudo).hexdigest()
    res_path = fetch_asset(BASE, "osm_vias_rm99999.gpkg.zip", sha256=sha_correto)
    assert res_path == test_file
    assert res_path.exists()
    assert len(chamadas) == 1
    # a chave de cache carrega o prefixo da base e a tag (D2)
    assert chamadas[0][0] == "gisbr_base_osm-20260929_osm_vias_rm99999.gpkg.zip"
    assert chamadas[0][1] == [
        "https://github.com/d-camargo/gisbr_base/releases/download/"
        "osm-20260929/osm_vias_rm99999.gpkg.zip"
    ]

    # sha errado: levanta DownloadError e o arquivo some do cache
    with pytest.raises(DownloadError) as exc_info:
        fetch_asset(BASE, "osm_vias_rm99999.gpkg.zip", sha256="f" * 64)
    assert "sha256 divergente" in str(exc_info.value)
    assert not test_file.exists()

    # sem sha informado: devolve o Path sem conferir nada
    test_file.write_bytes(conteudo)
    assert fetch_asset(BASE, "osm_vias_rm99999.gpkg.zip") == test_file


def test_fetch_manifest_schema_version(tmp_path, monkeypatch):
    def _mock_com_arquivo(path):
        monkeypatch.setattr(
            github_release, "_fetch_to_cache", lambda fid, urls, feedback=None: path)
        return path

    # schema_version == 1: devolve o dict
    valido = tmp_path / "manifest_v1.json"
    valido.write_text(json.dumps({"schema_version": 1, "rms": {"04501": {"status": "ok"}}}),
                      encoding="utf-8")
    _mock_com_arquivo(valido)
    manifest = fetch_manifest(BASE)
    assert manifest["schema_version"] == 1
    assert "04501" in manifest["rms"]

    # schema_version != 1: DownloadError
    invalido = tmp_path / "manifest_v2.json"
    invalido.write_text(json.dumps({"schema_version": 2, "rms": {}}), encoding="utf-8")
    _mock_com_arquivo(invalido)
    with pytest.raises(DownloadError) as exc_info:
        fetch_manifest(BASE)
    assert "schema_version incompatível" in str(exc_info.value)

    # schema_version ausente: DownloadError
    sem_versao = tmp_path / "manifest_sem_versao.json"
    sem_versao.write_text(json.dumps({"rms": {}}), encoding="utf-8")
    _mock_com_arquivo(sem_versao)
    with pytest.raises(DownloadError):
        fetch_manifest(BASE)

    # JSON quebrado: DownloadError
    quebrado = tmp_path / "manifest_quebrado.json"
    quebrado.write_text("{nao e json", encoding="utf-8")
    _mock_com_arquivo(quebrado)
    with pytest.raises(DownloadError):
        fetch_manifest(BASE)
