# -*- coding: utf-8 -*-
"""Motor do diagnostico. Protocolos: wfs, arcgis, geobr (code|bbox).

Fontes filtradas por bbox sao recortadas pelo POLIGONO do municipio (native:clip)
para nao trazer feicoes de municipios vizinhos. Camadas sem feicoes sao puladas
com aviso no Log.
"""
import os

from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

from .connectors import wfs, basemap, arcgis_rest, osm
from .sources import SOURCES
from . import osm_pipeline

_UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

_PROTOCOLOS = ("wfs", "arcgis", "geobr", "osm")


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


def _usou_bbox(s, usa_bbox):
    if s.get("protocolo") == "geobr":
        return s.get("recorte", "code") == "bbox"
    return usa_bbox


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


def _municipio_poligono(code_muni):
    """Poligono do municipio (read_municipality) p/ recorte. None se falhar."""
    import processing
    try:
        out = processing.run("gisbr:read_municipality", {
            "CODE": str(code_muni), "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]
    except Exception:
        return None
    out = _resolve_out(out, "municipio")
    return out if (out is not None and out.isValid()) else None


def _recorta_poligono(layer, poligono, layer_name):
    import processing
    try:
        out = processing.run("native:clip", {
            "INPUT": layer, "OVERLAY": poligono, "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]
        return _resolve_out(out, layer_name)
    except Exception as exc:
        return _invalida(layer_name, "recorte por poligono: {}".format(exc))


def _carrega_geobr(s, code_muni, layer_name):
    """recorte 'code' filtra por code_muni; 'bbox' baixa nacional (sera recortado
    pelo poligono no carregar_fontes)."""
    import processing
    if s.get("requer_parquet"):
        from . import capabilities
        if capabilities.parquet_backend() is None:
            return _invalida(layer_name, "requer driver Parquet ou pyarrow (fonte v2)")
    algo = s["algo"]
    code_param = str(code_muni) if s.get("recorte", "code") == "code" else "all"
    try:
        out = processing.run("gisbr:{}".format(algo), {
            "CODE": code_param, "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]
    except Exception as exc:
        return _invalida(layer_name, "geobr {}: {}".format(algo, exc))
    return _resolve_out(out, layer_name)


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
        return _carrega_geobr(s, code_muni, layer_name)
    if proto == "osm":
        # O protocolo osm nao retorna camada ainda; apenas executa a pipeline e a marca como pendente.
        res = osm_pipeline.build_osm_municipal_network(code_muni, s.get("nome_muni", ""), 
                                                        s.get("gpkg_path", ""), 
                                                        force=False, feedback=None)
        # Deixar a pipeline armazenar o raw_cache e metadados; nao montar camada agora.
        return _invalida(layer_name, "pipeline OSM: persistencia em camadas ainda nao implementada")
    return None


def carregar_fontes(source_ids, code_muni, nome_muni, bbox, gpkg_path,
                    add_basemap=False, force=False, feedback=None):
    def log(m):
        if feedback is not None:
            feedback.pushInfo(m)

    if gpkg_path and not gpkg_path.lower().endswith(".gpkg"):
        gpkg_path = gpkg_path + ".gpkg"

    uf = _UF_POR_CODIGO.get(str(code_muni)[:2], "").lower()
    res = {"ok": [], "falhou": [], "pulou": []}
    existentes = _layers_existentes(gpkg_path)
    poligono = None
    poligono_tentado = False

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

        # base nao retornou nada (ex.: aterro sem feicao no municipio)
        if layer.featureCount() == 0:
            res["pulou"].append((s["id"], "sem feicoes para este municipio (base nao retornou nada)"))
            continue

        # fontes filtradas por bbox -> recorta pelo POLIGONO do municipio
        if _usou_bbox(s, usa_bbox):
            if not poligono_tentado:
                poligono = _municipio_poligono(code_muni)
                poligono_tentado = True
            if poligono is None:
                res["falhou"].append((s["id"], "nao obtive o poligono do municipio p/ recorte"))
                continue
            layer = _recorta_poligono(layer, poligono, layer_name)
            if layer is None or not layer.isValid():
                res["falhou"].append((s["id"], getattr(layer, "error_msg", "falha no recorte")))
                continue
            if layer.featureCount() == 0:
                res["pulou"].append((s["id"], "sem feicoes dentro do municipio (apos recorte)"))
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
            proj = QgsProject.instance()
            proj.addMapLayer(bl, False)            # nao adiciona a arvore ainda
            proj.layerTreeRoot().addLayer(bl)      # anexa como ULTIMO filho = fundo
            log("basemap de satelite adicionado (ao fundo)")

    return res
