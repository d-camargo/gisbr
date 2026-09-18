# -*- coding: utf-8 -*-
"""Conector de arquivo ZIP oficial remoto (protocolo "zip_remoto").

Conector generico para bases espaciais disponibilizadas em arquivos .zip
remotos contendo shapefiles ou outros formatos suportados pelo GDAL.

Fluxo:
1. Baixa o arquivo para o cache local via downloader._fetch_to_cache
   (garantindo download unico por URL/file_id).
2. Abre o .zip via driver OGR usando o prefixo /vsizip/.
3. Se a camada nao possuir CRS valido (ex.: .prj ausente ou corrompido),
   forca o CRS da chave `srs` (default EPSG:4674) e registra aviso no log.
4. Se a chave `subset` for informada, aplica setSubsetString(subset) e
   VALIDA o retorno booleano. Se setSubsetString retornar False, a camada
   e invalidada explicitamente com .error_msg.
5. Em qualquer falha (download, abertura GDAL, subset invalido), retorna
   camada invalida com .error_msg contendo a URL e a causa da falha.
"""
from datetime import datetime

from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer

from .. import downloader


def _stamp(layer, fonte):
    layer.setCustomProperty("data_extracao", datetime.now().strftime("%Y-%m-%d"))
    layer.setCustomProperty("fonte", fonte)
    return layer


def _invalid(layer_name, msg):
    layer = QgsVectorLayer("", layer_name, "ogr")
    layer.error_msg = msg
    return layer


def fetch_layer(url, layer_name, srs="EPSG:4674", subset=None, feedback=None):
    """Baixa um arquivo .zip remoto para o cache e abre como QgsVectorLayer.

    Args:
        url (str): URL do arquivo .zip remoto.
        layer_name (str): Nome de exibicao da camada no QGIS.
        srs (str): Codigo SRS (ex.: "EPSG:4674") para fallback se o .prj
            estiver ausente. Default "EPSG:4674".
        subset (str, optional): Expressao de filtro SQL/OGR para setSubsetString.
        feedback (QgsProcessingFeedback, optional): Objeto de feedback para logs.

    Returns:
        QgsVectorLayer: Camada vetorial carregada (valida ou invalida com .error_msg).
    """
    if not url:
        return _invalid(layer_name, "URL invalida ou nao informada")

    file_id = url.rstrip("/").split("/")[-1]

    # 1. Download para cache via downloader._fetch_to_cache
    try:
        caminho_local = downloader._fetch_to_cache(file_id, [url], feedback=feedback)
    except Exception as exc:
        return _invalid(layer_name, "{}: falha no download ({})".format(url, exc))

    # 2. Abertura via /vsizip/
    caminho_str = str(caminho_local)
    fonte_gdal = "/vsizip/" + caminho_str if not caminho_str.startswith("/vsizip/") else caminho_str
    layer = QgsVectorLayer(fonte_gdal, layer_name, "ogr")

    if not layer.isValid():
        causa = layer.error().message() or "GDAL nao abriu o arquivo zip"
        return _invalid(layer_name, "{}: {}".format(url, causa))

    # 3. Verificacao de CRS / .prj
    if not layer.crs().isValid():
        srs_code = srs or "EPSG:4674"
        crs = QgsCoordinateReferenceSystem(srs_code)
        if crs.isValid():
            layer.setCrs(crs)
            msg_log = "Aviso: Camada '{}' ({}) sem CRS (.prj ausente/invalido). Forcado SRS: {}".format(
                layer_name, url, srs_code
            )
            if feedback is not None:
                feedback.pushWarning(msg_log)

    # 4. Aplicacao de subset e verificacao rigorosa do retorno
    if subset:
        ok = layer.setSubsetString(subset)
        if not ok:
            return _invalid(
                layer_name,
                "{}: setSubsetString falhou para o filtro '{}'".format(url, subset)
            )

    return _stamp(layer, "Zip remoto ({})".format(url))
