# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadSemiarid(BaseReadAlgorithm):
    GEO = "semiarid"
    FUNCTION_NAME = "read_semiarid"
    DISPLAY_NAME = "Semiarido"
    SUPPORTS_CODE = False
    HELP = (
        "Delimitacao do Semiarido brasileiro (SUDENE). Arquivo nacional unico."
    )
