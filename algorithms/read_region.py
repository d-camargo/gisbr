# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadRegion(BaseReadAlgorithm):
    GEO = "regions"
    FUNCTION_NAME = "read_region"
    DISPLAY_NAME = "Grandes regioes"
    CODE_COLUMN = "code_region"
    ABBREV_COLUMN = "name_region"
    UF_SLICED = False
    HELP = (
        "5 grandes regioes do IBGE. Filtre por codigo de regiao "
        "(1=Norte ... 5=Centro-Oeste) ou 'all'."
    )
