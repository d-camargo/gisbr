# -*- coding: utf-8 -*-
"""Testes do ícone do plugin e dos rótulos/estilos de ação QAction no QGIS."""

import os
import pytest

pytest.importorskip("qgis.core")

try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QToolBar

from gisbr.plugin_icon import icon_path, plugin_icon
from gisbr.provider import GeobrProvider


def test_icon_path_valido():
    path = icon_path()
    assert path is not None
    assert path.endswith("icon.svg")
    assert os.path.exists(path)


def test_plugin_icon_valido(qgis_app):
    if qgis_app is None:
        pytest.skip("qgis app não disponível")
    assert plugin_icon().isNull() is False


def test_geobr_provider_icon_valido(qgis_app):
    if qgis_app is None:
        pytest.skip("qgis app não disponível")
    provider = GeobrProvider()
    assert provider.icon().isNull() is False


def test_action_rotulos(qgis_app):
    if qgis_app is None:
        pytest.skip("qgis app não disponível")
    action = QAction(plugin_icon(), "GISBR")
    assert action.iconText() == "GISBR"
    assert action.text() == "GISBR"
    assert action.toolTip() == "GISBR"


def test_toolbar_button_style_override(qgis_app):
    if qgis_app is None:
        pytest.skip("qgis app não disponível")
    action = QAction(plugin_icon(), "GISBR")
    toolbar = QToolBar()
    toolbar.addAction(action)
    button = toolbar.widgetForAction(action)
    assert button is not None
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    assert button.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextBesideIcon
    assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly


def test_geobr_provider_id_e_nome(qgis_app):
    if qgis_app is None:
        pytest.skip("qgis app não disponível")
    provider = GeobrProvider()
    assert provider.name() == "GISBR"
    assert provider.id() == "gisbr"

