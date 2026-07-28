# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadImmediateRegion(BaseReadAlgorithm):
    GEO = "immediate_regions"
    FUNCTION_NAME = "read_immediate_region"
    DISPLAY_NAME = "Regioes imediatas"
    CODE_COLUMN = "code_immediate"
    UF_SLICED = False
    HELP = (
        "Regioes geograficas imediatas (IBGE). Arquivo nacional unico; "
        "filtre por codigo da regiao imediata ou \"all\"."
    )
