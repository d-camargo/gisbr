# -*- coding: utf-8 -*-
"""Testes das extensoes do motor do diagnostico para o censo (D4, D6, D8, D9)."""

import sys
import types
import pytest

pytest.importorskip("qgis.core")

from qgis.core import QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry, QgsPointXY
from gisbr.core import catalog, diagnostico
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
