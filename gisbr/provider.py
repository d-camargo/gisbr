# -*- coding: utf-8 -*-
"""GeobrProvider: registra os algoritmos read_* na Caixa de Ferramentas."""

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithms import ALGORITHMS
from .plugin_icon import icon_path


class GeobrProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        for alg_class in ALGORITHMS:
            self.addAlgorithm(alg_class())

    def id(self):
        return "gisbr"

    def name(self):
        return "GisBR"

    def longName(self):
        return self.tr("GisBR — official Brazilian spatial data (IBGE/IPEA)")

    def icon(self):
        path = icon_path()
        return QIcon(path) if path else QgsProcessingProvider.icon(self)
