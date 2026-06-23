# -*- coding: utf-8 -*-
"""geobr-qgis — acesso aos dados espaciais oficiais do Brasil (geobr/IPEA)
dentro do QGIS, usando apenas PyQGIS + stdlib (sem dependencias externas).
"""


def classFactory(iface):  # pylint: disable=invalid-name
    from .geobr_qgis_plugin import GeobrPlugin
    return GeobrPlugin(iface)
