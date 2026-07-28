# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadHealthRegion(BaseReadAlgorithm):
    GEO = "health_region"
    FUNCTION_NAME = "read_health_region"
    DISPLAY_NAME = "Regioes de saude"
    SUPPORTS_CODE = False
    HELP = (
        "Regioes de saude (DataSUS). Arquivo nacional unico; filtre por atributo apos a carga."
    )
