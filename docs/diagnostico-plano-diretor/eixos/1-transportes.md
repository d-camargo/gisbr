# Eixo 1: Infraestrutura de Transportes

Este eixo foca na infraestrutura de locomoção, conexões intermunicipais e rodovias federais/estaduais, essenciais para o planejamento de mobilidade urbana e regional do Plano Diretor.

## Catálogo de Geoservers e Serviços

| Fonte / Órgão | Nível | Serviço | Endpoint / URL | Camadas Principais | CRS | Licença | Data de Acesso | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **DNIT** | Federal | WFS | `https://geoservicos.inde.gov.br/geoserver/DNIT/ows?service=WFS&version=2.0.0&request=GetCapabilities` | `DNIT:snv_202507a` (Rodovias Federais)<br>`DNIT:cide_2024_25` (Rodovias Estaduais unificadas) | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. Sem campo muni nativo (filtrar por bbox; possui `sg_uf`/`uf` para estado) |
| **MInfra / VALEC** (ANTT) | Federal | WFS (via INDE) | `https://geoservicos.inde.gov.br/geoserver/ows?service=WFS&version=1.1.0&request=GetCapabilities` | `MInfra:Ferrovias` (Rede Ferroviária)<br>`VALEC:trecho_ferroviario_infrasa` (Trechos ferroviários) | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. `MInfra:Ferrovias` possui campo `municipio` (string). `VALEC` requer filtragem por bbox. |
| **DER-MG** | Estadual | WFS (via IDE-Sisema) | `https://geoserver.meioambiente.mg.gov.br/IDE/wfs?service=WFS&version=2.0.0&request=GetCapabilities` | `IDE:ide_0401_mg_rodovias_lin` (Rodovias de MG)<br>`IDE:ide_0402_mg_ferrovias_lin` (Ferrovias de MG) | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. Sem campo muni nativo (filtrar por bbox; `ide_0401_mg_rodovias_lin` possui `unidade_fe` para estado) |
| **IBGE** (via SGB/CPRM) | Federal | WFS | `https://opendata.sgb.gov.br/geoserver/ows?service=WFS&version=1.1.0&request=GetCapabilities` | `p3m:vw_ibge_rdv` (Trecho rodoviário BC250) | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. Sem campo muni nativo (filtrar por bbox). |
| **OpenStreetMap** (Terrestris) | Global | WMS | `https://ows.terrestris.de/osm/service?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities` | `OSM-WMS` | EPSG:3857, EPSG:4326 | CC-BY-SA / ODbL | 29/06/2026 | Online - GetCapabilities verificado |

## Integração no GisBR
- **Cobertura Atual:** Nenhuma.
- **Próximos Passos:** Implementar conector WFS na arquitetura do GisBR apontando para o DNIT (SNV) e a IDE-Sisema (DER-MG) para extração de malhas de transporte locais, filtradas dinamicamente pelo código do município.
- **Validação no QGIS (a validar):** Importar a camada `DNIT:snv_202507a` e filtrar pela UF desejada para avaliar performance.
