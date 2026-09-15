# -*- coding: utf-8 -*-
"""Ponto de entrada do plugin: registra/desregistra o GeobrProvider."""

from qgis.core import QgsApplication

from .core.ssl_support import install_default_ca_certificates
from .provider import GeobrProvider


class GeobrPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        install_default_ca_certificates()

    def initProcessing(self):
        self.provider = GeobrProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def tr(self, s):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("GeobrPlugin", s)

    def initGui(self):
        self.initProcessing()
        try:
            from qgis.PyQt.QtGui import QAction
        except ImportError:
            from qgis.PyQt.QtWidgets import QAction
        from qgis.PyQt.QtCore import Qt
        from .gui.diagnostico_dock import DiagnosticoDock
        from .plugin_icon import plugin_icon
        self.dock = DiagnosticoDock(self.iface)
        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()
        self.action = QAction(plugin_icon(), self.tr("Master Plan Diagnostic (GisBR)"), self.iface.mainWindow())
        self.action.setIconText("GisBR")
        self.action.setCheckable(True)
        self.action.triggered.connect(self.dock.setUserVisible)
        self.iface.addPluginToMenu("GisBR", self.action)
        self.iface.addToolBarIcon(self.action)
        barra = getattr(self.iface, "pluginToolBar", None)
        if barra is not None:
            botao = barra().widgetForAction(self.action)
            if botao is not None:
                botao.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

    def unload(self):
        if self.provider is not None:
            from qgis.PyQt import sip
            if not sip.isdeleted(self.provider):
                QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        if getattr(self, "action", None) is not None:
            self.iface.removePluginMenu("GisBR", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if getattr(self, "dock", None) is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock = None
