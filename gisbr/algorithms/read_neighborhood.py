# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadNeighborhood(BaseReadAlgorithm):
    GEO = "neighborhood"
    FUNCTION_NAME = "read_neighborhood"
    DISPLAY_NAME = "Bairros"
    SUPPORTS_CODE = False
    HELP = (
        "Bairros (IBGE). Arquivo nacional unico e pesado; filtre por code_muni apos a carga."
    )
