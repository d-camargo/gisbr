# -*- coding: utf-8 -*-
"""Conector de basemap: imagem de satelite de fundo (XYZ Esri World Imagery).

Ver docs/diagnostico-plano-diretor/referencia-satelite-hacarthon.md.
"""
from qgis.core import QgsRasterLayer

# {z}/{y}/{x} URL-encodado para o provider "wms"/xyz do QGIS.
ESRI_WORLD_IMAGERY = (
    "type=xyz&zmax=19&zmin=0&url="
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D"
)


def satellite_layer(name="Esri World Imagery"):
    """QgsRasterLayer de satelite (XYZ). Conferir .isValid() antes de adicionar."""
    layer = QgsRasterLayer(ESRI_WORLD_IMAGERY, name, "wms")
    if layer.isValid():
        layer.setCustomProperty(
            "fonte", "Esri, Maxar, Earthstar Geographics (World Imagery)")
    return layer
