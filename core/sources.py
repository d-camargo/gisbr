# -*- coding: utf-8 -*-
"""Catalogo declarativo de fontes do diagnostico (ver ARQUITETURA.md §3.1).

Cada fonte e um dict: id, eixo, nivel, protocolo ("wfs"|"arcgis"|"basemap"),
endpoint, type_name, crs, campo_muni, output_format, licenca, fonte.
Sera preenchido na T-010 a partir de docs/.../fontes-detalhe.md (T-007).
"""

SOURCES = []  # type: list[dict]
