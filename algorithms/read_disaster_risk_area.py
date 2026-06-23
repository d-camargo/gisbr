# -*- coding: utf-8 -*-
from .base_read_algorithm import BaseReadAlgorithm


class ReadDisasterRiskArea(BaseReadAlgorithm):
    GEO = "disaster_risk_area"
    FUNCTION_NAME = "read_disaster_risk_area"
    DISPLAY_NAME = "Areas de risco de desastre"
    SUPPORTS_CODE = False
    HELP = (
        "Areas de risco de desastre (CEMADEN/IBGE). Arquivo nacional unico."
    )
