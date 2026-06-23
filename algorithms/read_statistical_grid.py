# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadStatisticalGrid(BaseReadAlgorithm):
    GEO = "statistical_grid"
    FUNCTION_NAME = "read_statistical_grid"
    DISPLAY_NAME = "Grade estatistica"
    SUPPORTS_CODE = False
    HELP = (
        "Grade estatistica de 1km (IBGE). ATENCAO: arquivo nacional muito pesado; filtre apos a carga."
    )
