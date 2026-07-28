# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadPopArrangements(BaseReadAlgorithm):
    GEO = "pop_arrengements"
    FUNCTION_NAME = "read_pop_arrangements"
    DISPLAY_NAME = "Arranjos populacionais"
    SUPPORTS_CODE = False
    HELP = (
        "Arranjos populacionais (IBGE). Arquivo nacional unico. (geo='pop_arrengements' no dado oficial.)"
    )
