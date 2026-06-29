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
    # --- Contexto ---
    {"id": "basemap_satelite", "eixo": "contexto", "nome": "Imagem de satelite (Esri)",
     "protocolo": "basemap"},
]
