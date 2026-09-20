# -*- coding: utf-8 -*-
"""Testes das extensoes do motor do diagnostico para o censo (D4, D6, D8, D9)."""

import sys
import types
import pytest

pytest.importorskip("qgis.core")

from qgis.core import QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry, QgsPointXY
from gisbr.core import catalog, diagnostico, osm_pipeline
from gisbr.core.censo_join import CensoJoinError


def create_nonempty_mem_layer():
    lyr = QgsVectorLayer("Point?crs=EPSG:4674", "dummy", "memory")
    dp = lyr.dataProvider()
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
    dp.addFeatures([f])
    lyr.updateExtents()
    return lyr


def test_carrega_geobr_ano_valido_e_invalido(monkeypatch):
    monkeypatch.setattr(catalog, "available_years", lambda geo: [2000, 2010, 2022])

    captured_params = {}

    def mock_run(algo, params):
        captured_params.update(params)
        return {"OUTPUT": "mem_layer"}

    mock_proc = types.ModuleType("processing")
    mock_proc.run = mock_run
    monkeypatch.setitem(sys.modules, "processing", mock_proc)

    mem_layer = create_nonempty_mem_layer()

    monkeypatch.setattr(diagnostico, "_resolve_out", lambda out, name: mem_layer)

    s = {"id": "geobr_setores", "protocolo": "geobr", "algo": "read_census_tract", "recorte": "code"}

    # Ano valido -> passa "YEAR": idx
    layer = diagnostico._carrega_geobr(s, "3106200", "geobr_setores_3106200", ano=2010)
    assert captured_params.get("YEAR") == 1
    assert not hasattr(layer, "ano_invalido_msg")

    # Ano invalido -> nao passa "YEAR", anexa ano_invalido_msg
    captured_params.clear()
    layer_inv = diagnostico._carrega_geobr(s, "3106200", "geobr_setores_3106200", ano=1990)
    assert "YEAR" not in captured_params
    assert hasattr(layer_inv, "ano_invalido_msg")
    assert "1990" in layer_inv.ano_invalido_msg


def test_carregar_fontes_skip_msg_d9(tmp_path, monkeypatch):
    gpkg = str(tmp_path / "test.gpkg")

    # Mock layers_existentes to pretend layer already exists
    monkeypatch.setattr(diagnostico, "_layers_existentes", lambda path: {"geobr_setores_3106200"})

    res = diagnostico.carregar_fontes(["geobr_setores"], 3106200, "Contagem", None, gpkg)
    assert len(res["pulou"]) == 1
    sid, msg = res["pulou"][0]
    assert sid == "geobr_setores"
    assert "Atualizar bases já baixadas" in msg


def test_carregar_fontes_censo_backend_ausente_d6(tmp_path, monkeypatch):
    gpkg = str(tmp_path / "test.gpkg")
    mem_layer = create_nonempty_mem_layer()

    monkeypatch.setattr(diagnostico, "_layers_existentes", lambda path: set())
    monkeypatch.setattr(diagnostico, "_busca_camada", lambda *args, **kwargs: mem_layer)
    monkeypatch.setattr(diagnostico, "_grava_gpkg", lambda layer, path, name: (True, ""))
    monkeypatch.setattr(QgsProject.instance(), "addMapLayer", lambda lyr: None)

    orig_qgs_vl = QgsVectorLayer
    def mock_qgs_vl(uri, name, provider):
        if uri.startswith(gpkg):
            return mem_layer
        return orig_qgs_vl(uri, name, provider)

    monkeypatch.setattr(diagnostico, "QgsVectorLayer", mock_qgs_vl)

    def mock_anexar_censo(*args, **kwargs):
        raise CensoJoinError("Backend Parquet nao instalado.")

    monkeypatch.setattr(diagnostico.censo_join, "anexar_censo", mock_anexar_censo)

    logs = []
    class DummyFeedback:
        def pushInfo(self, msg):
            logs.append(msg)

    # Calling with feedback=None should survive without error
    res_no_fb = diagnostico.carregar_fontes(
        ["geobr_setores"], 3106200, "Contagem", None, gpkg,
        censo_ano=2010, censo_datasets=("Basico",)
    )
    assert "geobr_setores" in res_no_fb["ok"]

    # Calling with feedback should record the warning log
    res_fb = diagnostico.carregar_fontes(
        ["geobr_setores"], 3106200, "Contagem", None, gpkg,
        feedback=DummyFeedback(), censo_ano=2010, censo_datasets=("Basico",)
    )
    assert "geobr_setores" in res_fb["ok"]
    assert any("Backend Parquet nao instalado" in m for m in logs)


def test_diagnostico_dock_censo_ui(qgis_app, monkeypatch):
    if qgis_app is None:
        pytest.skip("qgis app not available")

    from qgis.PyQt.QtCore import QSettings, Qt
    from gisbr.gui.diagnostico_dock import DiagnosticoDock

    qs = QSettings()
    qs.remove("gisbr/censo_ano")
    qs.remove("gisbr/censo_datasets")

    dock = DiagnosticoDock(iface=None)
    assert hasattr(dock, "grp_censo")
    assert dock.grp_censo.isCheckable()
    assert not dock.grp_censo.isChecked()

    assert dock.cmb_censo_ano.count() > 0
    checked_ds = dock._get_checked_censo_datasets()
    assert "Basico" in checked_ds

    dock.grp_censo.setChecked(True)
    if dock.cmb_censo_ano.count() > 1:
        dock.cmb_censo_ano.setCurrentIndex(0)
        assert "Basico" in dock._get_checked_censo_datasets()

    saved_ano = qs.value("gisbr/censo_ano")
    saved_ds = qs.value("gisbr/censo_datasets")
    assert saved_ano is not None
    assert "Basico" in (saved_ds if isinstance(saved_ds, list) else [saved_ds])

    # Test tab Censo enabled/disabled & tooltip (D3)
    from gisbr.gui.diagnostico_dock import TAB_CENSO, TAB_LOG
    assert not dock.tabs.isTabEnabled(TAB_CENSO)
    assert "Select 'Setores censitarios" in dock.tabs.tabToolTip(TAB_CENSO)

    # Find and check geobr_setores item -> enables tab Censo
    setores_item = None
    for i in range(dock.tree.topLevelItemCount()):
        parent = dock.tree.topLevelItem(i)
        for j in range(parent.childCount()):
            child = parent.child(j)
            if child.data(0, Qt.ItemDataRole.UserRole) == "geobr_setores":
                setores_item = child
                break

    assert setores_item is not None
    setores_item.setCheckState(0, Qt.CheckState.Checked)
    assert dock.tabs.isTabEnabled(TAB_CENSO)
    assert dock.tabs.tabToolTip(TAB_CENSO) == ""
    setores_item.setCheckState(0, Qt.CheckState.Unchecked)
    assert not dock.tabs.isTabEnabled(TAB_CENSO)

    captured_calls = []
    def mock_carregar_fontes(*args, **kwargs):
        captured_calls.append((args, kwargs))
        return {"ok": [], "falhou": [], "pulou": []}

    monkeypatch.setattr(diagnostico, "carregar_fontes", mock_carregar_fontes)
    dock.ed_muni.setText("3106200")
    dock.ed_gpkg.setText("/tmp/dummy.gpkg")

    for i in range(dock.tree.topLevelItemCount()):
        parent = dock.tree.topLevelItem(i)
        for j in range(parent.childCount()):
            child = parent.child(j)
            sid = child.data(0, Qt.ItemDataRole.UserRole)
            if sid and sid != "geobr_setores":
                child.setCheckState(0, Qt.CheckState.Checked)
                break

    dock._munis = {"3106200": ("Belo Horizonte", (0, 0, 1, 1))}
    dock._on_carregar()

    assert "Notice: the Census option only applies to census tracts" in dock.txt_log.toPlainText()
    assert len(captured_calls) == 1
    assert captured_calls[0][1].get("censo_ano") is not None
    assert "Basico" in captured_calls[0][1].get("censo_datasets", ())


def test_diagnostico_dock_censo_catalog_fallback(qgis_app, monkeypatch):
    if qgis_app is None:
        pytest.skip("qgis app not available")

    from gisbr.gui.diagnostico_dock import DiagnosticoDock
    from gisbr.core import catalog_censo

    def mock_available_years():
        raise RuntimeError("Network offline")

    monkeypatch.setattr(catalog_censo, "available_years", mock_available_years)

    dock = DiagnosticoDock(iface=None)
    assert "Failed to load censobr catalog" in dock.txt_log.toPlainText()
    assert dock.cmb_censo_ano.count() == 3
    assert dock.cmb_censo_ano.itemText(0) == "2000"
    assert dock.cmb_censo_ano.itemText(1) == "2010"
    assert dock.cmb_censo_ano.itemText(2) == "2022"


def test_usou_bbox_ibge_tabular():
    assert diagnostico._usou_bbox({"protocolo": "ibge_tabular"}, True) is False


def test_carregar_fontes_ibge_tabular_sucesso(tmp_path, monkeypatch):
    gpkg = str(tmp_path / "test_agro.gpkg")

    muni_layer = create_nonempty_mem_layer()
    monkeypatch.setattr(diagnostico.agro_pipeline, "_municipio_poligono", lambda code, name=None: muni_layer)

    tbl_layer = QgsVectorLayer(
        "None?field=var_id:string&field=var_nome:string&field=unidade:string&field=produto:string&field=periodo:string&field=valor:double",
        "tbl", "memory"
    )
    dp = tbl_layer.dataProvider()
    f = QgsFeature(tbl_layer.fields())
    f.setAttributes(["109", "Área colhida", "Hectares", "Milho em grão", "2023", 1500.0])
    dp.addFeatures([f])
    tbl_layer.updateExtents()

    monkeypatch.setattr(diagnostico.ibge_agregados, "fetch_layer", lambda *args, **kwargs: tbl_layer)
    monkeypatch.setattr(diagnostico, "_layers_existentes", lambda path: set())
    monkeypatch.setattr(diagnostico, "_grava_gpkg", lambda layer, path, name: (True, ""))
    monkeypatch.setattr(QgsProject.instance(), "addMapLayer", lambda lyr: None)

    orig_qgs_vl = QgsVectorLayer
    def mock_qgs_vl(uri, name, provider):
        if uri.startswith(gpkg):
            return muni_layer
        return orig_qgs_vl(uri, name, provider)

    monkeypatch.setattr(diagnostico, "QgsVectorLayer", mock_qgs_vl)

    res = diagnostico.carregar_fontes(["ibge_pam_temporarias"], 3106200, "Belo Horizonte", None, gpkg)
    assert "ibge_pam_temporarias" in res["ok"]
    assert len(res["falhou"]) == 0
    assert len(res["pulou"]) == 0


def test_carregar_fontes_ibge_tabular_sem_dado(tmp_path, monkeypatch):
    gpkg = str(tmp_path / "test_agro_empty.gpkg")

    muni_layer = create_nonempty_mem_layer()
    monkeypatch.setattr(diagnostico.agro_pipeline, "_municipio_poligono", lambda code, name=None: muni_layer)

    tbl_layer = QgsVectorLayer(
        "None?field=var_id:string&field=var_nome:string&field=unidade:string&field=produto:string&field=periodo:string&field=valor:double",
        "tbl", "memory"
    )
    dp = tbl_layer.dataProvider()
    f = QgsFeature(tbl_layer.fields())
    f.setAttributes(["109", "Área colhida", "Hectares", "Milho em grão", "2023", None])
    dp.addFeatures([f])
    tbl_layer.updateExtents()

    monkeypatch.setattr(diagnostico.ibge_agregados, "fetch_layer", lambda *args, **kwargs: tbl_layer)
    monkeypatch.setattr(diagnostico, "_layers_existentes", lambda path: set())

    res = diagnostico.carregar_fontes(["ibge_pam_temporarias"], 3106200, "Belo Horizonte", None, gpkg)
    assert len(res["ok"]) == 0
    assert len(res["falhou"]) == 0
    assert len(res["pulou"]) == 1
    sid, msg = res["pulou"][0]
    assert sid == "ibge_pam_temporarias"
    assert "descartados" in msg or "sem valor" in msg or "sem produto" in msg


def test_carregar_fontes_zip_remoto_indisponivel(tmp_path, monkeypatch):
    gpkg = str(tmp_path / "test_zip_indisp.gpkg")
    source_indisp = {
        "id": "teste_zip_indisponivel",
        "protocolo": "zip_remoto",
        "indisponivel": "Host app.anm.gov.br indisponível (connection timed out)",
        "origem_url": "https://app.anm.gov.br/",
    }
    monkeypatch.setattr(diagnostico, "SOURCES", [source_indisp])
    monkeypatch.setattr(diagnostico, "_layers_existentes", lambda path: set())

    def mock_fetch_layer(*args, **kwargs):
        pytest.fail("zip_remoto.fetch_layer nao deveria ser chamado para fonte indisponivel")

    monkeypatch.setattr(diagnostico.zip_remoto, "fetch_layer", mock_fetch_layer)

    res = diagnostico.carregar_fontes(["teste_zip_indisponivel"], 3106200, "Belo Horizonte", None, gpkg)

    assert len(res["ok"]) == 0
    assert len(res["falhou"]) == 0
    assert len(res["pulou"]) == 1
    sid, msg = res["pulou"][0]
    assert sid == "teste_zip_indisponivel"
    assert "Host app.anm.gov.br indisponível" in msg
    assert "https://app.anm.gov.br/" in msg


def test_carregar_fontes_zip_remoto_feliz(tmp_path, monkeypatch):
    gpkg = str(tmp_path / "test_zip_feliz.gpkg")
    source_feliz = {
        "id": "teste_zip_feliz",
        "protocolo": "zip_remoto",
        "url": "https://exemplo.gov.br/dados.zip",
        "subset": "FASE = 'LAVRA'",
        "srs": "EPSG:4674",
        "filtro": {"tipo": "bbox"},
    }
    monkeypatch.setattr(diagnostico, "SOURCES", [source_feliz])
    monkeypatch.setattr(diagnostico, "_layers_existentes", lambda path: set())

    mem_layer = create_nonempty_mem_layer()
    fetch_calls = []

    def mock_fetch_layer(url, layer_name, srs="EPSG:4674", subset=None, feedback=None):
        fetch_calls.append({"url": url, "layer_name": layer_name, "srs": srs, "subset": subset})
        return mem_layer

    monkeypatch.setattr(diagnostico.zip_remoto, "fetch_layer", mock_fetch_layer)

    muni_layer = create_nonempty_mem_layer()
    monkeypatch.setattr(diagnostico, "_municipio_poligono", lambda code: muni_layer)
    monkeypatch.setattr(diagnostico, "_recorta_poligono", lambda layer, poly, name: layer)
    monkeypatch.setattr(diagnostico, "_grava_gpkg", lambda layer, path, name: (True, ""))
    monkeypatch.setattr(QgsProject.instance(), "addMapLayer", lambda lyr: None)

    orig_qgs_vl = QgsVectorLayer
    def mock_qgs_vl(uri, name, provider):
        if uri.startswith(gpkg):
            return mem_layer
        return orig_qgs_vl(uri, name, provider)

    monkeypatch.setattr(diagnostico, "QgsVectorLayer", mock_qgs_vl)

    res = diagnostico.carregar_fontes(["teste_zip_feliz"], 3106200, "Belo Horizonte", None, gpkg)

    assert "teste_zip_feliz" in res["ok"]
    assert len(res["falhou"]) == 0
    assert len(res["pulou"]) == 0

    assert len(fetch_calls) == 1
    assert fetch_calls[0]["url"] == "https://exemplo.gov.br/dados.zip"
    assert fetch_calls[0]["subset"] == "FASE = 'LAVRA'"



def test_carregar_fontes_raster_cog_skip_e_tree(tmp_path, monkeypatch):
    gpkg = str(tmp_path / "test_raster.gpkg")
    source_raster = {
        "id": "mapbiomas_cobertura",
        "protocolo": "raster_cog",
        "endpoint": "http://example.com/cog.tif",
        "ano": 2022
    }
    monkeypatch.setattr(diagnostico, "SOURCES", [source_raster])
    monkeypatch.setattr(diagnostico, "_layers_existentes", lambda path: set())
    
    muni_layer = create_nonempty_mem_layer()
    monkeypatch.setattr(diagnostico, "_municipio_poligono", lambda code: muni_layer)
    
    fetch_calls = []
    
    from qgis.core import QgsRasterLayer
    def mock_fetch_raster(url, mask_layer, output_path, layer_name, feedback=None, lang="pt"):
        fetch_calls.append(output_path)
        with open(output_path, "wb") as f:
            f.write(b"fake tif")
        class DummyRaster:
            def isValid(self):
                return True
        rl = DummyRaster()
        return rl

    monkeypatch.setattr(diagnostico.cog_raster, "fetch_layer", mock_fetch_raster)
    
    added_layers = []
    def mock_addMapLayer(layer, addToLegend=True):
        added_layers.append((layer, addToLegend))
        return True
        
    monkeypatch.setattr(QgsProject.instance(), "addMapLayer", mock_addMapLayer)
    
    class MockRoot:
        def addLayer(self, layer):
            added_layers.append((layer, "root.addLayer"))
            
    monkeypatch.setattr(QgsProject.instance(), "layerTreeRoot", lambda: MockRoot())
    
    res1 = diagnostico.carregar_fontes(["mapbiomas_cobertura"], 3106200, "Contagem", None, gpkg)
    assert "mapbiomas_cobertura" in res1["ok"]
    assert len(res1["falhou"]) == 0
    assert len(res1["pulou"]) == 0
    assert len(fetch_calls) == 1
    
    tif_path = fetch_calls[0]
    import os
    assert tif_path == str(tmp_path / "mapbiomas_cobertura_2022_3106200.tif")
    
    assert any(x[1] == "root.addLayer" for x in added_layers)
    
    res2 = diagnostico.carregar_fontes(["mapbiomas_cobertura"], 3106200, "Contagem", None, gpkg)
    assert len(res2["ok"]) == 0
    assert len(res2["pulou"]) == 1
    assert res2["pulou"][0][0] == "mapbiomas_cobertura"
    assert "ja existe" in res2["pulou"][0][1]


# --- cancelamento do osm_vias vira "pulou", nao "falhou" --------

def test_carregar_fontes_osm_vias_cancelado_vira_pulou(tmp_path, monkeypatch):
    gpkg = str(tmp_path / "test.gpkg")

    monkeypatch.setattr(diagnostico, "_layers_existentes", lambda path: set())
    monkeypatch.setattr(
        osm_pipeline, "build_osm_municipal_network",
        lambda *args, **kwargs: {
            "raw_cache": None,
            "layers": {"osm_links_raw": None, "osm_links": None, "osm_nodes": None, "osm_problemas": None},
            "metadata": {"code_muni": "3106200", "nome_muni": "Contagem", "cancelado": True},
        })

    res = diagnostico.carregar_fontes(["osm_vias"], 3106200, "Contagem", None, gpkg)

    assert res["ok"] == []
    assert res["falhou"] == []
    assert len(res["pulou"]) == 1
    assert res["pulou"][0] == ("osm_vias", "cancelado pelo usuário")
