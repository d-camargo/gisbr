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

    def initGui(self):
        self.initProcessing()
        try:
            from qgis.PyQt.QtGui import QAction
        except ImportError:
            from qgis.PyQt.QtWidgets import QAction
        from qgis.PyQt.QtCore import Qt, QTimer
        from .gui.diagnostico_dock import DiagnosticoDock
        from .plugin_icon import plugin_icon
        self.dock = DiagnosticoDock(self.iface)
        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()
        self.action = QAction(plugin_icon(), "GISBR", self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.dock.setUserVisible)
        self.iface.addPluginToMenu("GISBR", self.action)
        self.iface.addToolBarIcon(self.action)
        self._ajustar_barra()
        init_signal = getattr(self.iface, "initializationCompleted", None)
        if init_signal is not None:
            try:
                init_signal.connect(self._ajustar_barra)
            except (TypeError, RuntimeError):
                pass
        QTimer.singleShot(0, self._ajustar_barra)

    def _ajustar_barra(self):
        if getattr(self, "action", None) is None:
            return
        barra = getattr(self.iface, "pluginToolBar", None)
        if barra is None:
            return
        tb = barra()
        if tb is None:
            return
        from qgis.PyQt import sip
        if sip.isdeleted(tb) or sip.isdeleted(self.action):
            return
        from qgis.PyQt.QtCore import Qt
        botao = tb.widgetForAction(self.action)
        if botao is not None:
            botao.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            # O estilo muda depois da inserção, e sem recálculo o botão cai no "»".
            if tb.layout() is not None:
                tb.layout().invalidate()
            tb.updateGeometry()
            tb.adjustSize()

    def unload(self):
        init_signal = getattr(self.iface, "initializationCompleted", None)
        if init_signal is not None:
            try:
                init_signal.disconnect(self._ajustar_barra)
            except (TypeError, RuntimeError):
                pass
        if self.provider is not None:
            from qgis.PyQt import sip
            if not sip.isdeleted(self.provider):
                QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        if getattr(self, "action", None) is not None:
            self.iface.removePluginMenu("GISBR", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if getattr(self, "dock", None) is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock = None
