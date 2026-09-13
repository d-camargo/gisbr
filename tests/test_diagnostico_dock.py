# -*- coding: utf-8 -*-
"""Testes headless do painel DiagnosticoDock (D8)."""

import pytest

pytest.importorskip("qgis.core")

from qgis.PyQt.QtCore import Qt
from gisbr.gui import diagnostico_dock
from gisbr.gui.diagnostico_dock import DiagnosticoDock, TAB_CENSO, TAB_LOG
from gisbr.core import catalog_censo

_SETTINGS_STORE = {}


class MemoryQSettings:
    def value(self, key, default=None):
        return _SETTINGS_STORE.get(key, default)

    def setValue(self, key, value):
        _SETTINGS_STORE[key] = value


@pytest.fixture
def dock(qgis_app, monkeypatch):
    if qgis_app is None:
        pytest.skip("qgis app não disponível")

    _SETTINGS_STORE.clear()

    monkeypatch.setattr(catalog_censo, "available_years", lambda: [2000, 2010, 2022])
    monkeypatch.setattr(
        catalog_censo,
        "available_datasets_por_ano",
        lambda: {2000: ["Basico"], 2010: ["Basico", "DomicilioRenda"], 2022: ["Basico"]},
    )
    monkeypatch.setattr(
        diagnostico_dock, "QSettings", lambda *args, **kwargs: MemoryQSettings()
    )

    return DiagnosticoDock(iface=None)


def _find_tree_item_by_user_data(tree, target_id):
    for i in range(tree.topLevelItemCount()):
        parent = tree.topLevelItem(i)
        for j in range(parent.childCount()):
            child = parent.child(j)
            if child.data(0, Qt.ItemDataRole.UserRole) == target_id:
                return child
    return None


def test_dock_tab_count_and_labels(dock):
    assert dock.tabs.count() == 5
    labels = [dock.tabs.tabText(i) for i in range(dock.tabs.count())]
    assert labels == ["Location", "Sources", "Census", "Output", "Log"]


def test_aba_censo_inicialmente_desabilitada(dock):
    assert dock.tabs.isTabEnabled(TAB_CENSO) is False
    assert dock.tabs.tabToolTip(TAB_CENSO) != ""


def test_marcar_desmarcar_geobr_setores_habilita_aba_censo(dock):
    item = _find_tree_item_by_user_data(dock.tree, "geobr_setores")
    assert item is not None

    item.setCheckState(0, Qt.CheckState.Checked)
    assert dock.tabs.isTabEnabled(TAB_CENSO) is True
    assert dock.tabs.tabToolTip(TAB_CENSO) == ""

    item.setCheckState(0, Qt.CheckState.Unchecked)
    assert dock.tabs.isTabEnabled(TAB_CENSO) is False
    assert dock.tabs.tabToolTip(TAB_CENSO) != ""


def test_selected_source_ids(dock):
    for i in range(dock.tree.topLevelItemCount()):
        parent = dock.tree.topLevelItem(i)
        for j in range(parent.childCount()):
            parent.child(j).setCheckState(0, Qt.CheckState.Unchecked)

    item = _find_tree_item_by_user_data(dock.tree, "geobr_setores")
    assert item is not None
    item.setCheckState(0, Qt.CheckState.Checked)

    assert dock._selected_source_ids() == ["geobr_setores"]


def test_log_focar(dock):
    dock._log("oi", focar=True)
    assert "oi" in dock.txt_log.toPlainText()
    assert dock.tabs.currentIndex() == TAB_LOG
