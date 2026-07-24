# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadIntermediateRegion(BaseReadAlgorithm):
    GEO = "intermediate_regions"
    FUNCTION_NAME = "read_intermediate_region"
    DISPLAY_NAME = "Regioes intermediarias"
    CODE_COLUMN = "code_intermediate"
    UF_SLICED = False
    HELP = (
        "Regioes geograficas intermediarias (IBGE). Arquivo nacional unico; "
        "filtre por codigo da regiao intermediaria ou \"all\"."
    )
