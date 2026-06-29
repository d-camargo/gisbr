# Panorama de Portais de Dados Abertos

Levantamento dos principais agregadores e geoservers oficiais para obtenção de dados geoespaciais voltados ao diagnóstico de cidades.

| Portal / Sistema | Nível | Tipo de Serviço | Link (URL) | Status (Data de Acesso) | Observações |
| --- | --- | --- | --- | --- | --- |
| **INDE** (Infra. Nacional de Dados Espaciais) | Federal | WMS, WFS, CSW | [https://inde.gov.br/](https://inde.gov.br/) | Online (29/06/2026) | Agregador nacional. Muito completo, mas as camadas dependem dos nós fornecedores estarem no ar. |
| **BDGEx** (Banco de Dados Geográficos do Exército) | Federal | WMS, WMTS, Download | [https://bdgex.eb.mil.br/](https://bdgex.eb.mil.br/) | Online (29/06/2026) | WMS via `bdgex.eb.mil.br/mapcache`. Download de algumas cartas exige login. |
| **Dados.gov.br** | Federal | REST (CKAN), Download | [https://dados.gov.br/](https://dados.gov.br/) | Online (29/06/2026) | Busca textual por datasets abertos do governo federal, aponta para endpoints originais. |
| **IBGE SIDRA** | Federal | REST API, Tabelas | [https://sidra.ibge.gov.br/](https://sidra.ibge.gov.br/) | Online (29/06/2026) | Base tabular principal para demografia e economia. Integrável via API. |
| **IBGE BDiA** (Banco de Inf. Ambientais) | Federal | WMS, Mapas | [https://bdiaweb.ibge.gov.br/](https://bdiaweb.ibge.gov.br/) | Online (29/06/2026) | Mapas interativos focados em biomas, geomorfologia, pedologia e vegetação. |
| **Geociências IBGE** | Federal | WFS, WMS, Download | [https://geoftp.ibge.gov.br/](https://geoftp.ibge.gov.br/) | Online (29/06/2026) | Fonte primária do pacote geobr (IPEA). |
| **IDE-Sisema (MG)** | Estadual (MG) | WFS, WMS | [http://idesisema.meioambiente.mg.gov.br/](http://idesisema.meioambiente.mg.gov.br/) | Online (29/06/2026) | Fonte oficial primária para meio ambiente, recursos hídricos e geologia em Minas Gerais. |
| **IEDE (FJP - MG)** | Estadual (MG) | WFS, Mapas | [https://fjp.mg.gov.br](https://fjp.mg.gov.br) | Online (29/06/2026) | Gerida pela Fundação João Pinheiro, focada em limites municipais e planejamento territorial de MG. |

*Nota: Alguns serviços que disponibilizam apenas catálogos (sem WFS estruturado) exigirão fallback para downloads assíncronos.*
