# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadUrbanConcentrations(BaseReadAlgorithm):
    GEO = "urban_concentrations"
    FUNCTION_NAME = "read_urban_concentrations"
    DISPLAY_NAME = "Concentracoes urbanas"
    SUPPORTS_CODE = False
    HELP = (
        "Concentracoes urbanas (IBGE). Arquivo nacional unico."
    )
