# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadAmazon(BaseReadAlgorithm):
    GEO = "amazonia_legal"
    FUNCTION_NAME = "read_amazon"
    DISPLAY_NAME = "Amazonia Legal"
    SUPPORTS_CODE = False
    HELP = (
        "Limite da Amazonia Legal brasileira. Arquivo nacional unico."
    )
