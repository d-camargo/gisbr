# Eixo 3: Demografia

Este eixo reúne os dados de população, domicílios, renda e a malha territorial estatística básica. É o pilar que sustenta as análises espaciais de densidade urbana, crescimento demográfico e vulnerabilidade social para o Plano Diretor.

## Catálogo de Geoservers e Serviços

| Fonte / Órgão | Nível | Serviço | Endpoint / URL | Camadas Principais / Algoritmos | CRS | Licença | Data de Acesso | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **GisBR (geobr)** | Federal | Local (PyQGIS) | Integrado ao plugin | `read_census_tract` (Setores Censitários)<br>`read_weighting_area` (Áreas de Ponderação) | EPSG:4674 | GPL-3.0 | 29/06/2026 | **Coberto pelo GisBR** (Fase 1 e Fase 2) |
| **GisBR (censobr)** | Federal | Local (PyQGIS) | Integrado ao plugin | `join_censo` (Integração com dados tabulares do Censo por `code_tract`) | EPSG:4674 | GPL-3.0 | 29/06/2026 | **Coberto pelo GisBR** (Fase 2) |
| **IBGE SIDRA** | Federal | REST API | `https://apisidra.ibge.gov.br` | Consultas dinâmicas a tabelas do Censo (População, Domicílios, Renda) | N/A | Pública / Open Data | 29/06/2026 | Online - API REST funcional |
| **IBGE BDiA** | Federal | Mapas / WMS | `https://bdiaweb.ibge.gov.br` | Mapas de síntese socioeconômica e ambiental | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities consultável via INDE |

## Integração no GisBR
- **Cobertura Atual: Alta.** As Fases 1 e 2 do plugin já implementam o download nativo dos setores censitários (`read_census_tract_v2`) e o algoritmo `join_censo` para unificar geometrias com os microdados demográficos do `censobr` de forma local e eficiente (usando post-load e Post-processing).
- **Próximos Passos:** Não há necessidade de novos conectores. O esforço é focado em guias de uso no QGIS para criação automática de mapas coropléticos com base no `join_censo`.
