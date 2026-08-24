# -*- coding: utf-8 -*-
"""Testes de resolve_arquivo (gisbr.core.connectors.local_file).

Rodam SEM QGIS (o modulo nao importa nada do QGIS no nivel de modulo):
    python3 -m pytest tests/ -q
"""
import os

from gisbr.core.connectors.local_file import resolve_arquivo


def test_casa_por_glob(tmp_path):
    (tmp_path / "sigef_mg_2026.zip").write_bytes(b"x")
    (tmp_path / "outra_coisa.txt").write_bytes(b"y")
    achado = resolve_arquivo(str(tmp_path), ["*sigef*.zip", "*parcela*certific*.zip"])
    assert achado == tmp_path / "sigef_mg_2026.zip"


def test_escolhe_o_mais_recente(tmp_path):
    antigo = tmp_path / "sigef_1.zip"
    novo = tmp_path / "sigef_2.zip"
    antigo.write_bytes(b"a")
    novo.write_bytes(b"b")
    os.utime(str(antigo), (1_000_000, 1_000_000))
    os.utime(str(novo), (2_000_000, 2_000_000))
    assert resolve_arquivo(str(tmp_path), ["*sigef*.zip"]) == novo


def test_pasta_vazia_devolve_none(tmp_path):
    assert resolve_arquivo(str(tmp_path), ["*sigef*.zip"]) is None


def test_pasta_inexistente_devolve_none(tmp_path):
    assert resolve_arquivo(str(tmp_path / "nao_existe"), ["*sigef*.zip"]) is None


def test_insensivel_a_maiusculas(tmp_path):
    (tmp_path / "SIGEF_MG.ZIP").write_bytes(b"x")
    achado = resolve_arquivo(str(tmp_path), ["*sigef*.zip"])
    assert achado == tmp_path / "SIGEF_MG.ZIP"
