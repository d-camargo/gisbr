# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadBiomes(BaseReadAlgorithm):
    GEO = "biomes"
    FUNCTION_NAME = "read_biomes"
    DISPLAY_NAME = "Biomas"
    SUPPORTS_CODE = False
    HELP = (
        "Biomas brasileiros (IBGE/MMA). Arquivo nacional unico; filtre depois "
        "por atributo (ex.: name_biome = 'Cerrado')."
    )
