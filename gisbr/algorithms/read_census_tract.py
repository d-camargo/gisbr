# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadCensusTract(BaseReadAlgorithm):
    GEO = "census_tract"
    FUNCTION_NAME = "read_census_tract"
    DISPLAY_NAME = "Setores censitarios"
    CODE_COLUMN = "code_tract"
    ABBREV_COLUMN = "abbrev_state"
    UF_SLICED = True
    HELP = (
        "Setores censitarios (IBGE). Metadado fatiado por UF: filtre por "
        'sigla ("MG") ou codigo de UF para baixar so aquele estado. '
        "Base para join com o censobr (Fase 2)."
    )
