# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadMunicipality(BaseReadAlgorithm):
    GEO = "municipality"
    FUNCTION_NAME = "read_municipality"
    DISPLAY_NAME = "Municipios"
    CODE_COLUMN = "code_muni"
    ABBREV_COLUMN = "abbrev_state"
    UF_SLICED = True
    HELP = (
        "Municipios brasileiros. O metadado e fatiado por UF: passar uma "
        'sigla ("MG") ou codigo de UF (31) baixa so aquele estado. Um codigo '
        "IBGE de 7 digitos (3106200) retorna um unico municipio."
    )
