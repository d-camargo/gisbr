# -*- coding: utf-8 -*-
"""Algoritmos read_* do geobr-qgis (Processing Provider).

Fase 1 (backend GPKG v1.7.0). Geografias v2-only (favela, polling_places,
quilombola_land) e read_comparable_areas (assinatura start_year/end_year)
ficam para a Fase 2 / roadmap.
"""

# --- Divisao politico-administrativa ---
from .read_country import ReadCountry
from .read_region import ReadRegion
from .read_state import ReadState
from .read_meso_region import ReadMesoRegion
from .read_micro_region import ReadMicroRegion
from .read_immediate_region import ReadImmediateRegion
from .read_intermediate_region import ReadIntermediateRegion
from .read_municipality import ReadMunicipality
from .read_municipal_seat import ReadMunicipalSeat

# --- Recortes censitarios ---
from .read_census_tract import ReadCensusTract
from .read_weighting_area import ReadWeightingArea
from .read_statistical_grid import ReadStatisticalGrid
from .read_neighborhood import ReadNeighborhood

# --- Recortes urbanos / metropolitanos ---
from .read_metro_area import ReadMetroArea
from .read_urban_area import ReadUrbanArea
from .read_urban_concentrations import ReadUrbanConcentrations
from .read_pop_arrangements import ReadPopArrangements

# --- Ambiental / territorial ---
from .read_biomes import ReadBiomes
from .read_amazon import ReadAmazon
from .read_semiarid import ReadSemiarid
from .read_conservation_units import ReadConservationUnits
from .read_indigenous_land import ReadIndigenousLand
from .read_disaster_risk_area import ReadDisasterRiskArea

# --- Equipamentos / setoriais ---
from .read_health_region import ReadHealthRegion
from .read_health_facilities import ReadHealthFacilities
from .read_schools import ReadSchools

# --- Backend Parquet / v2.0.0 (Fase 2, classes geradas dinamicamente) ---
from .v2_factory import V2_ALGORITHMS

# Ordem de registro no provider.
ALGORITHMS = [
    # politico-administrativa
    ReadCountry,
    ReadRegion,
    ReadState,
    ReadMesoRegion,
    ReadMicroRegion,
    ReadIntermediateRegion,
    ReadImmediateRegion,
    ReadMunicipality,
    ReadMunicipalSeat,
    # censitarios
    ReadCensusTract,
    ReadWeightingArea,
    ReadStatisticalGrid,
    ReadNeighborhood,
    # urbanos
    ReadMetroArea,
    ReadUrbanArea,
    ReadUrbanConcentrations,
    ReadPopArrangements,
    # ambiental
    ReadBiomes,
    ReadAmazon,
    ReadSemiarid,
    ReadConservationUnits,
    ReadIndigenousLand,
    ReadDisasterRiskArea,
    # setoriais
    ReadHealthRegion,
    ReadHealthFacilities,
    ReadSchools,
] + V2_ALGORITHMS
