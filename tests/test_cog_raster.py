# -*- coding: utf-8 -*-
"""Testes unitários para o conector de rasters COG (gisbr.core.connectors.cog_raster).
"""
import os
import pytest
from osgeo import gdal, osr

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsPalettedRasterRenderer,
    QgsPointXY,
    QgsVectorLayer,
)

from gisbr.core.connectors import cog_raster
from gisbr.core.connectors.cog_raster import (
    Language,
    fetch_layer,
    fetch_raster,
)


def _criar_geotiff_local(caminho, width=10, height=10, epsg=4326):
    """Cria um GeoTIFF local minúsculo para testes offline."""
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(caminho), width, height, 1, gdal.GDT_Byte)

    # Transformação geográfica: bbox em torno de (-44.1, -19.9)
    ds.SetGeoTransform([-44.15, 0.01, 0, -19.85, 0, -0.01])

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    ds.SetProjection(srs.ExportToWkt())

    band = ds.GetRasterBand(1)
    band.SetNoDataValue(0)

    # Matriz 10x10 com pixels de classes MapBiomas (15=Pastagem, 24=Urbano, 3=Formação Florestal)
    linha = [15, 24, 3, 15, 24, 3, 15, 24, 3, 15]
    dados = bytes(linha * height)
    band.WriteRaster(0, 0, width, height, dados)
    band.FlushCache()
    ds = None


def _criar_mascara_vetorial(epsg=4674):
    """Cria uma camada vetorial com um polígono cobrindo o centro do raster de teste."""
    layer = QgsVectorLayer(f"Polygon?crs=EPSG:{epsg}", "mascara_teste", "memory")
    provider = layer.dataProvider()

    polygon = QgsGeometry.fromPolygonXY([[
        QgsPointXY(-44.14, -19.86),
        QgsPointXY(-44.06, -19.86),
        QgsPointXY(-44.06, -19.94),
        QgsPointXY(-44.14, -19.94),
        QgsPointXY(-44.14, -19.86),
    ]])

    feat = QgsFeature()
    feat.setGeometry(polygon)
    provider.addFeatures([feat])
    layer.updateExtents()
    return layer


def test_cog_raster_enums():
    assert Language.PT.value == "pt"
    assert Language.EN.value == "en"


def test_cog_raster_url_vazia(qgis_app, tmp_path):
    mask = _criar_mascara_vetorial()
    out = tmp_path / "out.tif"
    res = fetch_raster("", mask, str(out))
    assert not res.isValid()
    assert hasattr(res, "error_msg")
    assert "URL inválida" in res.error_msg


def test_cog_raster_mascara_invalida(qgis_app, tmp_path):
    out = tmp_path / "out.tif"
    res = fetch_raster("https://example.com/test.tif", None, str(out))
    assert not res.isValid()
    assert hasattr(res, "error_msg")
    assert "máscara" in res.error_msg


def test_cog_raster_url_inexistente(qgis_app, tmp_path):
    mask = _criar_mascara_vetorial()
    out = tmp_path / "out.tif"
    res = fetch_raster("/caminho/inexistente/raster.tif", mask, str(out))
    assert not res.isValid()
    assert hasattr(res, "error_msg")
    assert "/caminho/inexistente/raster.tif" in res.error_msg


def test_cog_raster_recorte_local_sem_rede(qgis_app, tmp_path):
    """Testa recorte offline de um GeoTIFF local minúsculo, provando recorte, gravação e paleta."""
    input_tif = tmp_path / "input_test.tif"
    output_tif = tmp_path / "output_clipped.tif"

    _criar_geotiff_local(input_tif, width=10, height=10, epsg=4326)

    # Máscara em EPSG:4674 (força a reprojeção D10 de 4674 para 4326)
    mask = _criar_mascara_vetorial(epsg=4674)

    layer = fetch_raster(
        url=str(input_tif),
        mask_layer=mask,
        output_path=str(output_tif),
        layer_name="UsoSoloMapBiomas",
        lang="pt",
    )

    assert layer.isValid()
    assert layer.name() == "UsoSoloMapBiomas"
    assert os.path.exists(output_tif)
    assert os.path.getsize(output_tif) > 0

    # Verifica se o renderizador paletado do MapBiomas foi aplicado
    renderer = layer.renderer()
    assert isinstance(renderer, QgsPalettedRasterRenderer)
    assert len(renderer.classes()) > 0

    # Proprietas customizadas
    assert layer.customProperty("fonte").startswith("COG remoto")


def test_cog_raster_alias_fetch_layer(qgis_app, tmp_path):
    input_tif = tmp_path / "input_test.tif"
    output_tif = tmp_path / "output_alias.tif"

    _criar_geotiff_local(input_tif, width=10, height=10, epsg=4326)
    mask = _criar_mascara_vetorial(epsg=4674)

    layer = fetch_layer(
        url=str(input_tif),
        mask_layer=mask,
        output_path=str(output_tif),
        layer_name="MapBiomasAlias",
    )

    assert layer.isValid()
    assert layer.name() == "MapBiomasAlias"


def test_cog_raster_reprojecao_mascara_epsg3857(qgis_app, tmp_path):
    """Testa reprojeção da máscara (D10) quando o raster está em EPSG:3857 (métrico)."""
    input_tif = tmp_path / "input_3857.tif"
    output_tif = tmp_path / "output_3857.tif"

    # Criar raster em 3857 com coordenadas em metros
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(input_tif), 20, 20, 1, gdal.GDT_Byte)
    # Origin: X=-4920000, Y=-2250000, pixel size 50m x -50m (cobre até -4910000, -2260000)
    ds.SetGeoTransform([-4920000, 50, 0, -2250000, 0, -50])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3857)
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.SetNoDataValue(0)
    band.WriteRaster(0, 0, 20, 20, bytes([15, 24, 3, 30] * 100))
    band.FlushCache()
    ds = None

    # Máscara em EPSG:4674 (graus decimais em BH/Contagem)
    mask = _criar_mascara_vetorial(epsg=4674)

    layer = fetch_raster(
        url=str(input_tif),
        mask_layer=mask,
        output_path=str(output_tif),
        layer_name="MapBiomas3857",
    )

    assert layer.isValid()
    assert layer.crs().authid() == "EPSG:3857"
