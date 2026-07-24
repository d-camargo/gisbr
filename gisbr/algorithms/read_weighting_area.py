# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadWeightingArea(BaseReadAlgorithm):
    GEO = "weighting_area"
    FUNCTION_NAME = "read_weighting_area"
    DISPLAY_NAME = "Areas de ponderacao"
    CODE_COLUMN = "code_weighting"
    ABBREV_COLUMN = "abbrev_state"
    UF_SLICED = True
    HELP = (
        "Areas de ponderacao do Censo (IBGE). Metadado fatiado por UF: "
        'filtre por sigla ("MG") ou codigo de UF.'
    )
