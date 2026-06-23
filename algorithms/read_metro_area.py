# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadMetroArea(BaseReadAlgorithm):
    GEO = "metropolitan_area"
    FUNCTION_NAME = "read_metro_area"
    DISPLAY_NAME = "Regioes metropolitanas"
    SUPPORTS_CODE = False
    HELP = (
        "Regioes metropolitanas oficiais. Arquivo nacional unico; filtre "
        "depois por atributo (ex.: name_metro = 'RM Belo Horizonte')."
    )
