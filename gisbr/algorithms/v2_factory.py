# -*- coding: utf-8 -*-
"""Gera dinamicamente os algoritmos read_*_v2 a partir de uma tabela de specs.

Cada entrada vira uma subclasse de BaseReadV2Algorithm. O id do algoritmo
recebe o sufixo "_v2" para nao colidir com o backend GPKG (Fase 1).

specs: (geo_v2, function_base, display, code_column, abbrev_column, supports_code, help)
"""

from .base_read_v2_algorithm import BaseReadV2Algorithm

# fmt: off
_SPECS = [
    # politico-administrativa
    ("country",             "read_country",            "Pais (Brasil)",          None,                None,           False, "Limite nacional."),
    ("regions",             "read_region",             "Grandes regioes",        "code_region",       None,           True,  "5 grandes regioes (IBGE)."),
    ("states",              "read_state",              "Estados (UF)",           "code_state",        "abbrev_state", True,  "UFs. Filtre por sigla (\"MG\"), codigo (31) ou \"all\"."),
    ("mesoregions",         "read_meso_region",        "Mesorregioes",           "code_meso",         "abbrev_state", True,  "Mesorregioes. Filtre por UF (sigla/codigo) ou codigo da meso."),
    ("microregions",        "read_micro_region",       "Microrregioes",          "code_micro",        "abbrev_state", True,  "Microrregioes. Filtre por UF ou codigo da micro."),
    ("immediateregions",    "read_immediate_region",   "Regioes imediatas",      "code_immediate",    "abbrev_state", True,  "Regioes geograficas imediatas (IBGE)."),
    ("intermediateregions", "read_intermediate_region","Regioes intermediarias", "code_intermediate", "abbrev_state", True,  "Regioes geograficas intermediarias (IBGE)."),
    ("municipalities",      "read_municipality",       "Municipios",             "code_muni",         "abbrev_state", True,  "Municipios. UF (sigla/codigo) filtra o estado; codigo de 7 digitos, um municipio."),
    ("municipalseats",      "read_municipal_seat",     "Sedes municipais",       "code_muni",         "abbrev_state", True,  "Sedes municipais (pontos)."),
    # censitarios
    ("censustracts",        "read_census_tract",       "Setores censitarios",    "code_tract",        "abbrev_state", True,  "Setores censitarios. Filtre por UF. (Base do join com censobr.)"),
    ("weightingareas",      "read_weighting_area",     "Areas de ponderacao",    "code_weighting",    "abbrev_state", True,  "Areas de ponderacao do Censo."),
    ("statsgrid",           "read_statistical_grid",   "Grade estatistica",      None,                None,           False, "Grade estatistica (IBGE). Arquivo grande."),
    ("neighborhoods",       "read_neighborhood",       "Bairros",                "code_muni",         "abbrev_state", True,  "Bairros (IBGE). Filtre por municipio (code_muni)."),
    # urbanos
    ("metroarea",           "read_metro_area",         "Regioes metropolitanas", None,                None,           False, "Regioes metropolitanas."),
    ("urbanareas",          "read_urban_area",         "Areas urbanizadas",      None,                None,           False, "Areas urbanizadas (IBGE)."),
    ("poparrangements",     "read_pop_arrangements",   "Arranjos populacionais", None,                None,           False, "Arranjos populacionais (IBGE)."),
    # ambiental / territorial
    ("biomes",              "read_biomes",             "Biomas",                 None,                None,           False, "Biomas brasileiros."),
    ("amazonialegal",       "read_amazon",             "Amazonia Legal",         None,                None,           False, "Limite da Amazonia Legal."),
    ("semiarid",            "read_semiarid",           "Semiarido",              None,                None,           False, "Delimitacao do Semiarido."),
    ("conservationunits",   "read_conservation_units", "Unidades de conservacao",None,                None,           False, "Unidades de conservacao (MMA)."),
    ("indigenouslands",     "read_indigenous_land",    "Terras indigenas",       None,                None,           False, "Terras indigenas (FUNAI)."),
    ("disasterriskareas",   "read_disaster_risk_area", "Areas de risco",         None,                None,           False, "Areas de risco de desastre."),
    # setoriais
    ("healthregions",       "read_health_region",      "Regioes de saude",       None,                None,           False, "Regioes de saude (DataSUS)."),
    ("healthfacilities",    "read_health_facilities",  "Estabelecimentos saude", None,                None,           False, "Estabelecimentos de saude (CNES, pontos)."),
    ("schools",             "read_schools",            "Escolas",                "code_muni",         "abbrev_state", True,  "Escolas (INEP, pontos). Filtre por municipio."),
    # so-v2 (nao existem no v1.7.0)
    ("favelas",             "read_favela",             "Favelas / comunidades",  "code_muni",         "abbrev_state", True,  "Favelas e comunidades urbanas (IBGE 2022). So-v2."),
    ("pollingplaces",       "read_polling_places",     "Locais de votacao",      None,                None,           False, "Locais de votacao (TSE, pontos). So-v2."),
    ("quilombolalands",     "read_quilombola_land",    "Terras quilombolas",     None,                None,           False, "Territorios quilombolas (INCRA). So-v2."),
]
# fmt: on


def _make_class(geo, function_base, display, code_col, abbrev_col, supports, help_):
    return type(
        f"Read_{geo}_V2",
        (BaseReadV2Algorithm,),
        {
            "GEO": geo,
            "FUNCTION_NAME": f"{function_base}_v2",
            "DISPLAY_NAME": f"{display} (v2)",
            "CODE_COLUMN": code_col,
            "ABBREV_COLUMN": abbrev_col,
            "SUPPORTS_CODE": supports,
            "HELP": help_,
        },
    )


V2_ALGORITHMS = [_make_class(*spec) for spec in _SPECS]
