# -*- coding: utf-8 -*-
"""Leitura da legenda MapBiomas Coleção 9 e gerador de QgsPalettedRasterRenderer.

Permite ler as classes do CSV usando stdlib pura (sem QGIS) para testabilidade
e fornecer renderizador paletado com apenas as classes presentes no recorte.
"""

import csv
import os
import re

# Caminho padrão para o CSV de classes
_DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "data", "mapbiomas_col9_classes.csv"
)

# Regex para validação de cor hex (#RRGGBB)
_HEX_RE = re.compile(r"^#[A-Fa-f0-9]{6}$")


def carregar_classes_mapbiomas(csv_path=None):
    """Carrega o dicionário de classes do MapBiomas Coleção 9 a partir do CSV.

    Args:
        csv_path (str, optional): Caminho customizado para o CSV.

    Returns:
        dict[int, dict]: Dicionário mapeando codigo (int) -> {
            "codigo": int,
            "rotulo_pt": str,
            "rotulo_en": str,
            "cor_hex": str,
        }
    """
    path = csv_path or _DEFAULT_CSV_PATH
    classes = {}

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codigo = int(row["codigo"])
            cor_hex = row["cor_hex"].strip()
            classes[codigo] = {
                "codigo": codigo,
                "rotulo_pt": row["rotulo_pt"].strip(),
                "rotulo_en": row["rotulo_en"].strip(),
                "cor_hex": cor_hex,
            }

    return classes


def obter_classes_presentes(codigos_presentes, classes_dict=None, lang="pt"):
    """Filtra as classes do MapBiomas apenas para os códigos presentes no recorte.

    Args:
        codigos_presentes (iterable[int]): Códigos de pixel presentes no raster.
        classes_dict (dict, optional): Dicionário de classes (carregar_classes_mapbiomas).
        lang (str): Idioma do rótulo ('pt' ou 'en').

    Returns:
        list[dict]: Lista de dicionários ordenados por código, cada um contendo:
            {"codigo": int, "rotulo": str, "cor_hex": str}
    """
    if classes_dict is None:
        classes_dict = carregar_classes_mapbiomas()

    key_rotulo = "rotulo_en" if str(lang).lower() in ("en", "english") else "rotulo_pt"
    codigos_set = {int(c) for c in codigos_presentes}

    resultado = []
    for codigo in sorted(codigos_set):
        if codigo in classes_dict:
            item = classes_dict[codigo]
            resultado.append({
                "codigo": codigo,
                "rotulo": item[key_rotulo],
                "cor_hex": item["cor_hex"],
            })

    return resultado


def extrair_codigos_presentes_raster(layer_or_path, band=1):
    """Extrai o conjunto de códigos de pixel (int) presentes em um raster.

    Tenta via GDAL VSI/local se for caminho, ou via QgsRasterBlock se for QgsRasterLayer.

    Args:
        layer_or_path (str | QgsRasterLayer): Raster a analisar.
        band (int): Número da banda (default 1).

    Returns:
        set[int] | None: Conjunto de inteiros ou None se não for possível extrair.
    """
    path = str(layer_or_path) if not hasattr(layer_or_path, "dataProvider") else layer_or_path.source()
    if path and os.path.exists(path):
        try:
            from osgeo import gdal
            ds = gdal.Open(path)
            if ds:
                b = ds.GetRasterBand(band)
                if b:
                    raw = b.ReadRaster()
                    if raw:
                        return set(raw)
        except Exception:
            return None

    if hasattr(layer_or_path, "dataProvider"):
        provider = layer_or_path.dataProvider()
        extent = layer_or_path.extent()
        width = layer_or_path.width()
        height = layer_or_path.height()
        block = provider.block(band, extent, width, height)
        if block and not block.isEmpty():
            data = bytes(block.data())
            return set(data)

    return None


def criar_renderizador_paletado(layer_or_provider, codigos_presentes=None, band=1, lang="pt"):
    """Cria um QgsPalettedRasterRenderer para o raster usando as classes presentes.

    Args:
        layer_or_provider (QgsRasterLayer | QgsRasterDataProvider): Layer ou data provider.
        codigos_presentes (iterable[int], optional): Códigos de pixel presentes no recorte.
            Se None, tenta extrair do raster ou usa todas as classes catalogadas.
        band (int): Número da banda (default 1).
        lang (str): Idioma dos rótulos ('pt' ou 'en').

    Returns:
        QgsPalettedRasterRenderer: Renderizador paletado pronto para aplicar no layer.
    """
    from qgis.core import QgsPalettedRasterRenderer
    from qgis.PyQt.QtGui import QColor

    classes_dict = carregar_classes_mapbiomas()

    if codigos_presentes is None:
        codigos_presentes = extrair_codigos_presentes_raster(layer_or_provider, band=band)

    if codigos_presentes is None:
        codigos_presentes = classes_dict.keys()

    classes_filtradas = obter_classes_presentes(codigos_presentes, classes_dict=classes_dict, lang=lang)

    qgis_classes = [
        QgsPalettedRasterRenderer.Class(
            c["codigo"],
            QColor(c["cor_hex"]),
            c["rotulo"],
        )
        for c in classes_filtradas
    ]

    provider = layer_or_provider.dataProvider() if hasattr(layer_or_provider, "dataProvider") else layer_or_provider

    return QgsPalettedRasterRenderer(provider, band, qgis_classes)
