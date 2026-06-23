# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadHealthFacilities(BaseReadAlgorithm):
    GEO = "health_facilities"
    FUNCTION_NAME = "read_health_facilities"
    DISPLAY_NAME = "Estabelecimentos de saude"
    SUPPORTS_CODE = False
    HELP = (
        "Estabelecimentos de saude (CNES/DataSUS, pontos). Sem versao simplificada; filtre por atributo apos a carga."
    )
