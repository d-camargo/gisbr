# -*- coding: utf-8 -*-
"""Catalogo declarativo de fontes do diagnostico (ARQUITETURA.md §3.1).

Preenchido a partir de docs/diagnostico-plano-diretor/fontes-detalhe.md (T-007).
Fase A: fontes WFS + basemap. As fontes ArcGIS REST entram na T-012.

Cada fonte e um dict:
  id, eixo, nome, protocolo ("wfs"|"basemap"), endpoint, type_name, srs,
  filtro, licenca.
filtro: {"tipo": "cql_codigo", "campo": <str>}  -> CQL campo = <code_muni>
        {"tipo": "cql_nome",   "campo": <str>}  -> CQL campo = '<nome_muni>'
        {"tipo": "bbox"}                          -> filtro espacial por bbox
type_name pode conter "{uf}" (substituido pela sigla da UF do municipio).
"""

SOURCES = [
    # --- Eixo 1: Transportes ---
    {"id": "dnit_snv", "eixo": "transportes", "nome": "DNIT — SNV (rodovias federais)",
     "protocolo": "wfs", "endpoint": "https://geoservicos.inde.gov.br/geoserver/DNIT/ows",
     "type_name": "DNIT:snv_202507a", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    {"id": "minfra_ferrovias", "eixo": "transportes", "nome": "MInfra — Ferrovias",
     "protocolo": "wfs", "endpoint": "https://geoservicos.inde.gov.br/geoserver/ows",
     "type_name": "MInfra:Ferrovias", "srs": "EPSG:4674",
     "filtro": {"tipo": "cql_nome", "campo": "municipio"}, "licenca": "Publica"},
    {"id": "der_mg_rodovias", "eixo": "transportes", "nome": "DER-MG — Rodovias estaduais",
     "protocolo": "wfs", "endpoint": "https://geoserver.meioambiente.mg.gov.br/IDE/wfs",
     "type_name": "IDE:ide_0401_mg_rodovias_lin", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    {"id": "osm_vias", "eixo": "transportes", "nome": "OSM — Vias urbanas (Overpass)",
     "protocolo": "osm", "licenca": "OpenStreetMap contributors"},
    # --- Eixo 2: Drenagem e Saneamento ---
    {"id": "sgb_rios", "eixo": "saneamento", "nome": "SGB/CPRM — Rios (BC250)",
     "protocolo": "wfs", "endpoint": "https://opendata.sgb.gov.br/geoserver/ows",
     "type_name": "p3m:vw_ibge_rios", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    {"id": "sgb_bacias", "eixo": "saneamento", "nome": "SGB/CPRM — Bacias hidrograficas",
     "protocolo": "wfs", "endpoint": "https://opendata.sgb.gov.br/geoserver/ows",
     "type_name": "p3m:vw_ibge_bacia_hidro_6", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    # --- Eixo 4: Ambiental ---
    {"id": "sicar_imoveis", "eixo": "ambiental", "nome": "SICAR — Imoveis (CAR)",
     "protocolo": "wfs", "endpoint": "https://geoserver.car.gov.br/geoserver/sicar/wfs",
     "type_name": "sicar:sicar_imoveis_{uf}", "srs": "EPSG:4674",
     "filtro": {"tipo": "cql_codigo", "campo": "cod_municipio_ibge"}, "licenca": "Publica"},
    {"id": "icmbio_embargos", "eixo": "ambiental", "nome": "ICMBio — Embargos",
     "protocolo": "wfs", "endpoint": "https://geoservicos.inde.gov.br/geoserver/ICMBio/ows",
     "type_name": "ICMBio:embargos_icmbio", "srs": "EPSG:4674",
     "filtro": {"tipo": "cql_nome", "campo": "municipio"}, "licenca": "Publica"},
    {"id": "icmbio_uc", "eixo": "ambiental", "nome": "ICMBio — UCs federais",
     "protocolo": "wfs", "endpoint": "https://geoservicos.inde.gov.br/geoserver/ICMBio/ows",
     "type_name": "ICMBio:limiteucsfederais_a", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    # --- ArcGIS REST (Fase C) ---
    {"id": "ana_hidrografia", "eixo": "saneamento", "nome": "ANA — Hidrografia",
     "protocolo": "arcgis",
     "endpoint": "https://www.snirh.gov.br/arcgis/rest/services/DADOSABERTOS/Hidrografia/MapServer",
     "layer_id": "0", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    {"id": "ibama_autos", "eixo": "ambiental", "nome": "IBAMA — Autos de infracao/embargos",
     "protocolo": "arcgis",
     "endpoint": "https://pamgia.ibama.gov.br/server/rest/services/app_dadosabertos/adm_auto_infracao_p/MapServer",
     "layer_id": "0", "srs": "EPSG:4674",
     "filtro": {"tipo": "cql_codigo", "campo": "cod_municipio"}, "licenca": "Publica"},
    {"id": "ibama_esgoto", "eixo": "saneamento", "nome": "IBAMA — Esgotamento sanitario",
     "protocolo": "arcgis",
     "endpoint": "https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Sistema_de_Esgotamento_Sanit%C3%A1rio/MapServer",
     "layer_id": "6", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    {"id": "ibama_agua", "eixo": "saneamento", "nome": "IBAMA — Abastecimento de agua",
     "protocolo": "arcgis",
     "endpoint": "https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Sistema_de_Abastecimento_de_%C3%81gua/MapServer",
     "layer_id": "5", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    {"id": "ibama_aterro", "eixo": "saneamento", "nome": "IBAMA — Aterro sanitario",
     "protocolo": "arcgis",
     "endpoint": "https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Aterro_Sanit%C3%A1rio/MapServer",
     "layer_id": "8", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    # --- geobr v1 (GPKG; sem dependencia externa) ---
    {"id": "geobr_municipio", "eixo": "demografia", "nome": "Limite municipal (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_municipality", "recorte": "code"},
    {"id": "geobr_setores", "eixo": "demografia", "nome": "Setores censitarios (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_census_tract", "recorte": "code"},
    {"id": "geobr_ponderacao", "eixo": "demografia", "nome": "Areas de ponderacao (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_weighting_area", "recorte": "code"},
    {"id": "geobr_escolas", "eixo": "educacao", "nome": "Escolas (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_schools", "recorte": "bbox"},
    {"id": "geobr_saude", "eixo": "saude", "nome": "Estabelecimentos de saude (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_health_facilities", "recorte": "bbox"},
    {"id": "geobr_biomas", "eixo": "ambiental", "nome": "Biomas (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_biomes", "recorte": "bbox"},
    {"id": "geobr_ucs", "eixo": "ambiental", "nome": "Unidades de conservacao (geobr)",
     "protocolo": "geobr", "algo": "read_conservation_units", "recorte": "bbox"},
    {"id": "geobr_terras_indigenas", "eixo": "ambiental", "nome": "Terras indigenas (geobr)",
     "protocolo": "geobr", "algo": "read_indigenous_land", "recorte": "bbox"},
    {"id": "geobr_risco", "eixo": "ambiental", "nome": "Areas de risco de desastre (geobr)",
     "protocolo": "geobr", "algo": "read_disaster_risk_area", "recorte": "bbox"},
    {"id": "geobr_mancha_urbana", "eixo": "urbano", "nome": "Mancha urbana (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_urban_area", "recorte": "bbox"},
    {"id": "geobr_sede", "eixo": "pol-admin", "nome": "Sede municipal (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_municipal_seat", "recorte": "bbox"},
    {"id": "geobr_bairros", "eixo": "pol-admin", "nome": "Bairros (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_neighborhood", "recorte": "bbox"},
    # --- geobr v2 (so-v2; REQUEREM driver Parquet ou pyarrow; senao sao pulados) ---
    {"id": "geobr_favelas", "eixo": "demografia", "nome": "Favelas/comunidades (geobr v2)",
     "protocolo": "geobr", "algo": "read_favela_v2", "recorte": "code", "requer_parquet": True},
    {"id": "geobr_locais_votacao", "eixo": "pol-admin", "nome": "Locais de votacao (geobr v2)",
     "protocolo": "geobr", "algo": "read_polling_places_v2", "recorte": "code", "requer_parquet": True},
    {"id": "geobr_quilombolas", "eixo": "ambiental", "nome": "Terras quilombolas (geobr v2)",
     "protocolo": "geobr", "algo": "read_quilombola_land_v2", "recorte": "bbox", "requer_parquet": True},
    # --- Contexto ---
    {"id": "basemap_satelite", "eixo": "contexto", "nome": "Imagem de satelite (Esri)",
     "protocolo": "basemap"},
]
