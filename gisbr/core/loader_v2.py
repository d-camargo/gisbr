# -*- coding: utf-8 -*-
"""Leitura de (Geo)Parquet do backend v2, com cadeia de backends.

Ordem (mantem o "maximo QGIS" possivel):
  1. Driver GDAL Parquet/Arrow  -> QgsVectorLayer(path, name, "ogr")  [nativo]
  2. pacote python `pyarrow`     -> le WKB e monta camada em memoria  [fallback]
  3. nenhum                      -> erro com orientacao de instalacao

GeoParquet guarda a geometria como WKB numa coluna binaria; o nome da coluna
primaria e o CRS vem do metadado "geo" (JSON) do schema. Arquivos do censobr
nao tem geometria (tabela pura) — tratados como camada NoGeometry.
"""

import json

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsVectorLayer,
    QgsWkbTypes,
)

from . import capabilities, qgis_compat
from .constants import EPSG_GEOBR


class LoaderV2Error(Exception):
    pass


# ----------------------------------------------------------------- backend GDAL
def _load_with_gdal(path, name):
    layer = QgsVectorLayer(str(path), name, "ogr")
    if not layer.isValid():
        raise LoaderV2Error(f"GDAL nao abriu o parquet: {path}")
    return layer


# --------------------------------------------------------------- backend pyarrow
def _arrow_type_to_qvariant(field_type):
    import pyarrow as pa

    if pa.types.is_boolean(field_type):
        return qgis_compat.field_type("bool")
    if pa.types.is_integer(field_type):
        return qgis_compat.field_type("int")
    if pa.types.is_floating(field_type) or pa.types.is_decimal(field_type):
        return qgis_compat.field_type("double")
    # string, large_string, e qualquer outro -> texto
    return qgis_compat.field_type("string")


def _detect_geometry_column(schema):
    """Coluna de geometria via metadado GeoParquet 'geo'; senao por nome comum."""
    if schema.metadata and b"geo" in schema.metadata:
        try:
            geo = json.loads(schema.metadata[b"geo"].decode("utf-8"))
            col = geo.get("primary_column")
            crs_epsg = None
            cols = geo.get("columns", {})
            cinfo = cols.get(col, {}) if col else {}
            crs_field = cinfo.get("crs")
            # crs pode ser PROJJSON (dict) ou string; geobr e sempre 4674.
            if isinstance(crs_field, dict):
                cid = crs_field.get("id", {})
                code = cid.get("code")
                if code:
                    crs_epsg = int(code)
            return col, crs_epsg
        except (ValueError, KeyError, TypeError):
            pass
    for candidate in ("geometry", "geom", "wkb_geometry", "_geometry"):
        if candidate in schema.names:
            return candidate, None
    return None, None


def _load_with_pyarrow(path, name, default_epsg=EPSG_GEOBR):
    import pyarrow.parquet as pq

    table = pq.read_table(str(path))
    schema = table.schema
    geom_col, crs_epsg = _detect_geometry_column(schema)
    if crs_epsg is None:
        crs_epsg = default_epsg

    attr_cols = [n for n in schema.names if n != geom_col]

    # monta os campos
    fields = QgsFields()
    for n in attr_cols:
        ftype = schema.field(n).type
        fields.append(QgsField(n, _arrow_type_to_qvariant(ftype)))

    data = table.to_pydict()
    n_rows = table.num_rows

    # tipo de geometria: detecta no primeiro WKB nao-nulo
    wkb_type = QgsWkbTypes.Type.NoGeometry
    if geom_col:
        for i in range(n_rows):
            raw = data[geom_col][i]
            if raw:
                g = QgsGeometry()
                g.fromWkb(bytes(raw))
                wkb_type = g.wkbType()
                break

    geom_token = (
        QgsWkbTypes.displayString(wkb_type)
        if wkb_type != QgsWkbTypes.Type.NoGeometry
        else "None"
    )
    uri = f"{geom_token}?crs=EPSG:{crs_epsg}"
    layer = QgsVectorLayer(uri, name, "memory")
    if not layer.isValid():
        raise LoaderV2Error(f"Falha ao criar camada em memoria (uri={uri}).")

    prov = layer.dataProvider()
    prov.addAttributes(fields.toList())
    layer.updateFields()

    feats = []
    for i in range(n_rows):
        f = QgsFeature(layer.fields())
        if geom_col:
            raw = data[geom_col][i]
            if raw:
                g = QgsGeometry()
                g.fromWkb(bytes(raw))
                f.setGeometry(g)
        f.setAttributes([data[c][i] for c in attr_cols])
        feats.append(f)
    prov.addFeatures(feats)
    layer.updateExtents()
    return layer


# ------------------------------------------------------------------- API publica
def read_parquet_layer(path, name):
    """Le um .parquet (com ou sem geometria) como QgsVectorLayer.

    Escolhe o backend disponivel (GDAL nativo > pyarrow). Levanta
    LoaderV2Error com orientacao se nenhum estiver presente.
    """
    backend = capabilities.parquet_backend()
    if backend == "gdal":
        return _load_with_gdal(path, name)
    if backend == "pyarrow":
        return _load_with_pyarrow(path, name)
    raise LoaderV2Error(capabilities.install_hint())
