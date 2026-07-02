# -*- coding: utf-8 -*-
"""geobr-qgis — acesso aos dados espaciais oficiais do Brasil (geobr/IPEA)
dentro do QGIS, usando apenas PyQGIS + stdlib (sem dependencias externas).
"""


def classFactory(iface):  # pylint: disable=invalid-name
    import os
    from qgis.PyQt.QtCore import QCoreApplication, QTranslator, QSettings
    locale = (QSettings().value("locale/userLocale") or "en")[:2]
    qm = os.path.join(os.path.dirname(__file__), "i18n", f"gisbr_{locale}.qm")
    if os.path.exists(qm):
        translator = QTranslator()
        if translator.load(qm):
            QCoreApplication.installTranslator(translator)
            classFactory._translator = translator  # manter viva a ref
    from .geobr_qgis_plugin import GeobrPlugin
    return GeobrPlugin(iface)
