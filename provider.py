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
        return "geobr"

    def name(self):
        return "geobr (IPEA)"

    def longName(self):
        return "geobr — dados espaciais oficiais do Brasil (IPEA)"

    def icon(self):
        here = os.path.dirname(__file__)
        for name in ("icon.svg", "icon.png"):  # SVG nitido em qualquer DPI
            path = os.path.join(here, name)
            if os.path.exists(path):
                return QIcon(path)
        return QgsProcessingProvider.icon(self)
