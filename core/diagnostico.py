# -*- coding: utf-8 -*-
"""Motor do diagnostico (ARQUITETURA.md §3.3/§3.5).

carregar_fontes(): para cada fonte WFS selecionada, busca filtrada por
municipio, grava no GeoPackage (1 camada/fonte) e adiciona ao projeto.
Opcional: basemap. NAO resolve nome/bbox do municipio (isso e do painel/caller,
T-011); recebe code_muni, nome_muni e bbox explicitos.
"""
from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

from .connectors import wfs, basemap
from .sources import SOURCES

# Prefixo de 2 digitos do code_muni -> sigla da UF.
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
    """Retorna (cql_filter, usa_bbox)."""
    f = s.get("filtro") or {"tipo": "bbox"}
    t = f.get("tipo")
    if t == "cql_codigo":
        return "{} = {}".format(f["campo"], int(code_muni)), False
    if t == "cql_nome":
        nome = (nome_muni or "").replace("'", "''")
        return "{} = '{}'".format(f["campo"], nome), False
    return None, True


def _grava_gpkg(layer, gpkg_path, layer_name, primeiro):
    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = layer_name
    opts.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteFile if primeiro
        else QgsVectorFileWriter.CreateOrOverwriteLayer
    )
    ctx = QgsProject.instance().transformContext()
    res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, gpkg_path, ctx, opts)
    return res[0] == QgsVectorFileWriter.NoError, res[1]


def carregar_fontes(source_ids, code_muni, nome_muni, bbox, gpkg_path,
                    add_basemap=False, feedback=None):
    def log(m):
        if feedback is not None:
            feedback.pushInfo(m)

    uf = _UF_POR_CODIGO.get(str(code_muni)[:2], "").lower()
    res = {"ok": [], "falhou": [], "pulou": []}
    primeiro = True

    for s in _por_id(source_ids):
        proto = s.get("protocolo")
        if proto == "basemap":
            continue
        if proto != "wfs":
            res["pulou"].append((s["id"], "conector {} ainda nao implementado".format(proto)))
            continue

        type_name = s["type_name"].replace("{uf}", uf)
        cql, usa_bbox = _filtro_para(s, code_muni, nome_muni)
        layer = wfs.fetch_layer(
            s["endpoint"], type_name, s["id"], srs=s.get("srs", "EPSG:4674"),
            cql_filter=cql, bbox=(bbox if usa_bbox else None),
        )
        if not layer.isValid():
            res["falhou"].append((s["id"], getattr(layer, "error_msg", "camada invalida")))
            continue

        ok, msg = _grava_gpkg(layer, gpkg_path, s["id"], primeiro)
        if not ok:
            res["falhou"].append((s["id"], "gravar GeoPackage: {}".format(msg)))
            continue
        primeiro = False

        gl = QgsVectorLayer("{}|layername={}".format(gpkg_path, s["id"]), s["id"], "ogr")
        if gl.isValid():
            QgsProject.instance().addMapLayer(gl)
            res["ok"].append(s["id"])
            log("OK: {}".format(s["id"]))
        else:
            res["falhou"].append((s["id"], "camada do GeoPackage invalida"))

    if add_basemap:
        bl = basemap.satellite_layer()
        if bl.isValid():
            QgsProject.instance().addMapLayer(bl)
            log("basemap de satelite adicionado")

    return res
