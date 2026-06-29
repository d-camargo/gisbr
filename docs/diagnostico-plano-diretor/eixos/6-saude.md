# Eixo 6: Saúde

Este eixo mapeia a distribuição dos estabelecimentos de saúde (hospitais, postos de saúde, UPAs) e as regiões de saúde. Permite calcular indicadores de acessibilidade e vazios de cobertura assistencial para subsidiar as propostas de melhoria de serviços de saúde no Plano Diretor.

## Catálogo de Geoservers e Serviços

| Fonte / Órgão | Nível | Serviço | Endpoint / URL | Camadas Principais / Algoritmos | CRS | Licença | Data de Acesso | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **GisBR (CNES)** | Federal | Local (PyQGIS) | Integrado ao plugin | `read_health_facilities` (Geolocalização de estabelecimentos de saúde com base no CNES/DATASUS) | EPSG:4674 | GPL-3.0 | 29/06/2026 | **Coberto pelo GisBR** (Fase 1 e Fase 2) |
| **GisBR (MS)** | Federal | Local (PyQGIS) | Integrado ao plugin | `read_health_region` (Polígonos das Regiões de Saúde definidas pelo Ministério da Saúde) | EPSG:4674 | GPL-3.0 | 29/06/2026 | **Coberto pelo GisBR** (Fase 1 e Fase 2) |
| **DATASUS / CNES** | Federal | Download / SOAP | `ftp://ftp.datasus.gov.br/dissemin/publicos/` | Microdados do CNES, SIH, SIA, SINAN, etc. | N/A | Pública / Open Data | 29/06/2026 | Apenas Download / SOAP (Sem Geoserver OGC WFS público centralizado) |
| **Ministério da Saúde** | Federal | Download | `https://dadosabertos.saude.gov.br` | Conjuntos de dados tabulares de programas de saúde | N/A | Pública / Open Data | 29/06/2026 | Apenas Download (Sem API geoespacial OGC pública) |

## Integração no GisBR
- **Cobertura Atual: Alta.** O GisBR já conta com os algoritmos `gisbr:read_health_facilities` e `gisbr:read_health_region` (nas Fases 1 & 2), que extraem os pontos de estabelecimentos e limites de regiões de saúde a partir das bases consolidadas pelo IPEA/geobr.
- **Próximos Passos:** Não requer novos conectores. O foco é aplicar análises de rede e cálculo de densidade (Kernel Density) sobre os pontos de saúde obtidos localmente.
