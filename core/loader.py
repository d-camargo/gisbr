# -*- coding: utf-8 -*-
"""Carrega arquivos .gpkg como QgsVectorLayer, junta varios e filtra por codigo.

Filtro fino pos-load via setSubsetString (igual ao geobr, que filtra o
GeoDataFrame por code_muni/code_state etc.).
"""

from qgis.core import QgsVectorLayer

from .constants import normalize_uf


class LoaderError(Exception):
    pass


def load_layer(path, name):
    """Abre um .gpkg com o driver OGR. Levanta se invalido."""
    layer = QgsVectorLayer(str(path), name, "ogr")
    if not layer.isValid():
        raise LoaderError(f"Camada invalida: {path}")
    return layer


def merge_layers(layers, context, feedback):
    """Concatena varias camadas em uma (native:mergevectorlayers).

    Se houver so uma, devolve ela direto.
    """
    if len(layers) == 1:
        return layers[0]
    import processing  # lazy: plugin 'processing' so existe em runtime do QGIS
    result = processing.run(
        "native:mergevectorlayers",
        {"LAYERS": layers, "CRS": layers[0].crs(), "OUTPUT": "memory:merged"},
        context=context,
        feedback=feedback,
    )
    return result["OUTPUT"]


def _eq_expr(layer, column, digits):
    """Monta '"col" = valor' com aspas conforme o tipo da coluna (texto/numero)."""
    field = layer.fields().field(column)
    if field.isNumeric():
        return f'"{column}" = {int(digits)}'
    return f"\"{column}\" = '{digits}'"


def apply_code_filter(layer, code, code_column, abbrev_column=None,
                      uf_sliced=False):
    """Aplica setSubsetString para filtrar por codigo/sigla.

    Espelha o filtro pos-load do geobr (filtragem do GeoDataFrame).

    Distingue dois casos:

    * ``uf_sliced=True`` (municipality, census_tract, weighting_area...): o
      metadado ja foi recortado por UF, entao um codigo de 2 digitos/sigla nao
      exige mais nada; so um codigo completo (ex.: 7 digitos de municipio)
      dispara filtro em ``code_column``.
    * ``uf_sliced=False`` (state, region, meso...): arquivo nacional unico; a
      sigla filtra ``abbrev_column`` e o codigo numerico filtra ``code_column``.

    Se a coluna nao existir na camada, ignora (fallback seguro).
    """
    if not code or str(code).strip().lower() == "all":
        return layer

    s = str(code).strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    is_alpha = not digits and s.isalpha()
    field_names = [f.name() for f in layer.fields()]

    expr = None
    if uf_sliced:
        # recorte por UF ja feito no catalogo; so codigo completo filtra.
        # Um codigo de 7 digitos e um MUNICIPIO -> filtra code_muni (ex.: pegar
        # os setores/areas de ponderacao de BH). Codigo proprio (15 digitos do
        # setor, etc.) -> filtra a coluna especifica da geografia.
        if len(digits) > 2:
            col = (
                "code_muni"
                if len(digits) == 7 and "code_muni" in field_names
                else code_column
            )
            if col in field_names:
                expr = _eq_expr(layer, col, digits)
    else:
        if is_alpha and abbrev_column and abbrev_column in field_names:
            expr = f"\"{abbrev_column}\" = '{s.upper()}'"
        elif digits and code_column in field_names:
            expr = _eq_expr(layer, code_column, digits)

    if expr is None:
        return layer

    if not layer.setSubsetString(expr):
        raise LoaderError(
            f"Falha ao filtrar com expressao: {expr} "
            f"(colunas: {', '.join(field_names)})"
        )
    return layer
