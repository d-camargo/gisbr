# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadMesoRegion(BaseReadAlgorithm):
    GEO = "meso_region"
    FUNCTION_NAME = "read_meso_region"
    DISPLAY_NAME = "Mesorregioes"
    CODE_COLUMN = "code_meso"
    ABBREV_COLUMN = "abbrev_state"
    UF_SLICED = True
    HELP = (
        "Mesorregioes (IBGE). Metadado fatiado por UF: sigla (\"MG\") ou codigo "
        "de UF baixa o estado; um codigo de mesorregiao filtra uma so."
    )
