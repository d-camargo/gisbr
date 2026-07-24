# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadIndigenousLand(BaseReadAlgorithm):
    GEO = "indigenous_land"
    FUNCTION_NAME = "read_indigenous_land"
    DISPLAY_NAME = "Terras indigenas"
    SUPPORTS_CODE = False
    HELP = (
        "Terras indigenas (FUNAI). Arquivo nacional unico; filtre por atributo apos a carga."
    )
