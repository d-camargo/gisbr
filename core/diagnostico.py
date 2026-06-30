# -*- coding: utf-8 -*-
"""Motor do diagnostico. Protocolos: wfs, arcgis, geobr (code|bbox)."""
import os

from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

from .connectors import wfs, basemap, arcgis_rest
from .sources import SOURCES

_UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

_PROTOCOLOS = ("wfs", "arcgis", "geobr")


def _por_id(ids):
    return [s for s in SOURCES if s["id"] in ids]


def _filtro_para(s, code_muni, nome_muni):
    f = s.get("filtro") or {"tipo": "bbox"}
    t = f.get("tipo")
    if t == "cql_codigo":
        return "{} = {}".format(f["campo"], int(code_muni)), False
    if t == "cql_nome":
        nome = (nome_muni or "").replace("'", "''")
        return "{} = '{}'".format(f["campo"], nome), False
    return None, True


def _layers_existentes(gpkg_path):
    if not os.path.exists(gpkg_path):
        return set()
    vl = QgsVectorLayer(gpkg_path, "probe", "ogr")
    if not vl.isValid():
        return set()
    nomes = set()
    for sub in vl.dataProvider().subLayers():
        parts = sub.split("!!::!!")
        if len(parts) > 1:
            nomes.add(parts[1])
    return nomes


def _grava_gpkg(layer, gpkg_path, layer_name):
    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = layer_name
    opts.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(gpkg_path)
        else QgsVectorFileWriter.CreateOrOverwriteFile
    )
    ctx = QgsProject.instance().transformContext()
    res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, gpkg_path, ctx, opts)
    return res[0] == QgsVectorFileWriter.NoError, res[1]


def _resolve_out(out, layer_name):
    if isinstance(out, str):
        return QgsProject.instance().mapLayer(out) or QgsVectorLayer(out, layer_name, "ogr")
    return out


def _invalida(layer_name, msg):
    inv = QgsVectorLayer("", layer_name, "ogr")
    inv.error_msg = msg
    return inv


def _carrega_geobr(s, code_muni, bbox, layer_name):
    """Roda o algoritmo geobr (Fase 1/2). recorte 'code' filtra por code_muni;
    recorte 'bbox' baixa e recorta pela bbox do municipio."""
    import processing
    if s.get("requer_parquet"):
        from . import capabilities
        if capabilities.parquet_backend() is None:
            return _invalida(layer_name, "requer driver Parquet ou pyarrow (fonte v2)")

    algo = s["algo"]
    recorte = s.get("recorte", "code")
    code_param = str(code_muni) if recorte == "code" else "all"
    try:
        out = processing.run("gisbr:{}".format(algo), {
            "CODE": code_param, "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]
    except Exception as exc:
        return _invalida(layer_name, "geobr {}: {}".format(algo, exc))
    out = _resolve_out(out, layer_name)

    if recorte == "bbox":
        if bbox is None:
            return _invalida(layer_name, "bbox do municipio necessario para esta fonte")
        if out is None or not out.isValid():
            return _invalida(layer_name, "geobr {} nao retornou camada".format(algo))
        try:
            extent = "{},{},{},{} [EPSG:4674]".format(bbox[0], bbox[2], bbox[1], bbox[3])
            clip = processing.run("native:extractbyextent", {
                "INPUT": out, "EXTENT": extent, "CLIP": True,
                "OUTPUT": "TEMPORARY_OUTPUT",
            })["OUTPUT"]
            out = _resolve_out(clip, layer_name)
        except Exception as exc:
            return _invalida(layer_name, "recorte bbox: {}".format(exc))
    return out


def _busca_camada(s, layer_name, uf, cql, usa_bbox, bbox, code_muni):
    proto = s.get("protocolo")
    srs = s.get("srs", "EPSG:4674")
    if proto == "wfs":
        type_name = s["type_name"].replace("{uf}", uf)
        return wfs.fetch_layer(s["endpoint"], type_name, layer_name, srs=srs,
                               cql_filter=cql, bbox=(bbox if usa_bbox else None))
    if proto == "arcgis":
        return arcgis_rest.fetch_layer(s["endpoint"], s["layer_id"], layer_name,
                                       srs=srs, where=cql,
                                       bbox=(bbox if usa_bbox else None))
    if proto == "geobr":
        return _carrega_geobr(s, code_muni, bbox, layer_name)
    return None


def carregar_fontes(source_ids, code_muni, nome_muni, bbox, gpkg_path,
                    add_basemap=False, force=False, feedback=None):
    def log(m):
        if feedback is not None:
            feedback.pushInfo(m)

    uf = _UF_POR_CODIGO.get(str(code_muni)[:2], "").lower()
    res = {"ok": [], "falhou": [], "pulou": []}
    existentes = _layers_existentes(gpkg_path)

    for s in _por_id(source_ids):
        proto = s.get("protocolo")
        if proto == "basemap":
            continue
        if proto not in _PROTOCOLOS:
            res["pulou"].append((s["id"], "conector {} ainda nao implementado".format(proto)))
            continue

        layer_name = "{}_{}".format(s["id"], code_muni)
        if (not force) and layer_name in existentes:
            res["pulou"].append((s["id"], "ja existe no GeoPackage ({})".format(layer_name)))
            continue

        cql, usa_bbox = _filtro_para(s, code_muni, nome_muni)
        layer = _busca_camada(s, layer_name, uf, cql, usa_bbox, bbox, code_muni)
        if layer is None or not layer.isValid():
            msg = getattr(layer, "error_msg", "camada invalida") if layer else "protocolo desconhecido"
            res["falhou"].append((s["id"], msg))
            continue

        ok, msg = _grava_gpkg(layer, gpkg_path, layer_name)
        if not ok:
            res["falhou"].append((s["id"], "gravar GeoPackage: {}".format(msg)))
            continue
        existentes.add(layer_name)

        nome_proj = "{} - {}".format(s.get("nome", s["id"]), nome_muni or code_muni)
        gl = QgsVectorLayer("{}|layername={}".format(gpkg_path, layer_name), nome_proj, "ogr")
        if gl.isValid():
            QgsProject.instance().addMapLayer(gl)
            res["ok"].append(s["id"])
            log("OK: {}".format(layer_name))
        else:
            res["falhou"].append((s["id"], "camada do GeoPackage invalida"))

    if add_basemap:
        bl = basemap.satellite_layer()
        if bl.isValid():
            QgsProject.instance().addMapLayer(bl)
            log("basemap de satelite adicionado")

    return res
