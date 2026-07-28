# -*- coding: utf-8 -*-
"""Constantes do plugin geobr-qgis (Fase 1 - backend GPKG legacy v1.7.0).

Nada de dependencias externas: apenas stdlib e PyQGIS.
"""

# ---------------------------------------------------------------------------
# URLs / mirrors  (replica a cadeia de fallback do geobr Python: url_solver)
# ---------------------------------------------------------------------------

# Metadado legacy v1.7.0 (CSV). O IPEA redireciona http -> https.
METADATA_URL = "https://www.ipea.gov.br/geobr/metadata/metadata_1.7.0_gpkg.csv"

# Base primaria dos dados no IPEA (download_path do CSV ja vem absoluto, mas
# guardamos a base para reconstrucao/depuracao).
IPEA_BASE = "https://www.ipea.gov.br/geobr/data_gpkg"

# Mirror no GitHub: mesmo file_id do arquivo do IPEA.
# Nota: O arquivo de metadados metadata_1.7.0_gpkg.csv existe como asset no mirror:
# https://github.com/ipeaGIT/geobr/releases/download/v1.7.0/metadata_1.7.0_gpkg.csv
GITHUB_MIRRORS = [
    "https://github.com/ipeaGIT/geobr/releases/download/v1.7.0/",
]

# ---------------------------------------------------------------------------
# Backend v2 (Parquet) — Fase 2
#
# Cadeia de URL INVERTIDA em relacao ao v1.7.0: o primario e o GitHub
# (browser_download_url dos assets) e o IPEA e fallback.
# ---------------------------------------------------------------------------

GEOBR_DATA_RELEASE = "v2.0.0"
GEOBR_V2_API_LATEST = "https://api.github.com/repos/ipea/geobr_prep_data/releases/latest"
GEOBR_V2_API_RELEASES = "https://api.github.com/repos/ipea/geobr_prep_data/releases"
# Fallback IPEA para os arquivos .parquet (mesmo file_name).
IPEA_V2_FALLBACK_BASE = "https://www.ipea.gov.br/geobr/data_v2.0.0"

# Mapa funcao read_* -> token `geo` no v2 (primeiro segmento do nome do
# arquivo, ANTES do primeiro "_"). Difere do v1.7.0: aqui os nomes sao no
# PLURAL (ex.: "states", "municipalities", "censustracts").
GEO_BY_FUNCTION_V2 = {
    "read_country": "country",
    "read_region": "regions",
    "read_state": "states",
    "read_meso_region": "mesoregions",
    "read_micro_region": "microregions",
    "read_immediate_region": "immediateregions",
    "read_intermediate_region": "intermediateregions",
    "read_municipality": "municipalities",
    "read_municipal_seat": "municipalseats",
    "read_weighting_area": "weightingareas",
    "read_census_tract": "censustracts",
    "read_statistical_grid": "statsgrid",
    "read_metro_area": "metroarea",
    "read_urban_area": "urbanareas",
    "read_amazon": "amazonialegal",
    "read_biomes": "biomes",
    "read_conservation_units": "conservationunits",
    "read_disaster_risk_area": "disasterriskareas",
    "read_indigenous_land": "indigenouslands",
    "read_semiarid": "semiarid",
    "read_health_facilities": "healthfacilities",
    "read_health_region": "healthregions",
    "read_neighborhood": "neighborhoods",
    "read_schools": "schools",
    "read_pop_arrangements": "poparrangements",
    # Geografias so-v2 (nao existem no metadado v1.7.0):
    "read_favela": "favelas",
    "read_polling_places": "pollingplaces",
    "read_quilombola_land": "quilombolalands",
}

# ---------------------------------------------------------------------------
# CRS
# ---------------------------------------------------------------------------

# Todos os dados do geobr estao em SIRGAS 2000 geografico.
EPSG_GEOBR = 4674
# CRS metrico para analises em BH / MG (UTM 23S).
EPSG_UTM23S = 31983

# ---------------------------------------------------------------------------
# Cache em disco (separado do geobr Python para nao colidir)
# ---------------------------------------------------------------------------

CACHE_SUBDIR = "geobr-qgis"

# ---------------------------------------------------------------------------
# Mapa funcao read_* -> valor da coluna `geo` no metadado v1.7.0
#
# IMPORTANTE: o nome da `geo` no CSV difere do nome da funcao. Valores abaixo
# foram extraidos dos valores unicos reais do metadata_1.7.0_gpkg.csv.
# (Em v2 mudam de novo; manter mapeamento separado por backend.)
# ---------------------------------------------------------------------------

GEO_BY_FUNCTION = {
    "read_country": "country",
    "read_region": "regions",
    "read_state": "state",
    "read_meso_region": "meso_region",
    "read_micro_region": "micro_region",
    "read_immediate_region": "immediate_regions",
    "read_intermediate_region": "intermediate_regions",
    "read_municipality": "municipality",
    "read_municipal_seat": "municipal_seat",
    "read_weighting_area": "weighting_area",
    "read_census_tract": "census_tract",
    "read_statistical_grid": "statistical_grid",
    "read_metro_area": "metropolitan_area",
    "read_urban_area": "urban_area",
    "read_amazon": "amazonia_legal",
    "read_biomes": "biomes",
    "read_conservation_units": "conservation_units",
    "read_disaster_risk_area": "disaster_risk_area",
    "read_indigenous_land": "indigenous_land",
    "read_semiarid": "semiarid",
    "read_health_facilities": "health_facilities",
    "read_health_region": "health_region",
    "read_neighborhood": "neighborhood",
    "read_schools": "schools",
    "read_urban_concentrations": "urban_concentrations",
    "read_pop_arrangements": "pop_arrengements",  # typo presente no dado oficial
}

# ---------------------------------------------------------------------------
# Tabela de UF: codigo IBGE <-> sigla.  (codigos 11-53, exceto 20/30/40)
# Portada do _filter.py do geobr.
# ---------------------------------------------------------------------------

UF_CODE_TO_ABBREV = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
    28: "SE", 29: "BA",
    31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF",
}

UF_ABBREV_TO_CODE = {abbr: code for code, abbr in UF_CODE_TO_ABBREV.items()}


def normalize_uf(value):
    """Recebe sigla ('MG'), codigo ('31' ou 31) ou codigo de municipio
    ('3106200') e retorna ``(uf_code, uf_abbrev)`` ou ``(None, None)``.

    Usa os dois primeiros digitos para deduzir a UF (padrao IBGE), igual ao
    geobr (``str(code)[:2]``).
    """
    if value is None:
        return None, None
    s = str(value).strip()
    if not s or s.lower() == "all":
        return None, None
    su = s.upper()
    if su in UF_ABBREV_TO_CODE:
        code = UF_ABBREV_TO_CODE[su]
        return code, su
    # numerico: pega os 2 primeiros digitos
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) >= 2:
        uf_code = int(digits[:2])
        if uf_code in UF_CODE_TO_ABBREV:
            return uf_code, UF_CODE_TO_ABBREV[uf_code]
    return None, None
