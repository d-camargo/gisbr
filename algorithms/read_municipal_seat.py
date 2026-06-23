# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadMunicipalSeat(BaseReadAlgorithm):
    GEO = "municipal_seat"
    FUNCTION_NAME = "read_municipal_seat"
    DISPLAY_NAME = "Sedes municipais"
    SUPPORTS_CODE = False
    HELP = (
        "Sedes municipais (pontos). Sem versao simplificada; filtre por atributo (code_muni) apos a carga."
    )
