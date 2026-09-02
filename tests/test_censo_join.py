# -*- coding: utf-8 -*-
"""Testes do modulo core/censo_join.py (D1, D3, D5, D10)."""

import pytest

pytest.importorskip("qgis.core")

from gisbr.core import capabilities
from gisbr.core.censo_join import (
    DATASETS_FALLBACK,
    CensoJoinError,
    anexar_censo,
    filtro_censo,
    prefixo_de,
)


def test_prefixo_de():
    assert prefixo_de("DomicilioRenda") == "DomicilioRenda_"
    assert prefixo_de("Basico") == "Basico_"


def test_filtro_censo_tres_casos():
    # Caso 1: code_muni for None -> retorna None
    assert filtro_censo(None, ["code_muni", "code_tract"]) is None
    assert filtro_censo(None, []) is None

    # Caso 2: code_muni fornecido e 'code_muni' em colunas -> ("code_muni", code_muni, "igual")
    cols_com_muni = ["code_muni", "code_tract", "v001"]
    assert filtro_censo(3106200, cols_com_muni) == ("code_muni", 3106200, "igual")
    assert filtro_censo("3106200", cols_com_muni) == ("code_muni", "3106200", "igual")

    # Caso 3: code_muni fornecido e 'code_muni' NAO em colunas -> ("code_tract", str(code_muni)[:7], "prefixo")
    cols_sem_muni = ["code_tract", "v001"]
    assert filtro_censo(3106200, cols_sem_muni) == ("code_tract", "3106200", "prefixo")
    assert filtro_censo("31062000500", cols_sem_muni) == ("code_tract", "3106200", "prefixo")


def test_gate_backend_ausente(monkeypatch):
    monkeypatch.setattr(capabilities, "parquet_backend", lambda: None)

    with pytest.raises(CensoJoinError) as exc_info:
        anexar_censo(layer=None, ano=2010, datasets=["DomicilioRenda"])

    assert str(exc_info.value) == capabilities.install_hint()


def test_anexar_censo_sem_context(qgis_app, tmp_path, monkeypatch):
    """Caminho do painel: context=None tem de funcionar de ponta a ponta.

    Regressao do bug em que processing.run(..., is_child_algorithm=True) sem
    context criava um contexto interno que morria com os sinks "memory:" —
    o join do censobr nunca chegava a camada gravada no GeoPackage.
    """
    if qgis_app is None:
        pytest.skip("qgis app not available")

    try:
        import processing
    except ModuleNotFoundError:
        # layout Linux (apt e imagens oficiais qgis/qgis): o pacote 'processing'
        # vive fora do sys.path default e precisa ser acrescentado na mao
        import os
        import sys
        for cand in ("/usr/share/qgis/python/plugins",):
            if os.path.isdir(cand):
                sys.path.append(cand)
                break
        try:
            import processing
        except ModuleNotFoundError:
            pytest.skip("processing module unavailable in this environment")

    from processing.core.Processing import Processing
    Processing.initialize()

    from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer
    from gisbr.core import catalog_censo, downloader, loader_v2

    monkeypatch.setattr(capabilities, "parquet_backend", lambda: "pyarrow")

    # setores como no geobr v1: code_tract double
    tracts = QgsVectorLayer(
        "Polygon?crs=EPSG:4674&field=code_tract:double", "tracts", "memory")
    feats = []
    for code in (310620005000001.0, 310620005000002.0):
        f = QgsFeature(tracts.fields())
        f.setGeometry(QgsGeometry.fromWkt("POLYGON((0 0,1 0,1 1,0 0))"))
        f["code_tract"] = code
        feats.append(f)
    tracts.dataProvider().addFeatures(feats)
    tracts.updateExtents()

    # tabela como no censobr: code_tract string + variavel
    tabela = QgsVectorLayer(
        "None?field=code_tract:string&field=V001:integer",
        "censo", "memory")
    tfeats = []
    for code, valor in (("310620005000001", 42), ("999999999999999", 7)):
        f = QgsFeature(tabela.fields())
        f["code_tract"] = code
        f["V001"] = valor
        tfeats.append(f)
    tabela.dataProvider().addFeatures(tfeats)

    monkeypatch.setattr(
        catalog_censo, "select",
        lambda ano, ds: {
            "file_name": "2010_tracts_Basico_v0.5.0.parquet",
            "download_url": "https://example.com/x.parquet",
            "size": 9123456,
        })
    monkeypatch.setattr(
        downloader, "fetch_asset",
        lambda nome, url, feedback=None: str(tmp_path / "x.parquet"))
    monkeypatch.setattr(
        loader_v2, "read_parquet_layer",
        lambda path, name, filtro=None: tabela)

    resultado, relatorio = anexar_censo(
        tracts, 2010, ["Basico"], code_muni=3106200)

    assert relatorio["datasets_ok"] == ["Basico"]
    assert relatorio["casados"] == 1
    assert relatorio["sem_par"] == 1
    assert isinstance(resultado, QgsVectorLayer)
    assert "Basico_V001" in [f.name() for f in resultado.fields()]
    valores = [feat["Basico_V001"] for feat in resultado.getFeatures()]
    assert valores == [42, None] or valores == [None, 42]


def test_datasets_fallback():
    assert isinstance(DATASETS_FALLBACK, list)
    assert "DomicilioRenda" in DATASETS_FALLBACK
    assert "Basico" in DATASETS_FALLBACK


def test_join_censo_algorithm_metadata():
    from gisbr.algorithms.join_censo import JoinCenso
    alg = JoinCenso()
    assert alg.name() == "join_censo"
    assert alg.groupId() == "censobr"
    assert "code_tract" in alg.shortHelpString() or "censobr" in alg.shortHelpString()

