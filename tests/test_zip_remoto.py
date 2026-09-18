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

import pytest
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
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
