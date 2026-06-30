# -*- coding: utf-8 -*-
"""Motor do diagnostico (ARQUITETURA.md §3.3/§3.5).

carregar_fontes(): para cada fonte WFS selecionada, busca filtrada por municipio,
grava no GeoPackage (1 camada/fonte, nome inclui o code do municipio) e adiciona
ao projeto. Pula fontes ja existentes no GeoPackage (a nao ser force=True).
"""
import os

from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

from .connectors import wfs, basemap
from .sources import SOURCES

_UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}


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
    """Nomes de camadas ja presentes no GeoPackage (set). Vazio se nao existe."""
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
    """Grava 1 camada no GeoPackage. Cria o arquivo se nao existir; senao
    adiciona/sobrescreve so essa camada (preserva as demais)."""
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
        if proto != "wfs":
            res["pulou"].append((s["id"], "conector {} ainda nao implementado".format(proto)))
            continue

        layer_name = "{}_{}".format(s["id"], code_muni)
        if (not force) and layer_name in existentes:
            res["pulou"].append((s["id"], "ja existe no GeoPackage ({})".format(layer_name)))
            continue

        type_name = s["type_name"].replace("{uf}", uf)
        cql, usa_bbox = _filtro_para(s, code_muni, nome_muni)
        layer = wfs.fetch_layer(
            s["endpoint"], type_name, layer_name, srs=s.get("srs", "EPSG:4674"),
            cql_filter=cql, bbox=(bbox if usa_bbox else None),
        )
        if not layer.isValid():
            res["falhou"].append((s["id"], getattr(layer, "error_msg", "camada invalida")))
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
