# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadCountry(BaseReadAlgorithm):
    GEO = "country"
    FUNCTION_NAME = "read_country"
    DISPLAY_NAME = "Pais (Brasil)"
    SUPPORTS_CODE = False
    HELP = "Limite do territorio nacional brasileiro."
