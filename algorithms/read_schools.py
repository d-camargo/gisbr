# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadSchools(BaseReadAlgorithm):
    GEO = "schools"
    FUNCTION_NAME = "read_schools"
    DISPLAY_NAME = "Escolas"
    SUPPORTS_CODE = False
    HELP = (
        "Escolas (INEP, pontos). Sem versao simplificada; filtre por code_muni apos a carga."
    )
