# -*- coding: utf-8 -*-
"""Conector de arquivo ZIP oficial remoto (protocolo "zip_remoto").

Conector generico para bases espaciais disponibilizadas em arquivos .zip
remotos contendo shapefiles ou outros formatos suportados pelo GDAL.

Fluxo:
1. Resolucao do file_id (cache_id ou ultimo segmento da URL). Se refresh=True
   e o arquivo de cache existir, renomeia para <file_id>.old para forcar novo
   download; se o download falhar, restaura o .old com pushWarning; se tiver
   sucesso, apaga o .old.
2. Abre o .zip via driver OGR usando o prefixo /vsizip/.
3. Se a camada nao possuir CRS valido (ex.: .prj ausente ou corrompido),
   forca o CRS da chave `srs` (default EPSG:4674) e registra aviso no log.
4. Se a chave `subset` for informada, aplica setSubsetString(subset) e
   VALIDA o retorno booleano. Se setSubsetString retornar False, a camada
   e invalidada explicitamente com .error_msg.
5. Se layer.crs() for valido e diferente de `srs`, reprojeta para `srs`
   via `native:reprojectlayer` ("memory:"), mantendo `layer_name`.
6. Em qualquer falha (download, abertura GDAL, subset invalido, reprojecao),
   retorna camada invalida com .error_msg contendo a URL e a causa da falha.
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


def fetch_layer(url, layer_name, srs="EPSG:4674", subset=None, feedback=None, cache_id=None, refresh=False):
    """Baixa um arquivo .zip remoto para o cache e abre como QgsVectorLayer.

    Args:
        url (str): URL do arquivo .zip remoto.
        layer_name (str): Nome de exibicao da camada no QGIS.
        srs (str): Codigo SRS (ex.: "EPSG:4674") para fallback se o .prj
            estiver ausente e para reprojecao de saida. Default "EPSG:4674".
        subset (str, optional): Expressao de filtro SQL/OGR para setSubsetString.
        feedback (QgsProcessingFeedback, optional): Objeto de feedback para logs.
        cache_id (str, optional): Identificador opcional do arquivo no cache.
            Se omitido, usa o ultimo segmento da URL.
        refresh (bool, optional): Se True, forca novo download preservando o cache
            anterior como fallback em caso de falha. Default False.

    Returns:
        QgsVectorLayer: Camada vetorial carregada (valida ou invalida com .error_msg).
    """
    if not url:
        return _invalid(layer_name, "URL invalida ou nao informada")

    file_id = cache_id or url.rstrip("/").split("/")[-1]

    cache_file = downloader.cache_dir() / file_id
    old_file = downloader.cache_dir() / "{}.old".format(file_id)

    renamed_old = False
    if refresh and cache_file.exists():
        cache_file.replace(old_file)
        renamed_old = True

    # 1. Download para cache via downloader._fetch_to_cache
    try:
        caminho_local = downloader._fetch_to_cache(file_id, [url], feedback=feedback)
        if renamed_old and old_file.exists():
            old_file.unlink()
    except Exception as exc:
        if renamed_old and old_file.exists():
            old_file.replace(cache_file)
            caminho_local = cache_file
            mtime = cache_file.stat().st_mtime
            dt_mtime = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            msg_aviso = "download falhou; mantida a base em cache de {}".format(dt_mtime)
            if feedback is not None:
                feedback.pushWarning(msg_aviso)
        else:
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

    # 5. Reprojecao para srs caso o CRS da camada seja valido e diferente
    if srs and layer.crs().isValid() and layer.crs().authid() != srs:
        import processing
        try:
            res = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": layer,
                    "TARGET_CRS": QgsCoordinateReferenceSystem(srs),
                    "OUTPUT": "memory:",
                },
            )
            out = res.get("OUTPUT")
            if out is None or not out.isValid():
                return _invalid(
                    layer_name,
                    "{}: falha ao reprojetar camada para {}".format(url, srs),
                )
            out.setName(layer_name)
            layer = out
        except Exception as exc:
            return _invalid(
                layer_name,
                "{}: falha na reprojecao ({})".format(url, exc),
            )

    return _stamp(layer, "Zip remoto ({})".format(url))
