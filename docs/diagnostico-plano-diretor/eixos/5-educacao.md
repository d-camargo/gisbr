# Eixo 5: Educação

Este eixo foca na distribuição geográfica das escolas e demais infraestruturas de ensino públicas e privadas, permitindo calcular o raio de atendimento e cobertura educacional para subsidiar as diretrizes de expansão de equipamentos comunitários no Plano Diretor.

## Catálogo de Geoservers e Serviços

| Fonte / Órgão | Nível | Serviço | Endpoint / URL | Camadas Principais / Algoritmos | CRS | Licença | Data de Acesso | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **GisBR (INEP)** | Federal | Local (PyQGIS) | Integrado ao plugin | `read_schools` (Geolocalização de escolas com base no Censo Escolar/INEP) | EPSG:4674 | GPL-3.0 | 29/06/2026 | **Coberto pelo GisBR** (Fase 1 e Fase 2) |
| **IBGE** (BC250) | Federal | WFS | `https://opendata.sgb.gov.br/geoserver/ows?service=WFS&version=1.1.0&request=GetCapabilities` | `p3m:vw_ibge_escolas` or similar | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado |
| **INEP** | Federal | Download | `https://www.gov.br/inep/pt-br` | Microdados do Censo Escolar (matrículas, docentes, infraestrutura) | N/A | Pública / Open Data | 29/06/2026 | Apenas Download (Sem Geoserver OGC WFS público centralizado) |

## Integração no GisBR
- **Cobertura Atual: Alta.** O GisBR já conta com o algoritmo `gisbr:read_schools` na Fase 1 (e sua respectiva versão v2 na Fase 2), que extrai os pontos de escolas a partir dos microdados oficiais espacializados pelo IPEA/geobr.
- **Próximos Passos:** Não requer novos conectores. O esforço é focado no desenvolvimento de relatórios e buffers de área de influência espacial (Service Area) ao redor das escolas obtidas.
