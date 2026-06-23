# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadConservationUnits(BaseReadAlgorithm):
    GEO = "conservation_units"
    FUNCTION_NAME = "read_conservation_units"
    DISPLAY_NAME = "Unidades de conservacao"
    SUPPORTS_CODE = False
    HELP = (
        "Unidades de conservacao (MMA). Arquivo nacional unico; filtre por atributo (name_conservation) apos a carga."
    )
