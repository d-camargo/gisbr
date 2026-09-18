# -*- coding: utf-8 -*-
"""Conector para COG (Cloud-Optimized GeoTIFF) remoto com recorte vetorial.

Permite recortar rasters COG usando gdal:cliprasterbymasklayer, garantindo que
a máscara seja reprojetada para o mesmo CRS do raster de origem antes da
operação de corte (D10).
"""
from datetime import datetime
from enum import Enum
import os

from qgis.core import QgsRasterLayer

from ..mapbiomas_legenda import criar_renderizador_paletado


class Language(Enum):
    """Idiomas suportados para rótulos da legenda."""
    PT = "pt"
    EN = "en"


def _stamp(layer, fonte):
    """Adiciona propriedades customizadas de rastreabilidade à camada."""
    layer.setCustomProperty("data_extracao", datetime.now().strftime("%Y-%m-%d"))
    layer.setCustomProperty("fonte", fonte)
    return layer


def _invalid(layer_name, msg):
    """Cria e retorna uma camada de raster inválida com mensagem de erro."""
    layer = QgsRasterLayer("", layer_name)
    layer.error_msg = msg
    return layer


def fetch_raster(
    url,
    mask_layer,
    output_path,
    layer_name="MapBiomas",
    feedback=None,
    lang="pt",
    nodata=0,
):
    """Baixa e corta um raster COG remoto (ou local) via polígono de máscara.

    Args:
        url (str): URL HTTP/HTTPS do COG (ou caminho VSI / caminho local).
        mask_layer (QgsVectorLayer): Camada vetorial com o polígono do município/máscara.
        output_path (str): Caminho local onde o GeoTIFF recortado será gravado.
        layer_name (str): Nome de exibição da camada no QGIS (default "MapBiomas").
        feedback (QgsProcessingFeedback, optional): Objeto de feedback para processamento.
        lang (str | Language): Idioma para rótulos da legenda ('pt' ou 'en').
        nodata (int | float): Valor de NoData (default 0).

    Returns:
        QgsRasterLayer: Camada raster carregada do GeoTIFF salvo (ou camada inválida com .error_msg).
    """
    if not url:
        return _invalid(layer_name, "URL inválida ou não informada")

    if not mask_layer or not mask_layer.isValid():
        return _invalid(layer_name, f"{url}: máscara de recorte inválida ou ausente")

    # Formatar gdal_input: se URL HTTP/HTTPS, prefixar com /vsicurl/
    if url.startswith(("http://", "https://")):
        gdal_input = "/vsicurl/" + url
    else:
        gdal_input = url

    # (a) Abrir temporariamente o raster para obter seu CRS
    temp_raster = QgsRasterLayer(gdal_input, "temp_raster")
    if not temp_raster.isValid() or not temp_raster.crs().isValid():
        causa = temp_raster.error().message() or "falha ao abrir raster remoto/local"
        return _invalid(layer_name, f"{url}: {causa}")

    raster_crs = temp_raster.crs()

    import processing

    # (a) Reprojetar a máscara de 4674 para o CRS do raster se diferente
    mask_to_use = mask_layer
    if mask_layer.crs() != raster_crs:
        try:
            reproj_res = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": mask_layer,
                    "TARGET_CRS": raster_crs,
                    "OUTPUT": "memory:",
                },
                feedback=feedback,
            )
            mask_to_use = reproj_res.get("OUTPUT")
            if not mask_to_use or not mask_to_use.isValid():
                return _invalid(
                    layer_name,
                    f"{url}: falha na reprojeção da máscara para CRS {raster_crs.authid()}",
                )
        except Exception as exc:
            return _invalid(
                layer_name,
                f"{url}: erro ao reprojetar máscara ({exc})",
            )

    # (b) Executar gdal:cliprasterbymasklayer com CROP_TO_CUTLINE=True, NODATA=nodata e saída GeoTIFF
    clip_params = {
        "INPUT": gdal_input,
        "MASK": mask_to_use,
        "NODATA": nodata,
        "ALPHA_BAND": False,
        "CROP_TO_CUTLINE": True,
        "KEEP_RESOLUTION": True,
        "OUTPUT": output_path,
    }

    try:
        processing.run(
            "gdal:cliprasterbymasklayer",
            clip_params,
            feedback=feedback,
        )
    except Exception as exc:
        return _invalid(
            layer_name,
            f"{url}: falha no algoritmo de recorte GDAL ({exc})",
        )

    # (c) Verificar se o GeoTIFF foi criado e devolve QgsRasterLayer do .tif gravado
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return _invalid(
            layer_name,
            f"{url}: arquivo GeoTIFF não gerado em {output_path}",
        )

    out_layer = QgsRasterLayer(output_path, layer_name)
    if not out_layer.isValid():
        causa = out_layer.error().message() or "não foi possível carregar o GeoTIFF gerado"
        return _invalid(layer_name, f"{url}: {causa}")

    # (passo 12) Aplicar o renderizador paletado do MapBiomas antes de devolver
    lang_str = lang.value if isinstance(lang, Language) else str(lang)
    try:
        renderer = criar_renderizador_paletado(out_layer, lang=lang_str)
        if renderer:
            out_layer.setRenderer(renderer)
    except Exception as exc:
        if feedback is not None:
            feedback.pushWarning(f"Não foi possível aplicar legenda MapBiomas: {exc}")

    return _stamp(out_layer, f"COG remoto ({url})")


def fetch_layer(url, mask_layer, output_path, layer_name="MapBiomas", feedback=None, lang="pt"):
    """Alias para fetch_raster conforme convenção dos demais conectores."""
    return fetch_raster(
        url=url,
        mask_layer=mask_layer,
        output_path=output_path,
        layer_name=layer_name,
        feedback=feedback,
        lang=lang,
    )
