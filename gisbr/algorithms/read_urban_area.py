# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadUrbanArea(BaseReadAlgorithm):
    GEO = "urban_area"
    FUNCTION_NAME = "read_urban_area"
    DISPLAY_NAME = "Areas urbanizadas"
    SUPPORTS_CODE = False
    HELP = (
        "Areas urbanizadas (IBGE). Arquivo nacional unico; filtre por atributo apos a carga."
    )
