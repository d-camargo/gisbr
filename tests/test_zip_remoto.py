# -*- coding: utf-8 -*-
"""Testes para o conector zip_remoto (gisbr.core.connectors.zip_remoto).

Cobre:
- Abertura de shapefile zipped sem rede (mock de downloader._fetch_to_cache).
- Aplicacao de subset valido (setSubsetString retorna True).
- Aplicacao de subset invalido (setSubsetString retorna False e invalida a camada).
- Arquivo corrompido / invalido.
- Fallback de CRS quando .prj estouver ausente.
- Tratamento de erro no download.
"""
import os
import zipfile
from pathlib import Path

import pytest
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPoint,
    QgsPointXY,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from gisbr.core.connectors import zip_remoto


def _cria_zip_shapefile(dir_destino, com_prj=True):
    """Gera um .zip contendo um shapefile minimo em dir_destino."""
    shp_path = os.path.join(dir_destino, "teste.shp")

    vl = QgsVectorLayer("Point?crs=EPSG:4674", "teste_memoria", "memory")
    pr = vl.dataProvider()
    pr.addAttributes([QgsField("FASE", QVariant.String), QgsField("VALOR", QVariant.Int)])
    vl.updateFields()

    f1 = QgsFeature(vl.fields())
    f1.setAttribute("FASE", "LAVRA")
    f1.setAttribute("VALOR", 10)
    f1.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(-43.9, -19.9)))

    f2 = QgsFeature(vl.fields())
    f2.setAttribute("FASE", "PESQUISA")
    f2.setAttribute("VALOR", 20)
    f2.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(-43.8, -19.8)))

    pr.addFeatures([f1, f2])

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"
    options.fileEncoding = "UTF-8"
    QgsVectorFileWriter.writeAsVectorFormatV3(
        vl, shp_path, QgsProject.instance().transformContext(), options
    )

    zip_path = os.path.join(dir_destino, "teste_shapefile.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fname in os.listdir(dir_destino):
            if fname.startswith("teste.") and not fname.endswith(".zip"):
                if not com_prj and fname.endswith(".prj"):
                    continue
                zf.write(os.path.join(dir_destino, fname), fname)

    return zip_path


def test_abertura_zip_valido(tmp_path, monkeypatch, qgis_app):
    zip_path = _cria_zip_shapefile(str(tmp_path))
    monkeypatch.setattr(
        "gisbr.core.downloader._fetch_to_cache",
        lambda file_id, urls, feedback=None: zip_path,
    )

    url = "https://exemplo.gov.br/dados.zip"
    layer = zip_remoto.fetch_layer(url, "camada_teste")

    assert layer.isValid()
    assert layer.featureCount() == 2
    assert "Zip remoto" in layer.customProperty("fonte", "")


def test_subset_valido(tmp_path, monkeypatch, qgis_app):
    zip_path = _cria_zip_shapefile(str(tmp_path))
    monkeypatch.setattr(
        "gisbr.core.downloader._fetch_to_cache",
        lambda file_id, urls, feedback=None: zip_path,
    )

    url = "https://exemplo.gov.br/dados.zip"
    layer = zip_remoto.fetch_layer(url, "camada_teste", subset="FASE = 'LAVRA'")

    assert layer.isValid()
    assert layer.featureCount() == 1


def test_subset_invalido_falha_explicitamente(tmp_path, monkeypatch, qgis_app):
    zip_path = _cria_zip_shapefile(str(tmp_path))
    monkeypatch.setattr(
        "gisbr.core.downloader._fetch_to_cache",
        lambda file_id, urls, feedback=None: zip_path,
    )

    url = "https://exemplo.gov.br/dados.zip"
    layer = zip_remoto.fetch_layer(
        url, "camada_teste", subset="COLUNA_INEXISTENTE = 123"
    )

    assert not layer.isValid()
    assert hasattr(layer, "error_msg")
    assert "setSubsetString falhou" in layer.error_msg
    assert url in layer.error_msg


def test_arquivo_corrompido(tmp_path, monkeypatch, qgis_app):
    corrupt_zip = tmp_path / "corrupted.zip"
    corrupt_zip.write_bytes(b"cabecalho_invalido_de_zip")

    monkeypatch.setattr(
        "gisbr.core.downloader._fetch_to_cache",
        lambda file_id, urls, feedback=None: str(corrupt_zip),
    )

    url = "https://exemplo.gov.br/corrupted.zip"
    layer = zip_remoto.fetch_layer(url, "camada_corrompida")

    assert not layer.isValid()
    assert hasattr(layer, "error_msg")
    assert url in layer.error_msg


def test_crs_ausente_forca_srs(tmp_path, monkeypatch, qgis_app):
    zip_sem_prj = _cria_zip_shapefile(str(tmp_path), com_prj=False)
    monkeypatch.setattr(
        "gisbr.core.downloader._fetch_to_cache",
        lambda file_id, urls, feedback=None: zip_sem_prj,
    )

    class DummyFeedback:
        def __init__(self):
            self.warnings = []

        def pushWarning(self, msg):
            self.warnings.append(msg)

    feedback = DummyFeedback()
    url = "https://exemplo.gov.br/dados_sem_prj.zip"
    layer = zip_remoto.fetch_layer(url, "camada_sem_prj", srs="EPSG:4674", feedback=feedback)

    assert layer.isValid()
    assert layer.crs().authid() == "EPSG:4674"
    assert len(feedback.warnings) > 0
    assert "sem CRS" in feedback.warnings[0]


def test_falha_download(monkeypatch, qgis_app):
    def _raise_error(file_id, urls, feedback=None):
        raise RuntimeError("Conexao recusada pelo servidor")

    monkeypatch.setattr("gisbr.core.downloader._fetch_to_cache", _raise_error)

    url = "https://exemplo.gov.br/offline.zip"
    layer = zip_remoto.fetch_layer(url, "camada_offline")

    assert not layer.isValid()
    assert hasattr(layer, "error_msg")
    assert url in layer.error_msg
    assert "falha no download" in layer.error_msg


def _garantir_processing():
    try:
        import processing
    except ModuleNotFoundError:
        import sys
        for cand in ("/usr/share/qgis/python/plugins",):
            if os.path.isdir(cand) and cand not in sys.path:
                sys.path.append(cand)
                break
        import processing
    from processing.core.Processing import Processing
    Processing.initialize()
    return processing


def _cria_zip_linestringz_5880(dir_destino):
    """Gera um .zip contendo um shapefile com LineStringZ em EPSG:5880 (coordenadas de SP)."""
    shp_path = os.path.join(dir_destino, "teste_sp_5880.shp")

    vl = QgsVectorLayer("LineStringZ?crs=EPSG:5880", "teste_memoria_z", "memory")
    pr = vl.dataProvider()

    f = QgsFeature()
    geom = QgsGeometry.fromPolyline([
        QgsPoint(5751824.0, 7375179.0, 750.0),
        QgsPoint(5752000.0, 7375300.0, 760.0),
    ])
    f.setGeometry(geom)
    pr.addFeatures([f])

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"
    options.fileEncoding = "UTF-8"
    QgsVectorFileWriter.writeAsVectorFormatV3(
        vl, shp_path, QgsProject.instance().transformContext(), options
    )

    zip_path = os.path.join(dir_destino, "teste_sp_5880.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fname in os.listdir(dir_destino):
            if fname.startswith("teste_sp_5880.") and not fname.endswith(".zip"):
                zf.write(os.path.join(dir_destino, fname), fname)

    return zip_path


def test_reprojecao_linestringz_5880_para_4674(tmp_path, monkeypatch, qgis_app):
    _garantir_processing()

    zip_path = _cria_zip_linestringz_5880(str(tmp_path))
    monkeypatch.setattr(
        "gisbr.core.downloader._fetch_to_cache",
        lambda file_id, urls, feedback=None: zip_path,
    )

    url = "https://exemplo.gov.br/sp_5880.zip"
    layer = zip_remoto.fetch_layer(url, "camada_reprojetada", srs="EPSG:4674")

    assert layer.isValid()
    assert layer.name() == "camada_reprojetada"
    assert layer.crs().authid() == "EPSG:4674"
    assert QgsWkbTypes.hasZ(layer.wkbType())

    feats = list(layer.getFeatures())
    assert len(feats) == 1
    geom = feats[0].geometry()
    assert QgsWkbTypes.hasZ(geom.wkbType())
    vertices = list(geom.vertices())
    assert len(vertices) == 2
    for v in vertices:
        assert -54 <= v.x() <= -44
        assert v.z() > 0


def test_cache_id_repassado_ao_fetch_to_cache(tmp_path, monkeypatch, qgis_app):
    zip_path = _cria_zip_shapefile(str(tmp_path))
    capturado = {}

    def mock_fetch(file_id, urls, feedback=None):
        capturado["file_id"] = file_id
        capturado["urls"] = urls
        return zip_path

    monkeypatch.setattr("gisbr.core.downloader._fetch_to_cache", mock_fetch)

    url = "https://exemplo.gov.br/caminho/arquivo_original.zip"
    layer = zip_remoto.fetch_layer(
        url,
        "camada_cache_id",
        cache_id="meu_cache_especifico.zip",
    )

    assert layer.isValid()
    assert capturado.get("file_id") == "meu_cache_especifico.zip"
    assert capturado.get("urls") == [url]


def test_refresh_cache_existente_download_ok(tmp_path, monkeypatch, qgis_app):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("gisbr.core.downloader.cache_dir", lambda: cache_dir)

    antigo_dir = tmp_path / "antigo"
    antigo_dir.mkdir()
    zip_antigo = _cria_zip_shapefile(str(antigo_dir))
    file_id = "dados_refresh.zip"
    cache_file = cache_dir / file_id
    cache_file.write_bytes(Path(zip_antigo).read_bytes())
    old_file = cache_dir / "{}.old".format(file_id)

    novo_dir = tmp_path / "novo"
    novo_dir.mkdir()
    zip_novo = _cria_zip_shapefile(str(novo_dir))
    novo_bytes = Path(zip_novo).read_bytes()

    verificacoes = {}

    def mock_fetch(fid, urls, feedback=None):
        verificacoes["old_existia_durante_download"] = old_file.exists()
        verificacoes["cache_foi_renomeado"] = not cache_file.exists()
        cache_file.write_bytes(novo_bytes)
        return cache_file

    monkeypatch.setattr("gisbr.core.downloader._fetch_to_cache", mock_fetch)

    url = "https://exemplo.gov.br/" + file_id
    layer = zip_remoto.fetch_layer(url, "camada_refresh", refresh=True)

    assert layer.isValid()
    assert verificacoes.get("old_existia_durante_download") is True
    assert verificacoes.get("cache_foi_renomeado") is True
    assert cache_file.exists()
    assert not old_file.exists()


def test_refresh_download_falhando_restaura_antigo(tmp_path, monkeypatch, qgis_app):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("gisbr.core.downloader.cache_dir", lambda: cache_dir)

    antigo_dir = tmp_path / "antigo"
    antigo_dir.mkdir()
    zip_antigo = _cria_zip_shapefile(str(antigo_dir))
    file_id = "dados_refresh_falha.zip"
    cache_file = cache_dir / file_id
    cache_file.write_bytes(Path(zip_antigo).read_bytes())
    old_file = cache_dir / "{}.old".format(file_id)

    def mock_fetch_falha(fid, urls, feedback=None):
        raise RuntimeError("Falha de conexao com o servidor")

    monkeypatch.setattr("gisbr.core.downloader._fetch_to_cache", mock_fetch_falha)

    class DummyFeedback:
        def __init__(self):
            self.warnings = []

        def pushWarning(self, msg):
            self.warnings.append(msg)

    feedback = DummyFeedback()
    url = "https://exemplo.gov.br/" + file_id
    layer = zip_remoto.fetch_layer(url, "camada_restaurada", refresh=True, feedback=feedback)

    assert layer.isValid()
    assert layer.featureCount() == 2
    assert cache_file.exists()
    assert not old_file.exists()
    assert len(feedback.warnings) > 0
    assert "download falhou; mantida a base em cache de" in feedback.warnings[0]
