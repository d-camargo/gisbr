# -*- coding: utf-8 -*-
"""GeobrProvider: registra os algoritmos read_* na Caixa de Ferramentas."""

import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithms import ALGORITHMS


class GeobrProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        for alg_class in ALGORITHMS:
            self.addAlgorithm(alg_class())

    def id(self):
        return "gisbr"

    def name(self):
        return "GisBR"

    def longName(self):
        return "GisBR — dados espaciais oficiais do Brasil (IBGE/IPEA)"

    def icon(self):
        here = os.path.dirname(__file__)
        for name in ("icon.svg", "icon.png"):  # SVG nitido em qualquer DPI
            path = os.path.join(here, name)
            if os.path.exists(path):
                return QIcon(path)
        return QgsProcessingProvider.icon(self)
