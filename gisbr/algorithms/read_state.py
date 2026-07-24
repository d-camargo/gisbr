# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadState(BaseReadAlgorithm):
    GEO = "state"
    FUNCTION_NAME = "read_state"
    DISPLAY_NAME = "Estados (UF)"
    CODE_COLUMN = "code_state"
    ABBREV_COLUMN = "abbrev_state"
    UF_SLICED = False
    HELP = (
        "Unidades da federacao. Arquivo nacional unico; filtre por sigla "
        '("MG"), codigo IBGE (31) ou "all".'
    )
