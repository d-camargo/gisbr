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


def test_carregar_fontes_ibge_tabular_rm_passa_lista_de_codes(tmp_path, monkeypatch):
    """D9: em modo RM o conector recebe a LISTA de códigos (localidades=N6[a,b,c]),
    nunca o sufixo 'rm<id>' — e a camada se chama <id>_rm<id>."""
    gpkg = str(tmp_path / "test_agro_rm.gpkg")

    muni_layer = create_nonempty_mem_layer()
    monkeypatch.setattr(diagnostico.agro_pipeline, "_municipio_poligono", lambda code, name=None: muni_layer)

    tbl_layer = QgsVectorLayer(
        "None?field=code_muni:string&field=var_id:string&field=var_nome:string&field=unidade:string&field=produto:string&field=periodo:string&field=valor:double",
        "tbl", "memory"
    )
    dp = tbl_layer.dataProvider()
    for code, valor in (("3106200", 100.0), ("3106705", 250.0)):
        f = QgsFeature(tbl_layer.fields())
        f.setAttributes([code, "109", "Área colhida", "Hectares", "Milho em grão", "2023", valor])
        dp.addFeatures([f])
    tbl_layer.updateExtents()

    capturas = []
    def mock_fetch(agregado, codes, layer_name, **kwargs):
        capturas.append((agregado, codes, layer_name))
        return tbl_layer
    monkeypatch.setattr(diagnostico.ibge_agregados, "fetch_layer", mock_fetch)
    monkeypatch.setattr(diagnostico, "_layers_existentes", lambda path: set())
    monkeypatch.setattr(diagnostico, "_grava_gpkg", lambda layer, path, name: (True, ""))
    monkeypatch.setattr(QgsProject.instance(), "addMapLayer", lambda lyr: None)

    orig_qgs_vl = QgsVectorLayer
    def mock_qgs_vl(uri, name, provider):
        if uri.startswith(gpkg):
            return muni_layer
        return orig_qgs_vl(uri, name, provider)

    monkeypatch.setattr(diagnostico, "QgsVectorLayer", mock_qgs_vl)

    recorte = Recorte.de_rm("04501", "Região Metropolitana de Belo Horizonte",
                            ["3106200", "3106705"], nomes=["Belo Horizonte", "Betim"])
    res = diagnostico.carregar_fontes(["ibge_pam_temporarias"], None, None, None, gpkg,
                                      recorte=recorte)
    assert "ibge_pam_temporarias" in res["ok"]
    assert len(capturas) == 1
    _agregado, codes_enviados, layer_name = capturas[0]
    assert list(codes_enviados) == ["3106200", "3106705"]
    assert layer_name == "ibge_pam_temporarias_rm04501"


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


# --- testes do _filtro_para (D5) --------------------------------

from gisbr.core.recorte import Recorte


def test_filtro_para_cql_codigo_1_codigo():
    s = {"filtro": {"tipo": "cql_codigo", "campo": "cod_municipio_ibge"}}
    cql, usa_bbox = diagnostico._filtro_para(s, "3106200", "Contagem")
    assert cql == "cod_municipio_ibge = 3106200"
    assert usa_bbox is False

    recorte = Recorte.de_municipio("3106200", "Contagem")
    cql_rec, usa_bbox_rec = diagnostico._filtro_para(s, recorte)
    assert cql_rec == "cod_municipio_ibge = 3106200"
    assert usa_bbox_rec is False


def test_filtro_para_cql_codigo_n_codigos():
    s = {"filtro": {"tipo": "cql_codigo", "campo": "cod_municipio_ibge"}}
    cql, usa_bbox = diagnostico._filtro_para(s, ["3106200", "3106705"])
    assert cql == "cod_municipio_ibge IN (3106200,3106705)"
    assert usa_bbox is False

    recorte = Recorte.de_rm("rm1", "RM Belo Horizonte", ["3106200", "3106705"])
    cql_rec, usa_bbox_rec = diagnostico._filtro_para(s, recorte)
    assert cql_rec == "cod_municipio_ibge IN (3106200,3106705)"
    assert usa_bbox_rec is False


def test_filtro_para_cql_nome_1_nome():
    s = {"filtro": {"tipo": "cql_nome", "campo": "municipio"}}
    cql, usa_bbox = diagnostico._filtro_para(s, "3106200", "Contagem")
    assert cql == "municipio = 'Contagem'"
    assert usa_bbox is False

    cql_apostrofo, _ = diagnostico._filtro_para(s, "1505536", "Pau d'Arco")
    assert cql_apostrofo == "municipio = 'Pau d''Arco'"


def test_filtro_para_cql_nome_n_nomes():
    s = {"filtro": {"tipo": "cql_nome", "campo": "municipio"}}
    cql, usa_bbox = diagnostico._filtro_para(s, ["3106200", "1505536"], ["Contagem", "Pau d'Arco"])
    assert cql == "municipio IN ('Contagem','Pau d''Arco')"
    assert usa_bbox is False

    # via de produção: o motor passa o Recorte (que carrega os nomes) — D5
    recorte = Recorte.de_rm("rm1", "RM", ["3106200", "1505536"], nomes=["Contagem", "Pau d'Arco"])
    cql_rec, usa_bbox_rec = diagnostico._filtro_para(s, recorte)
    assert cql_rec == "municipio IN ('Contagem','Pau d''Arco')"
    assert usa_bbox_rec is False


def test_carrega_geobr_rm_multi_codigo(monkeypatch):
    from unittest.mock import MagicMock
    from gisbr.core.recorte import Recorte

    captured_runs = []

    def mock_run(algo, params, **kwargs):
        captured_runs.append((algo, dict(params)))
        if algo.startswith("gisbr:"):
            dummy = MagicMock()
            dummy.crs.return_value = "EPSG:4674"
            return {"OUTPUT": dummy}
        if algo == "native:mergevectorlayers":
            dummy = MagicMock()
            return {"OUTPUT": dummy}
        if algo == "native:extractbyexpression":
            layer_mock = create_nonempty_mem_layer()
            layer_mock.featureCount = lambda: 5
            return {"OUTPUT": layer_mock}
        return {}

    mock_proc = types.ModuleType("processing")
    mock_proc.run = mock_run
    monkeypatch.setitem(sys.modules, "processing", mock_proc)

    # 1 UF, 2 códigos (ex.: RMBH: Contagem 3106200, Betim 3106705)
    recorte_1uf = Recorte.de_rm("rm04501", "RMBH", ["3106200", "3106705"])
    s = {"id": "geobr_municipio", "protocolo": "geobr", "algo": "read_municipality", "recorte": "code"}

    res_layer = diagnostico._carrega_geobr(s, recorte_1uf, "geobr_municipio_rm04501")
    assert res_layer is not None
    assert res_layer.isValid()

    # Confere chamadas
    read_calls = [call for call in captured_runs if call[0] == "gisbr:read_municipality"]
    assert len(read_calls) == 1
    assert read_calls[0][1]["CODE"] == "31"

    extract_calls = [call for call in captured_runs if call[0] == "native:extractbyexpression"]
    assert len(extract_calls) == 1
    expr = extract_calls[0][1]["EXPRESSION"]
    assert "'3106200'" in expr and "'3106705'" in expr

    # 2 UFs (ex.: RIDE DF/GO: 5300108, 5200000)
    captured_runs.clear()
    recorte_2uf = Recorte.de_rm("ride1", "RIDE", ["5300108", "5200000"])
    res_layer2 = diagnostico._carrega_geobr(s, recorte_2uf, "geobr_municipio_ride1")
    assert res_layer2 is not None

    read_calls2 = [call for call in captured_runs if call[0] == "gisbr:read_municipality"]
    assert len(read_calls2) == 2
    codes_sent = {call[1]["CODE"] for call in read_calls2}
    assert codes_sent == {"53", "52"}

    merge_calls = [call for call in captured_runs if call[0] == "native:mergevectorlayers"]
    assert len(merge_calls) == 1

    extract_calls2 = [call for call in captured_runs if call[0] == "native:extractbyexpression"]
    assert len(extract_calls2) == 1
    expr2 = extract_calls2[0][1]["EXPRESSION"]
    assert "'5300108'" in expr2 and "'5200000'" in expr2


def test_carrega_geobr_favelas_sem_parquet_pula_rm(monkeypatch):
    from gisbr.core.recorte import Recorte
    from gisbr.core import capabilities

    monkeypatch.setattr(capabilities, "parquet_backend", lambda: None)
    s = {"id": "geobr_favelas", "protocolo": "geobr", "algo": "read_favela_v2", "recorte": "code", "requer_parquet": True}
    recorte = Recorte.de_rm("rm04501", "RMBH", ["3106200", "3106705"])

    layer = diagnostico._carrega_geobr(s, recorte, "geobr_favelas_rm04501")
    assert layer is not None
    assert not layer.isValid()
    assert "requer driver Parquet" in getattr(layer, "error_msg", "")


def test_carregar_fontes_raster_cog_rm_skip_e_tree(tmp_path, monkeypatch):
    gpkg = str(tmp_path / "test_raster_rm.gpkg")
    source_raster = {
        "id": "mapbiomas_cobertura",
        "protocolo": "raster_cog",
        "endpoint": "http://example.com/cog.tif",
        "ano": 2023
    }
    monkeypatch.setattr(diagnostico, "SOURCES", [source_raster])
    monkeypatch.setattr(diagnostico, "_layers_existentes", lambda path: set())

    rm_layer = create_nonempty_mem_layer()

    from gisbr.core.recorte import Recorte
    recorte_rm = Recorte.de_rm("04501", "RM Belo Horizonte", ["3106200", "3106705"])

    monkeypatch.setattr("gisbr.core.recorte.camada_do_recorte", lambda rec, **kwargs: rm_layer)
    monkeypatch.setattr(diagnostico, "_grava_gpkg", lambda layer, path, name: (True, ""))

    fetch_calls = []
    masks_used = []

    def mock_fetch_raster(url, mask_layer, output_path, layer_name, feedback=None, lang="pt"):
        fetch_calls.append(output_path)
        masks_used.append(mask_layer)
        with open(output_path, "wb") as f:
            f.write(b"fake tif")
        class DummyRaster:
            def isValid(self):
                return True
        return DummyRaster()

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

    res1 = diagnostico.carregar_fontes(["mapbiomas_cobertura"], None, None, None, gpkg, recorte=recorte_rm)
    assert "mapbiomas_cobertura" in res1["ok"]
    assert len(res1["falhou"]) == 0
    assert len(res1["pulou"]) == 0
    assert len(fetch_calls) == 1

    tif_path = fetch_calls[0]
    assert tif_path == str(tmp_path / "mapbiomas_cobertura_2023_rm04501.tif")
    assert masks_used[0] == rm_layer

    res2 = diagnostico.carregar_fontes(["mapbiomas_cobertura"], None, None, None, gpkg, recorte=recorte_rm)
    assert len(res2["ok"]) == 0
    assert len(res2["pulou"]) == 1
    assert res2["pulou"][0][0] == "mapbiomas_cobertura"
    assert "ja existe" in res2["pulou"][0][1]
    assert "mapbiomas_cobertura_2023_rm04501.tif" in res2["pulou"][0][1]


def test_carregar_fontes_osm_rm_pulou(tmp_path, monkeypatch):
    from gisbr.core.recorte import Recorte
    gpkg = str(tmp_path / "test_osm_rm.gpkg")

    def fail_pipeline(*args, **kwargs):
        pytest.fail("Pipeline OSM nao deveria ser invocado em modo RM")

    monkeypatch.setattr(diagnostico.osm_pipeline, "build_osm_municipal_network", fail_pipeline)
    monkeypatch.setattr(diagnostico.poi_pipeline, "build_osm_municipal_pois", fail_pipeline)

    recorte_rm = Recorte.de_rm("04501", "RM Belo Horizonte", ["3106200", "3106705"])

    res = diagnostico.carregar_fontes(["osm_vias", "osm_pois"], None, None, None, gpkg, recorte=recorte_rm)

    assert len(res["falhou"]) == 0
    assert len(res["ok"]) == 0
    assert len(res["pulou"]) == 2

    pulou_dict = dict(res["pulou"])
    assert "osm_vias" in pulou_dict
    assert "osm_pois" in pulou_dict

    expected_msg = "a rede viária e os POIs do OpenStreetMap rodam por município; escolha o recorte Município para carregá-los"
    assert pulou_dict["osm_vias"] == expected_msg
    assert pulou_dict["osm_pois"] == expected_msg


def test_carregar_fontes_modo_rm_integracao(tmp_path, monkeypatch):
    from gisbr.core.recorte import Recorte

    gpkg = str(tmp_path / "test_rm_integ.gpkg")

    sources = [
        {
            "id": "wfs_cql",
            "protocolo": "wfs",
            "endpoint": "http://example.com/wfs",
            "type_name": "ns:camada_cql",
            "filtro": {"tipo": "cql_codigo", "campo": "code_muni"},
        },
        {
            "id": "wfs_bbox",
            "protocolo": "wfs",
            "endpoint": "http://example.com/wfs",
            "type_name": "ns:camada_bbox",
            "filtro": {"tipo": "bbox"},
        },
    ]
    monkeypatch.setattr(diagnostico, "SOURCES", sources)

    recorte_rm = Recorte.de_rm("04501", "RM Belo Horizonte", ["3106200", "3106705", "3101508"])

    rm_poly_layer = create_nonempty_mem_layer()
    monkeypatch.setattr("gisbr.core.recorte.camada_do_recorte", lambda rec, **kwargs: rm_poly_layer)

    wfs_calls = []

    def mock_fetch_layer(endpoint, type_name, layer_name, srs="EPSG:4674", cql_filter=None, bbox=None, feedback=None):
        wfs_calls.append({
            "endpoint": endpoint,
            "type_name": type_name,
            "layer_name": layer_name,
            "cql_filter": cql_filter,
            "bbox": bbox,
        })
        return create_nonempty_mem_layer()

    monkeypatch.setattr(diagnostico.wfs, "fetch_layer", mock_fetch_layer)
    monkeypatch.setattr(diagnostico, "_recorta_poligono", lambda layer, poly, name: layer)
    monkeypatch.setattr(QgsProject.instance(), "addMapLayer", lambda lyr: None)

    # Primeira execução: carrega ambas as fontes
    res1 = diagnostico.carregar_fontes(["wfs_cql", "wfs_bbox"], None, None, None, gpkg, recorte=recorte_rm)

    assert res1["ok"] == ["wfs_cql", "wfs_bbox"]
    assert res1["falhou"] == []
    assert res1["pulou"] == []

    # Contrato D2:
    # 1) Duas chamadas ao conector (uma por fonte), camadas nomeadas <id>_rm<id>
    assert len(wfs_calls) == 2
    cql_call = next(c for c in wfs_calls if c["layer_name"] == "wfs_cql_rm04501")
    bbox_call = next(c for c in wfs_calls if c["layer_name"] == "wfs_bbox_rm04501")

    # 2) Filtro cql_codigo enviado com IN (...) para 3 municípios
    assert cql_call["cql_filter"] == "code_muni IN (3106200,3106705,3101508)"
    assert bbox_call["cql_filter"] is None

    # 3) GPKG gravado com uma camada por fonte (<id>_rm<id>) + limite da RM (rm_<id> / D7)
    existentes1 = diagnostico._layers_existentes(gpkg)
    assert "wfs_cql_rm04501" in existentes1
    assert "wfs_bbox_rm04501" in existentes1
    assert "rm_04501" in existentes1

    # Segunda execução sem force ("Atualizar"): pula por skip-exists
    wfs_calls.clear()
    res2 = diagnostico.carregar_fontes(["wfs_cql", "wfs_bbox"], None, None, None, gpkg, recorte=recorte_rm)

    assert res2["ok"] == []
    assert res2["falhou"] == []
    assert len(res2["pulou"]) == 2
    pulou_sids = [sid for sid, _ in res2["pulou"]]
    assert "wfs_cql" in pulou_sids
    assert "wfs_bbox" in pulou_sids
    assert len(wfs_calls) == 0





