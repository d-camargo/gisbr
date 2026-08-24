# -*- coding: utf-8 -*-
"""Conector de arquivo local do diagnostico (protocolo "arquivo").

Para bases oficiais que so existem por download manual autenticado
(ex.: parcelas certificadas do SIGEF/INCRA, atras de login gov.br).
O motor resolve o arquivo mais recente que casar com os globs da fonte
dentro da pasta de downloads manuais e abre como camada vetorial:
.zip via /vsizip/ (o GDAL acha o .shp dentro), .shp/.gpkg soltos direto.

resolve_arquivo e puro pathlib/fnmatch — roda sem QGIS (testavel no pytest);
os imports do QGIS ficam em fetch_layer.
"""
import fnmatch
from datetime import datetime
from pathlib import Path


def resolve_arquivo(pasta, globs):
    """Arquivo mais recente em `pasta` que casar com algum glob de `globs`.

    Casamento por nome de arquivo, insensivel a maiusculas/minusculas
    (o nome entregue pelo portal oficial varia). Devolve Path do mais
    recente (maior st_mtime) ou None se nada casar / pasta inexistente.
    Nao levanta excecao.
    """
    if not pasta or not globs:
        return None
    base = Path(pasta)
    try:
        entradas = [e for e in base.iterdir() if e.is_file()]
    except OSError:
        return None
    padroes = [g.lower() for g in globs]
    candidatos = [
        e for e in entradas
        if any(fnmatch.fnmatch(e.name.lower(), p) for p in padroes)
    ]
    if not candidatos:
        return None
    return max(candidatos, key=lambda e: e.stat().st_mtime)


def _stamp(layer, fonte):
    layer.setCustomProperty("data_extracao", datetime.now().strftime("%Y-%m-%d"))
    layer.setCustomProperty("fonte", fonte)
    return layer


def _invalid(layer_name, msg):
    from qgis.core import QgsVectorLayer
    layer = QgsVectorLayer("", layer_name, "ogr")
    layer.error_msg = msg
    return layer


def fetch_layer(caminho, layer_name, srs=None, feedback=None):
    """Abre um vetor local (Path|str). .zip entra via /vsizip/ e o GDAL
    varre o zip ate achar a camada vetorial. Em falha devolve camada
    invalida com .error_msg = caminho + causa reportada pelo GDAL
    (nunca "falha generica"). NAO levanta excecao.
    """
    from qgis.core import QgsVectorLayer

    caminho = str(caminho)
    fonte = caminho
    if caminho.lower().endswith(".zip"):
        fonte = "/vsizip/" + caminho
    layer = QgsVectorLayer(fonte, layer_name, "ogr")
    if not layer.isValid():
        causa = layer.error().message() or "GDAL nao abriu o arquivo"
        return _invalid(layer_name, "{}: {}".format(caminho, causa))
    return _stamp(layer, "Arquivo local ({})".format(caminho))
