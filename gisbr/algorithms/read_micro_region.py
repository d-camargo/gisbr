# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadMicroRegion(BaseReadAlgorithm):
    GEO = "micro_region"
    FUNCTION_NAME = "read_micro_region"
    DISPLAY_NAME = "Microrregioes"
    CODE_COLUMN = "code_micro"
    ABBREV_COLUMN = "abbrev_state"
    UF_SLICED = True
    HELP = (
        "Microrregioes (IBGE). Metadado fatiado por UF: sigla (\"MG\") ou codigo "
        "de UF baixa o estado; um codigo de microrregiao filtra uma so."
    )
