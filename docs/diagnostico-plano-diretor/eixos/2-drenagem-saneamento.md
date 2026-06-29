# Eixo 2: Drenagem e Saneamento

Este eixo aborda os recursos hídricos superficiais e subterrâneos, bem como a infraestrutura de distribuição de água, coleta de esgoto e drenagem urbana, fundamentais para a definição de áreas de preservação permanente (APPs) hídricas e planejamento de saneamento no Plano Diretor.

## Catálogo de Geoservers e Serviços

| Fonte / Órgão | Nível | Serviço | Endpoint / URL | Camadas Principais | CRS | Licença | Data de Acesso | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **ANA** | Federal | ArcGIS REST | `https://www.snirh.gov.br/arcgis/rest/services/DADOSABERTOS/Hidrografia/MapServer` | `0` (Trechos de Drenagem / BHO) | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. Sem campo muni (filtrar por bbox) |
| **SGB / CPRM** | Federal | WFS | `https://opendata.sgb.gov.br/geoserver/ows?service=WFS&version=1.1.0&request=GetCapabilities` | `p3m:vw_ibge_rios` (Rios e massas d'água)<br>`p3m:vw_ibge_bacia_hidro_6` (Bacias Nível 6)<br>`p3m:vw_cprm_pol_a_hidrog` (Hidrogeologia) | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. Sem campo muni nativo (filtrar por bbox). |
| **IBAMA** | Federal | ArcGIS REST | `https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/` | `Sistema_de_Esgotamento_Sanit%C3%A1rio/MapServer/6`<br>`Sistema_de_Abastecimento_de_%C3%81gua/MapServer/5`<br>`Aterro_Sanit%C3%A1rio/MapServer/8` | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. Sem campo muni nativo (filtrar por bbox). |
| **SNIS** | Federal | Download | `https://www.gov.br/cidades/pt-br/acesso-a-informacao/dados-abertos/snis` | Arquivos tabulares de indicadores de água e esgoto | N/A | Pública / Open Data | 29/06/2026 | Apenas Download (Sem API geoespacial OGC pública) |
| **COPASA-MG** | Estadual | Download | `https://www.copasa.com.br/` | Relatórios e visualizadores corporativos | N/A | Restrita / Corporativa | 29/06/2026 | Não Confirmado (Sem geoserver WFS público estruturado) |

## Integração no GisBR
- **Cobertura Atual:** Nenhuma.
- **Próximos Passos:**
  - Desenvolver conector para bases ArcGIS REST da ANA para ingestão da Base Hidrográfica Otorgada (BHO).
  - Integrar limites de bacias hidrográficas da CPRM via WFS.
- **Validação no QGIS (a validar):** Configurar o ArcGIS REST Server na URL da ANA no QGIS e adicionar a camada da BHO correspondente ao município.
