# -*- coding: utf-8 -*-
"""Testes para osm_pipeline.importar_rede_rm (D4).

Testa a importação da rede pré-processada de Região Metropolitana do GitHub Releases:
- caminho feliz: as 3 camadas aparecem no GPKG de destino com a mesma contagem,
  gpkg_ok=True, e data_extracao igual ao timestamp_osm[:10];
- RM fora do manifest -> pulou;
- zip sem uma das camadas -> erro.
"""

import os
import zipfile
from pathlib import Path

import pytest
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
)

from gisbr.core import osm_pipeline
from gisbr.core.connectors import github_release
from gisbr.core.recorte import Recorte


def _skip_sem_qgis(qgis_app):
    if qgis_app is None:
        pytest.skip("PyQGIS não disponível neste ambiente")


def _cria_gpkg_e_zip(dir_path, id_rm="99999", incluir_problemas=True):
    """Cria um GPKG com as 3 camadas (ou 2 se incluir_problemas=False) e zipa."""
    sufixo = f"rm{id_rm}"
    gpkg_name = f"osm_vias_{sufixo}.gpkg"
    gpkg_path = os.path.join(dir_path, gpkg_name)
    ctx = QgsProject.instance().transformContext()

    # 1. osm_links_<sufixo> (LineString, 2 feições)
    vl_links = QgsVectorLayer("LineString?crs=EPSG:4674", "links", "memory")
    pr_links = vl_links.dataProvider()
    pr_links.addAttributes([QgsField("arc_id", QVariant.Int), QgsField("name", QVariant.String)])
    vl_links.updateFields()

    f1 = QgsFeature(vl_links.fields())
    f1.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(-43.9, -19.9), QgsPointXY(-43.8, -19.8)]))
    f1.setAttributes([1, "Via 1"])
    f2 = QgsFeature(vl_links.fields())
    f2.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(-43.8, -19.8), QgsPointXY(-43.7, -19.7)]))
    f2.setAttributes([2, "Via 2"])
    pr_links.addFeatures([f1, f2])

    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = f"osm_links_{sufixo}"
    res = QgsVectorFileWriter.writeAsVectorFormatV3(vl_links, gpkg_path, ctx, opts)
    assert res[0] == QgsVectorFileWriter.WriterError.NoError, res[1]

    # 2. osm_nodes_<sufixo> (Point, 2 feições)
    opts.actionOnExistingFile = QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
    opts.layerName = f"osm_nodes_{sufixo}"
    vl_nodes = QgsVectorLayer("Point?crs=EPSG:4674", "nodes", "memory")
    pr_nodes = vl_nodes.dataProvider()
    pr_nodes.addAttributes([QgsField("node_id", QVariant.Int)])
    vl_nodes.updateFields()

    fn1 = QgsFeature(vl_nodes.fields())
    fn1.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(-43.9, -19.9)))
    fn1.setAttributes([101])
    fn2 = QgsFeature(vl_nodes.fields())
    fn2.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(-43.8, -19.8)))
    fn2.setAttributes([102])
    pr_nodes.addFeatures([fn1, fn2])

    res = QgsVectorFileWriter.writeAsVectorFormatV3(vl_nodes, gpkg_path, ctx, opts)
    assert res[0] == QgsVectorFileWriter.WriterError.NoError, res[1]

    # 3. osm_problemas_<sufixo> (Point, 1 feição)
    if incluir_problemas:
        opts.layerName = f"osm_problemas_{sufixo}"
        vl_prob = QgsVectorLayer("Point?crs=EPSG:4674", "problemas", "memory")
        pr_prob = vl_prob.dataProvider()
        pr_prob.addAttributes([QgsField("tipo", QVariant.String)])
        vl_prob.updateFields()

        fp = QgsFeature(vl_prob.fields())
        fp.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(-43.8, -19.8)))
        fp.setAttributes(["cruzamento_sem_no"])
        pr_prob.addFeatures([fp])

        res = QgsVectorFileWriter.writeAsVectorFormatV3(vl_prob, gpkg_path, ctx, opts)
        assert res[0] == QgsVectorFileWriter.WriterError.NoError, res[1]

    # Zipar
    zip_path = os.path.join(dir_path, f"{gpkg_name}.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(gpkg_path, arcname=gpkg_name)

    return Path(zip_path)


def test_importar_rede_rm_caminho_feliz(qgis_app, tmp_path, monkeypatch):
    """Caminho feliz: 3 camadas gravadas no GPKG destino com mesma contagem e metadata certa."""
    _skip_sem_qgis(qgis_app)

    zip_path = _cria_gpkg_e_zip(str(tmp_path), id_rm="99999", incluir_problemas=True)

    timestamp_osm = "2026-09-29T20:22:51Z"
    manifest = {
        "schema_version": 1,
        "tag": "osm-20260929",
        "gerado_em": "2026-09-29T21:00:00Z",
        "gisbr_ref": "abcdef123456789",
        "atribuicao": "© OpenStreetMap contributors (ODbL)",
        "fontes": {
            "sudeste": {
                "arquivo": "sudeste-latest.osm.pbf",
                "timestamp_osm": timestamp_osm,
                "bytes": 1000000,
            }
        },
        "rms": {
            "99999": {
                "id": "99999",
                "nome": "Região Metropolitana de Teste",
                "status": "ok",
                "regiao_geofabrik": "sudeste",
                "asset": "osm_vias_rm99999.gpkg.zip",
                "sha256": "dummy_sha256",
                "bytes": 50000,
            }
        },
    }

    monkeypatch.setattr(github_release, "fetch_manifest", lambda *a, **kw: manifest)
    monkeypatch.setattr(github_release, "fetch_asset", lambda *a, **kw: zip_path)

    recorte = Recorte.de_rm("99999", "RM Teste", ["9999901"])
    gpkg_destino = str(tmp_path / "destino.gpkg")

    resultado = osm_pipeline.importar_rede_rm(recorte, gpkg_destino)
    meta = resultado.get("metadata", {})

    # Verificação da metadata descrita no D4
    assert meta.get("gpkg_ok") is True
    assert meta.get("data_extracao") == timestamp_osm[:10]
    assert meta.get("data_extracao") == "2026-09-29"
    assert meta.get("fonte") == "gisbr_base osm-20260929 (abcdef1)"
    assert meta.get("atribuicao") == "© OpenStreetMap contributors (ODbL)"

    # Verificação das 3 camadas gravadas no GPKG de destino
    vl_links = QgsVectorLayer(f"{gpkg_destino}|layername=osm_links_rm99999", "links", "ogr")
    assert vl_links.isValid(), "osm_links_rm99999 deve ser válida no GPKG"
    assert vl_links.featureCount() == 2

    vl_nodes = QgsVectorLayer(f"{gpkg_destino}|layername=osm_nodes_rm99999", "nodes", "ogr")
    assert vl_nodes.isValid(), "osm_nodes_rm99999 deve ser válida no GPKG"
    assert vl_nodes.featureCount() == 2

    vl_prob = QgsVectorLayer(f"{gpkg_destino}|layername=osm_problemas_rm99999", "problemas", "ogr")
    assert vl_prob.isValid(), "osm_problemas_rm99999 deve ser válida no GPKG"
    assert vl_prob.featureCount() == 1


def test_importar_rede_rm_fora_do_manifest_pulou(qgis_app, tmp_path, monkeypatch):
    """RM fora do manifest deve retornar metadata com pulou."""
    _skip_sem_qgis(qgis_app)

    manifest = {
        "schema_version": 1,
        "tag": "osm-20260929",
        "rms": {
            "99999": {"id": "99999", "status": "ok", "asset": "osm_vias_rm99999.gpkg.zip"},
        },
    }

    monkeypatch.setattr(github_release, "fetch_manifest", lambda *a, **kw: manifest)

    recorte_fora = Recorte.de_rm("88888", "RM Ausente", ["8888801"])
    gpkg_destino = str(tmp_path / "destino.gpkg")

    resultado = osm_pipeline.importar_rede_rm(recorte_fora, gpkg_destino)
    meta = resultado.get("metadata", {})

    assert "pulou" in meta
    assert "88888" in meta["pulou"]
    assert meta.get("gpkg_ok") is not True


def test_importar_rede_rm_status_falhou_pulou(qgis_app, tmp_path, monkeypatch):
    """RM com status != 'ok' no manifest deve retornar pulou informando o status."""
    _skip_sem_qgis(qgis_app)

    manifest = {
        "schema_version": 1,
        "tag": "osm-20260929",
        "rms": {
            "77777": {
                "id": "77777",
                "status": "falhou",
                "erro": "Timeout na extração",
            },
        },
    }

    monkeypatch.setattr(github_release, "fetch_manifest", lambda *a, **kw: manifest)

    recorte_falha = Recorte.de_rm("77777", "RM Falha", ["7777701"])
    gpkg_destino = str(tmp_path / "destino.gpkg")

    resultado = osm_pipeline.importar_rede_rm(recorte_falha, gpkg_destino)
    meta = resultado.get("metadata", {})

    assert "pulou" in meta
    assert "falhou" in meta["pulou"]
    assert meta.get("gpkg_ok") is not True


def test_importar_rede_rm_zip_sem_camada_erro(qgis_app, tmp_path, monkeypatch):
    """Zip sem uma das camadas esperadas (ex.: sem osm_problemas) deve retornar metadata com erro."""
    _skip_sem_qgis(qgis_app)

    # Cria zip faltando osm_problemas_rm99999
    zip_incompleto = _cria_gpkg_e_zip(str(tmp_path), id_rm="99999", incluir_problemas=False)

    manifest = {
        "schema_version": 1,
        "tag": "osm-20260929",
        "rms": {
            "99999": {
                "id": "99999",
                "status": "ok",
                "asset": "osm_vias_rm99999.gpkg.zip",
            }
        },
    }

    monkeypatch.setattr(github_release, "fetch_manifest", lambda *a, **kw: manifest)
    monkeypatch.setattr(github_release, "fetch_asset", lambda *a, **kw: zip_incompleto)

    recorte = Recorte.de_rm("99999", "RM Teste", ["9999901"])
    gpkg_destino = str(tmp_path / "destino.gpkg")

    resultado = osm_pipeline.importar_rede_rm(recorte, gpkg_destino)
    meta = resultado.get("metadata", {})

    assert "erro" in meta
    assert "osm_problemas_rm99999" in meta["erro"]
    assert meta.get("gpkg_ok") is False
