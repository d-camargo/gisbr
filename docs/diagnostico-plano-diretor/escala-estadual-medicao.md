# Medição da Escala Estadual, Regional e Fontes de IDEs Estaduais

Documento de medição empírica e registro técnico para a integração de recortes em escala estadual (**Estado / UF**), regional (**Microrregião**, **Mesorregião** e **Macrorregião / Grande Região**) e fontes de Infraestruturas de Dados Espaciais (IDEs) estaduais no plugin **GisBR**.

- **Data da medição:** 2026-09-30
- **Ambiente de teste:** Linux VPS (curl real, Python 3.12 / OGC GetCapabilities e ArcGIS REST)
- **Status da documentação:** Notas técnicas internas (pasta `docs/diagnostico-plano-diretor/` em `exclude_docs`, não publicada no site)

---

## 1. M1 — INDE (`visualizador.inde.gov.br`)

### 1.1. Arquitetura do Catálogo Nacional
- **URL testada:** `https://visualizador.inde.gov.br` (Data: 2026-09-30)
- O visualizador é uma aplicação ASP.NET. O catálogo de **nós** vem de:
  - `GET https://visualizador.inde.gov.br/api/buscacamada` (JSON de 26 KB, 79 nós cadastrados). Cada nó possui os campos `url` (WMS), `url_wfs` e `nivel_no` (*Nacional*, *Subnacional*, *Governo local*, *Academia*).
  - A árvore completa de camadas vem de `GET https://visualizador.inde.gov.br/api/montamenu` (JSON de 1,47 MB).
- **Papel na arquitetura:** O INDE opera como catálogo de **descoberta**, e **não** como fonte de runtime centralizada para dados estaduais. Ele apenas aponta para os servidores e serviços de cada órgão estadual ou municipal.
- **Catálogo CSW:** `https://metadados.inde.gov.br/geonetwork/srv/por/csw` (GeoNetwork 2.0.2), indexando 66.141 registros de metadados.

### 1.2. GeoServer Próprio do INDE
- **URL testada:** `https://geoservicos.inde.gov.br/geoserver/ows` (Data: 2026-09-30)
- Disponibiliza 5.005 `FeatureType`s distribuídos em 35 workspaces (ex.: INEA com 4.249 camadas, ICMBio com 85).
- O único workspace estadual expressivo hospedado diretamente na infraestrutura do INDE é o **INEA (Rio de Janeiro)**.
- Parâmetros `outputFormat=application/json` e `CQL_FILTER` funcionam normalmente:
  - Exemplo medido: `UF='MG'` na camada `BNDES:CNAES_por_Municipio_2012` retorna 837 registros com sucesso.

### 1.3. Nós Estaduais (*Subnacional*), Testados com GetCapabilities (2026-09-30)

| Nó Estadual | Serviço Avaliado | Status / Retorno | Detalhes Técnicos |
|---|---|---|---|
| **ES GEOBASES** | `https://ide.geobases.es.gov.br/geoserver/ows` | WFS, 672 tipos | WFS ativo e funcional |
| **MG Sisema** | `https://geoserver.meioambiente.mg.gov.br/ows/` | WFS, 1.421 tipos | WFS ativo (`IDE:ide_*`), TLS válido |
| **SP IDEA** | `https://datageo.ambiente.sp.gov.br/geoserver/ows` | "WFS disabled" | WFS global desabilitado nos workspaces |
| **SP Emplasa** | `http://ide.emplasa.sp.gov.br/geoserver/ows` | WFS, 2.146 tipos, **só HTTP** | Inviável em produção por falta de HTTPS |
| **MG FJP** | `https://geoserver.fjp.mg.gov.br` | **HTTP 403** | Acesso negado / bloqueio WAF |
| **RS IEDE** | `https://iede.rs.gov.br/geoserver/wms` | só WMS | Sem serviço WFS ativo no nó GeoServer |
| **RJ INEA** | `https://geoservicos.inde.gov.br/geoserver/ows` (via INDE) | WFS, 4.249 tipos | Hospedado no GeoServer do INDE |
| **MG PRODEMGE** | `http://geoserver.prodemge.gov.br/...` | WFS, 44 tipos, só HTTP | Apenas HTTP simples |
| **CE SEMA** | `https://pedea.sema.ce.gov.br/geoserver/inde/ows` | WFS, 145 tipos | WFS ativo e funcional |
| **CE SEMACE** | `https://geo.semace.ce.gov.br/geoserver/ows` | WFS, 5 tipos | Catálogo restrito |
| **AL SEPLAG** | `http://dados.seplag.al.gov.br/...` | Sem resposta | Timeout de conexão |
| **TO SEPLAN** | `https://geoportal.to.gov.br/geoserver/ows` | WFS, 1.267 tipos | WFS ativo e funcional |
| **RO TCE** | `https://geo.tce.ro.gov.br/geoserver/ows` | WFS, 3 tipos | Catálogo restrito |
| **DF** | `https://geoservicos.ide.df.gov.br/wms` | só WMS | Nó GeoServer restrito a visualização |

---

## 2. M2 — As Oito IDEs Estaduais Indicadas

Avaliação técnica detalhada dos portais e serviços geográficos reais dos oito estados priorizados (Medição em 2026-09-30):

| UF | Portal → Serviço Real | Veredito | Observações Técnicas |
|---|---|---|---|
| **MG** | `https://geoserver.meioambiente.mg.gov.br/IDE/wfs` | **VIÁVEL WFS** | 1.421 FeatureTypes (`IDE:ide_*`), certificado TLS válido (Let's Encrypt / ISRG Root X1). `CQL_FILTER` e filtragem por `bbox` plenamente funcionais. Atributo com código/nome do município varia conforme a camada (`geocodigo`, `nome_municipio`, etc.). |
| **SP** | IDE-SP (`https://idesp.sp.gov.br`): **só WMS** (WFS desligado globalmente). Vetores disponíveis via `https://datageo.ambiente.sp.gov.br/geoserver/datageo/<CAMADA>/wfs`, **por camada**, exigindo `version=1.1.0` e `typeName` sem prefixo de workspace | **VIÁVEL com ressalva** | Não permite listar catálogo WFS completo via GetCapabilities raiz; viável apenas com lista fixa declarativa. Teste: camada `VWM_AREA_RISCO_INUNDACAO_IG_2014_POL` = 776 feições, GeoJSON retornado com sucesso. |
| **PR** | `https://geopr.iat.pr.gov.br/server/rest/services` (ArcGIS 11.5) | **VIÁVEL ArcGIS** | 957 FeatureServers na pasta `00_PUBLICACOES`. `maxRecordCount = 2000`, latência medida entre 0,2 s e 30 s, TLS Sectigo. O formato `f=geojson` emite a propriedade `exceededTransferLimit = true` quando ultrapassa o limite. |
| **RS** | `https://iede.rs.gov.br/server/rest/services` (ArcGIS 12.1) | **VIÁVEL ArcGIS** | Cerca de 1.150 datasets disponíveis. Zoneamento de Plano Diretor disponível apenas para municípios sob jurisdição da METROPLAN (um serviço dedicado por município, não agregado estadual). |
| **BA** | `https://map.geo.sei.ba.gov.br/arcgis/rest/services` (ArcGIS 11.4) | **VIÁVEL ArcGIS** | Cartografia sistemática SEI (escalas 1:25k, 1:50k e 1:100k). O endpoint WFS Esri ignora `CQL_FILTER`. Hosts ambientais do INEMA (`inema.ba.gov.br`) e GeoBahia (`geobahia.ba.gov.br`) falham em TLS/SNI, tornando os dados ambientais estaduais **inviáveis**. |
| **DF** | `https://www.geoservicos.ide.df.gov.br/arcgis/rest/services` (ArcGIS 10.71) | **VIÁVEL ArcGIS** | O domínio `ide.df.gov.br` sem o prefixo `www` não resolve DNS. `maxRecordCount = 1000`. Camadas de PDOT, Macrozoneamento, Limites e Equipamentos Urbanos (LUOS) disponíveis. |
| **GO** | `https://siga.meioambiente.go.gov.br/geoserver/ows` (GeoNode) | **VIÁVEL WFS** | 136 FeatureTypes `geonode:*`, TLS emitido por ISRG Root X1. O portal legado SIEG (`sieg.go.gov.br`) está com **certificado SSL expirado e não responde**: inviável. |
| **SC** | `https://sigsc.sc.gov.br/sigserver/SIGSC/wfs` | **VIÁVEL, mas raso** | Apenas 23 tipos: limites territoriais, sedes municipais e hidrografia (que duplica ANA/IBGE). **Fica de fora nesta rodada.** |

---

## 3. M3 — Divisão Regional do IBGE (Composição Município → Região)

- **URL testada:** `https://servicodados.ibge.gov.br/api/v1/localidades/municipios` (Data: 2026-09-30)
- **Volume:** Resposta JSON de 2,4 MB contendo 5.571 municípios brasileiros.
- **Hierarquia:** Cada item da API estrutura o encadeamento:
  `município → microrregião → mesorregião → UF → região (macro)` (além de `região-imediata` e `região-intermediária`).
- **Abordagem offline:** Uma única requisição extrai toda a árvore de composição regional brasileira, que é compilada em CSV embarcado (`gisbr/core/data/divisao_regional.csv`), eliminando requisições em tempo de execução.
- **Totais de entidades territoriais identificadas:**
  - **137** mesorregiões
  - **558** microrregiões
  - **5** Grandes Regiões (denominadas correntemente como *Macrorregiões*: Norte, Nordeste, Sudeste, Sul, Centro-Oeste)
  - *Adicional (divisão 2017):* 133 regiões geográficas intermediárias e 510 regiões geográficas imediatas.
- **Avaliação de polígonos no WFS do IBGE:**
  - O IBGE disponibiliza camadas agregadas em `https://geoservicos.ibge.gov.br/geoserver/ows` (`CGMAT:qg_2025_170_mesoreg_agreg`, `CGMAT:qg_2025_180_microreg_agreg`, `CGMAT:qg_2025_020_uf_agreg`, `CGMAT:qg_2025_010_grandreg_agreg`).
  - **Decisão:** Essas geometrias agregadas **não** serão consumidas em runtime. A fronteira vetorial do recorte agregado continua sendo gerada a partir da malha de municípios oficiais do geobr (com `native:dissolve` nas escalas UF e Macro), garantindo alinhamento topológico exato com as demais camadas do projeto.

---

## 4. M4 — Volume das Fontes Atuais em Escala Estadual

Medições realizadas tendo o estado de **Minas Gerais (MG)** como caso de maior estresse (853 municípios, 586.522 km²) e **Sergipe (SE)** como caso estadual compacto (75 municípios). Contagens brutas levantadas via BBOX (incluindo sobreposição com UFs vizinhas).

### 4.1. Tamanho e Contagem das Fontes Existentes em MG (2026-09-30)

| Fonte / ID | Volume / Contagem em MG | Observações Técnicas |
|---|---|---|
| `sicar_imoveis` | 1.179.185 feições (~1,15 GB) | **Servidor WFS trunca silenciosamente em 10.000 feições sem aviso** |
| `sgb_rios` | 187.000 feições (~200 MB) | Requisição de contagem (hits) leva mais de 14 segundos |
| `ibge_bc250_drenagem` | 182.000 feições (~245 MB) | Volume impraticável para carga síncrona na UF |
| `ibge_bdia_pedologia` | ~231 MB | Camada temática contínua de solos muito densa |
| `ibge_bdia_geologia` | ~125 MB | Volume elevado em escala estadual |
| `ibge_bdia_geomorfologia` | ~91 MB | Polígonos complexos em escala estadual |
| `anm_sigmine` | 95.000 feições | Servidor ArcGIS impõe `maxRecordCount = 5000` e não pagina GeoJSON |
| `ibama_autos` | 38.000 feições (~120 MB) | Servidor ArcGIS impõe `maxRecordCount = 2000` |
| `ibge_bdia_vegetacao` | ~53 MB | Volume intermediário |
| `dnit_snv` | ~47 MB | Malha federal de rodovias em MG |
| `ibge_bc250_rodovias` | ~46 MB | Malha estadual/federal 1:250k |
| `der_mg_rodovias` | ~69 MB | Rodovias estaduais de MG |
| `ibge_areas_urbanizadas` | ~28 MB | Polígonos de manchas urbanizadas |
| `sgb_pocos_siagas` | 61.000 pontos (~25 MB) | Pontos de captação subterrânea |
| `sgb_bacias` | ~26 MB | Delimitação de bacias hidrográficas |
| `sgb_risco` | ~13 MB | Setores de risco geológico CPRM |
| `icmbio_uc` | ~6 MB | Unidades de Conservação federais |

*Demais fontes existentes:* Tamanho de resposta de 5 MB ou inferior em MG.

### 4.2. Filtros por UF Medidos (Substituição de `IN (853 códigos)` em GET)

Para evitar strings de consulta GET excedendo limites de URI (8 KB) ao consultar centenas de municípios, foram testadas expressões de filtragem direta por UF:

| Fonte | Filtro Testado | Resultado Medido (2026-09-30) |
|---|---|---|
| `minfra_ferrovias` | `uf='MG'` | 423 feições retornadas |
| `icmbio_embargos` | `uf='MG'` | 854 feições retornadas |
| `ibge_areas_urbanizadas` | `cd_mun LIKE '31%'` | 14.858 feições em 0,24 s |
| `ibge_aglomerados_subnormais` | `cd_geocodm LIKE '31%'` | 372 feições retornadas |

### 4.3. Comportamento do geobr e OSM na Escala da UF
- **geobr vetorial:** O arquivo de setores censitários (`census_tract`) de MG possui 79 MB na versão simplificada; `weighting_area` e `municipality` são nativamente particionados por UF no repositório IPEA. Camadas pontuais como `schools` (101 MB) e `health_facilities` (191 MB) já são baixadas nacionalmente pelo conector legado e recortadas localmente.
- **OpenStreetMap (Overpass API):** Inviável para Estado ou Macrorregião. A extração da malha viária ou de POIs de uma UF inteira resulta em dezenas de milhões de elementos OSM, estourando imediatamente os limites de memória e o timeout de 60 segundos do servidor Overpass. O OSM permanece restrito ao recorte municipal.

---

## 5. D4 — Tabela de Classificação por Escala Máxima (`escala_max`)

Para prevenir travamentos do QGIS, esgotamento de memória e downloads corrompidos por truncamento de servidores em recortes ampliados, cada fonte do catálogo `SOURCES` recebe a declaração da chave obrigatória `"escala_max"`.

### 5.1. Critérios de Enquadramento
- **Hierarquia de escalas:** `municipio = 0`, `regional = 2` (abrange Microrregião, RM e Mesorregião), `estado = 3`, `macrorregiao = 4`.
- **Corte para `regional` (desabilitada em Estado e Macrorregião):** Fontes que excedem ~90 MB ou 100.000 feições em MG; servidores que truncam o retorno sem suporte a paginação no conector; rasters COG estaduais massivos (`mapbiomas_cobertura` a 30 m em MG gera ~650 milhões de pixels); e tabelas agregadas do SIDRA com lote de 853 municípios em requisição GET não homologada.
- **Corte para `estado` (desabilitada em Macrorregião):** Fontes que excedem ~20 MB em MG ou operam sob servidores ArcGIS com `maxRecordCount` reduzido.

### 5.2. Classificação Completa das Fontes

| `escala_max` | Fontes Abrangidas |
|---|---|
| **`municipio`** | `osm_vias`, `osm_pois` |
| **`regional`** | `sicar_imoveis`, `sgb_rios`, `ibge_bc250_drenagem`, `ibge_bdia_pedologia`, `ibge_bdia_geologia`, `ibge_bdia_geomorfologia`, `anm_sigmine`, os quatro pacotes `anm_sigmine_*` (`zip_remoto`), `ibama_autos`, `mapbiomas_cobertura`, `ibge_pam_temporarias`, `ibge_pam_permanentes`, `ibge_censo_agro` |
| **`estado`** | `dnit_snv`, `der_mg_rodovias`, `ibge_bc250_rodovias`, `ibge_bdia_vegetacao`, `sgb_pocos_siagas`, `sgb_risco`, `sgb_bacias`, `ibge_areas_urbanizadas`, `ana_hidrografia`, `geobr_setores`, `geobr_bairros`, `geobr_favelas`, `geobr_locais_votacao`, `incra_sigef_parcelas` |
| **`macrorregiao`** | `minfra_ferrovias`, `icmbio_embargos`, `icmbio_uc`, `ibge_bc250_ferrovias`, `ibge_bc250_massa_dagua`, `ibge_bc250_area_densa`, `ibge_aglomerados_subnormais`, `ibama_esgoto`, `ibama_agua`, `ibama_aterro`, `geobr_municipio`, `geobr_ponderacao`, `geobr_escolas`, `geobr_saude`, `geobr_biomas`, `geobr_ucs`, `geobr_terras_indigenas`, `geobr_risco`, `geobr_mancha_urbana`, `geobr_sede`, `geobr_quilombolas`, `basemap_satelite` |

---

## 6. D10 — Fontes Estaduais e Avaliação de Candidatas

### 6.1. Fontes Avaliadas que Ficaram de Fora (com Justificativa Técnica)

Durante a varredura das IDEs estaduais em 2026-09-30, diversas fontes foram avaliadas e explicitamente **excluídas** desta rodada pelos seguintes motivos:

1. **Bahia (BA — SEI / INEMA):**
   - Apenas a cartografia sistemática da SEI estava disponível via ArcGIS REST, a qual duplica as bases cartográficas já providas pelo IBGE.
   - Os servidores ambientais do INEMA (`inema.ba.gov.br`) e do portal GeoBahia (`geobahia.ba.gov.br`) falham sistematicamente no handshake TLS/SNI, impossibilitando conexões HTTPS seguras nativas pelo QGIS.
2. **Santa Catarina (SC — SIGSC):**
   - O WFS `https://sigsc.sc.gov.br/sigserver/SIGSC/wfs` conta com apenas 23 camadas, limitadas a divisões político-administrativas e hidrografia redundante com ANA e IBGE.
3. **São Paulo (SP — IDE-SP):**
   - O geoportal principal (`idesp.sp.gov.br`) desabilitou os serviços WFS em seus workspaces, servindo estritamente WMS (raster de visualização sem vetor).
4. **São Paulo (SP — Emplasa):**
   - O GeoServer (`http://ide.emplasa.sp.gov.br/geoserver/ows`), apesar de possuir 2.146 tipos, opera exclusivamente sobre HTTP sem suporte a HTTPS/TLS.
5. **Goiás (GO — SIEG):**
   - O servidor legado do SIEG (`sieg.go.gov.br`) encontra-se com certificado SSL expirado e não responde a conexões HTTP/HTTPS.
6. **Rio Grande do Sul (RS — Zoneamento METROPLAN):**
   - O zoneamento urbano dos Planos Diretores municipais está distribuído em FeatureServers individuais (um serviço isolado por município), o que não se enquadra na arquitetura atual de catálogo unificado por fonte.
7. **Paraná (PR — `pr_app_fbds`, Lote B reprovado em medição):**
   - A query espacial por bbox municipal (Curitiba) no `fbds_app/FeatureServer` falha com `Error performing query operation` / `Wait timeout for the request exceeded` (29–61 s; a única resposta parcial levou 83 s, acima do timeout de transporte de 60 s da NAM do QGIS). Detalhes na seção 6.4.

### 6.2. Candidatas Selecionadas para Integração

Para os lotes de fontes estaduais implementados nos passos seguintes, foram homologadas camadas específicas com protocolos existentes (`wfs` e `arcgis`):

- **Lote A (GeoServer WFS):**
  - **MG (Sisema):** `mg_areas_urbanizadas`, `mg_uc_estaduais`, `mg_uc_municipais`, `mg_ete`, `mg_outorgas`, `mg_risco_erosao` (`https://geoserver.meioambiente.mg.gov.br/IDE/wfs`).
  - **GO (Siga/GeoNode):** `go_malha_viaria`, `go_aterros`, `go_captacoes`, `go_uc_estaduais`, `go_suscet_deslizamento` (`https://siga.meioambiente.go.gov.br/geoserver/ows`).
  - **SP (DataGeo):** `sp_risco_inundacao` (`https://datageo.ambiente.sp.gov.br/geoserver/datageo/VWM_AREA_RISCO_INUNDACAO_IG_2014_POL/wfs`).
- **Lote B (ArcGIS REST):**
  - **DF (GeoServiços IDE-DF):** `df_pdot_zoneamento`, `df_pdot_macrozoneamento`, `df_regioes_administrativas`, `df_escolas_publicas` (`https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/...`).
  - **RS (IEDE / SEDUR):** `rs_areas_urbanizadas`, `rs_suscet_inundacao`, `rs_suscet_mov_massa` (`https://iede.rs.gov.br/server/rest/services/SEDUR/...`).
  - **PR (IAT GeoPR):** `pr_uc_estaduais`, `pr_rodovias_der`, `pr_app_fbds` (`https://geopr.iat.pr.gov.br/server/rest/services/00_PUBLICACOES/...`).

### 6.3. Medição Empírica e Vereditos do Lote A (GeoServer WFS — D10)

Para cada uma das 12 candidatas do Lote A, foram executadas as três verificações obrigatórias do **D10**:
1. **Bbox municipal:** requisição GetFeature com a BBOX de um município da respectiva UF (`wfs.build_url` com CRS EPSG:4674 e GeoJSON), confirmando recebimento de feições válidas;
2. **Contagem total na UF (hits):** requisição `resultType=hits` para apurar a contagem total no estado e definir `escala_max` segundo o critério D4 (limiar de 90 MB ou truncamento sem paginação = `regional`; caso contrário = `estado`);
3. **Verificação TLS:** confirmação de que `python3 tools/check_sources_tls.py` não aponta `FALTA` (cadeias TLS válidas e suportadas).

#### Tabela de Medição do Lote A (Medido em 2026-09-30)

| ID / Fonte | UF | Eixo | TypeName | BBOX Teste (Município) | Contagem BBOX (tempo) | Total UF / Hits (tempo) | Volume / Comportamento UF | TLS Anchor | `escala_max` | Veredito D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| `mg_areas_urbanizadas` | MG | Urbano | `IDE:ide_1401_mg_areas_urbanizadas_2022_pol` | Belo Horizonte | 349 feats (0,18 s) | 20.737 feats (0,06 s) | ~35 MB, sem truncamento (2,5 s) | ISRG Root X1 [OK] | `estado` | **Aprovada** |
| `mg_uc_estaduais` | MG | Ambiental | `IDE:ide_2010_mg_unidades_conservacao_estaduais_pol` | Belo Horizonte | 6 feats (0,13 s) | 95 feats (0,06 s) | ~8 MB, sem truncamento | ISRG Root X1 [OK] | `estado` | **Aprovada** |
| `mg_uc_municipais` | MG | Ambiental | `IDE:ide_2010_mg_unidades_conservacao_municipais_pol` | Belo Horizonte | 10 feats (0,10 s) | 195 feats (0,06 s) | ~3 MB, sem truncamento | ISRG Root X1 [OK] | `estado` | **Aprovada** |
| `mg_ete` | MG | Saneamento | `IDE:ide_0603_mg_ete_pto` | Belo Horizonte | 9 feats (0,10 s) | 416 feats (0,06 s) | < 1 MB, pontos | ISRG Root X1 [OK] | `estado` | **Aprovada** |
| `mg_outorgas` | MG | Saneamento | `IDE:ide_2103_mg_outorgas_uso_recursos_hidricos_pto` | Belo Horizonte | 1.211 feats (0,54 s) | 58.741 feats (0,45 s) | 145,4 MB (19,17 s; excede 90 MB) | ISRG Root X1 [OK] | `regional` | **Aprovada** |
| `mg_risco_erosao` | MG | Ambiental | `IDE:ide_1705_mg_risco_erosao_pol` | Belo Horizonte | 3 feats (0,16 s) | 1.293 feats (0,06 s) | ~18 MB | ISRG Root X1 [OK] | `estado` | **Aprovada** |
| `go_malha_viaria` | GO | Transportes | `geonode:malha_viaria_2024` | Goiânia | 40 feats (0,29 s) | 1.845 feats (0,15 s) | ~12 MB | ISRG Root X1 [OK] | `estado` | **Aprovada** |
| `go_aterros` | GO | Saneamento | `geonode:aterro_sanitario` | Goiânia | 3 feats (0,13 s) | 254 feats (0,13 s) | < 1 MB | ISRG Root X1 [OK] | `estado` | **Aprovada** |
| `go_captacoes` | GO | Saneamento | `geonode:GO_Captacoes_Saneago` | Goiânia | 5 feats (0,13 s) | 183 feats (0,13 s) | < 1 MB | ISRG Root X1 [OK] | `estado` | **Aprovada** |
| `go_uc_estaduais` | GO | Ambiental | `geonode:ceuc_estadual` | Goiânia | 4 feats (0,17 s) | 27 feats (0,17 s) | ~1,5 MB | ISRG Root X1 [OK] | `estado` | **Aprovada** |
| `go_suscet_deslizamento` | GO | Ambiental | `geonode:suscet_desliz3` | Goiânia | 127 feats (0,35 s) | 31.619 feats (0,13 s) | ~43,6 MB, sem truncamento (2,07 s) | ISRG Root X1 [OK] | `estado` | **Aprovada** |
| `sp_risco_inundacao` | SP | Ambiental | `VWM_AREA_RISCO_INUNDACAO_IG_2014_POL` | Pindamonhangaba | 94 feats (0,14 s) | 776 feats (0,05 s) | ~950 KB | DigiCert Global Root G2 [OK] | `estado` | **Aprovada** |

#### Detalhes Técnicos e URLs das Candidatas

- **MG — Sisema (`https://geoserver.meioambiente.mg.gov.br/IDE/wfs`):**
  - `mg_areas_urbanizadas`: `https://geoserver.meioambiente.mg.gov.br/IDE/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=IDE:ide_1401_mg_areas_urbanizadas_2022_pol&srsName=EPSG:4674&outputFormat=application/json&bbox=-44.063,-20.06,-43.857,-19.767,EPSG:4674`
  - `mg_uc_estaduais`: `https://geoserver.meioambiente.mg.gov.br/IDE/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=IDE:ide_2010_mg_unidades_conservacao_estaduais_pol&srsName=EPSG:4674&outputFormat=application/json&bbox=-44.063,-20.06,-43.857,-19.767,EPSG:4674`
  - `mg_uc_municipais`: `https://geoserver.meioambiente.mg.gov.br/IDE/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=IDE:ide_2010_mg_unidades_conservacao_municipais_pol&srsName=EPSG:4674&outputFormat=application/json&bbox=-44.063,-20.06,-43.857,-19.767,EPSG:4674`
  - `mg_ete`: `https://geoserver.meioambiente.mg.gov.br/IDE/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=IDE:ide_0603_mg_ete_pto&srsName=EPSG:4674&outputFormat=application/json&bbox=-44.063,-20.06,-43.857,-19.767,EPSG:4674`
  - `mg_outorgas`: `https://geoserver.meioambiente.mg.gov.br/IDE/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=IDE:ide_2103_mg_outorgas_uso_recursos_hidricos_pto&srsName=EPSG:4674&outputFormat=application/json&bbox=-44.063,-20.06,-43.857,-19.767,EPSG:4674`. Com 58.741 feições totalizando 145,4 MB, ultrapassa o corte de 90 MB do D4, recebendo a classificação `escala_max = "regional"`.
  - `mg_risco_erosao`: `https://geoserver.meioambiente.mg.gov.br/IDE/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=IDE:ide_1705_mg_risco_erosao_pol&srsName=EPSG:4674&outputFormat=application/json&bbox=-44.063,-20.06,-43.857,-19.767,EPSG:4674`

- **GO — Siga / GeoNode (`https://siga.meioambiente.go.gov.br/geoserver/ows`):**
  - `go_malha_viaria`: `https://siga.meioambiente.go.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=geonode:malha_viaria_2024&srsName=EPSG:4674&outputFormat=application/json&bbox=-49.42,-16.85,-49.12,-16.55,EPSG:4674`
  - `go_aterros`: `https://siga.meioambiente.go.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=geonode:aterro_sanitario&srsName=EPSG:4674&outputFormat=application/json&bbox=-49.42,-16.85,-49.12,-16.55,EPSG:4674`
  - `go_captacoes`: `https://siga.meioambiente.go.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=geonode:GO_Captacoes_Saneago&srsName=EPSG:4674&outputFormat=application/json&bbox=-49.42,-16.85,-49.12,-16.55,EPSG:4674`
  - `go_uc_estaduais`: `https://siga.meioambiente.go.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=geonode:ceuc_estadual&srsName=EPSG:4674&outputFormat=application/json&bbox=-49.42,-16.85,-49.12,-16.55,EPSG:4674`
  - `go_suscet_deslizamento`: `https://siga.meioambiente.go.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=geonode:suscet_desliz3&srsName=EPSG:4674&outputFormat=application/json&bbox=-49.42,-16.85,-49.12,-16.55,EPSG:4674`. 31.619 feições totalizando ~43,6 MB, baixado em 2,07 s sem truncamento pelo servidor; enquadrado em `escala_max = "estado"`.

- **SP — DataGeo (`https://datageo.ambiente.sp.gov.br/geoserver/datageo/VWM_AREA_RISCO_INUNDACAO_IG_2014_POL/wfs`):**
  - `sp_risco_inundacao`: `https://datageo.ambiente.sp.gov.br/geoserver/datageo/VWM_AREA_RISCO_INUNDACAO_IG_2014_POL/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=VWM_AREA_RISCO_INUNDACAO_IG_2014_POL&srsName=EPSG:4674&outputFormat=application/json&bbox=-45.58,-23.05,-45.35,-22.75,EPSG:4674`
  - *Nota sobre `wfs_version`:* Embora o levantamento preliminar do M2 tenha aventado a exigência de `version=1.1.0`, os testes empíricos demonstraram que o endpoint WFS dedicado da camada no DataGeo responde perfeitamente sob WFS 2.0.0 padrão (`typeNames=VWM_AREA_RISCO_INUNDACAO_IG_2014_POL`), retornando GeoJSON compatível com OGR (94 feições na BBOX de Pindamonhangaba e 776 feições no total da UF). Dessa forma, a camada opera nativamente sem necessidade de parâmetro especial `wfs_version` nem alteração em `_busca_camada`.

### 6.4. Medição Empírica e Vereditos do Lote B (ArcGIS REST — D10)

Medido em 2026-09-30, mesmo método do Lote A: (1) query no formato exato do
conector (`arcgis_rest.build_url`: `/query?outFields=*&f=geojson&outSR=4674&where=1=1&geometry=…&geometryType=esriGeometryEnvelope&inSR=4674&spatialRel=esriSpatialRelIntersects`) com a bbox de um município da UF; (2) contagem total (`returnCountOnly`) contra o `maxRecordCount` do serviço; (3) `tools/check_sources_tls.py`.

#### Tabela de Medição do Lote B (2026-09-30)

| ID / Fonte | UF | Eixo | Serviço / Layer | BBOX Teste (Município) | Contagem BBOX (tempo) | Total UF (tempo) | maxRecordCount | `escala_max` | Veredito D10 |
|---|---|---|---|---|---|---|---|---|---|
| `df_pdot_zoneamento` | DF | Urbano | `Publico/PDOT/MapServer` layer 4 | DF (5300108) | 74 feats (0,70 s) | 78 (0,13 s) | 1.000 | `estado` | **Aprovada** |
| `df_pdot_macrozoneamento` | DF | Urbano | `Publico/PDOT/MapServer` layer 0 | DF | 3 feats (0,57 s) | 3 (0,12 s) | 1.000 | `estado` | **Aprovada** |
| `df_regioes_administrativas` | DF | Pol.-adm. | `Publico/LIMITES/FeatureServer` layer 1 | DF | 36 feats (0,91 s) | 37 (0,16 s) | 1.000 | `estado` | **Aprovada** |
| `df_escolas_publicas` | DF | Educação | `Publico/EQUIPAMENTOS_URBANOS/FeatureServer` layer 0 | DF | 691 feats (0,28 s) | 760 (0,12 s) | 1.000 | `estado` | **Aprovada** |
| `rs_areas_urbanizadas` | RS | Urbano | `SEDUR/pdvt_areas_urbanizadas_pol/FeatureServer` layer 0 | Arroio do Meio (4301008) | 248 feats (0,20 s) | 248 (0,11 s) | 3.000 | `estado` | **Aprovada** (com ressalva de cobertura, abaixo) |
| `rs_suscet_inundacao` | RS | Ambiental | `SEDUR/pdvt_suscetibilidade_inundacao/FeatureServer` layer 0 | Arroio do Meio | 21 feats | 21 (0,11 s) | 3.000 | `estado` | **Aprovada** (idem) |
| `rs_suscet_mov_massa` | RS | Ambiental | `SEDUR/pdvt_suscetibilidade_mov_massas/FeatureServer` layer 0 | Arroio do Meio | 28 feats | 28 (0,09 s) | 3.000 | `estado` | **Aprovada** (idem) |
| `pr_uc_estaduais` | PR | Ambiental | `00_PUBLICACOES/unidades_conservacao_estaduais/FeatureServer` layer 0 | Curitiba | 2 feats (1,42 s) | 74 (0,19 s) | 2.000 | `estado` | **Aprovada** |
| `pr_rodovias_der` | PR | Transportes | `00_PUBLICACOES/rodovias_der/FeatureServer` layer 0 | Curitiba | 47 feats (14,7 s) | 2.328 (0,11 s) | 2.000 | `regional` | **Aprovada** (total > maxRecordCount ⇒ regional, como previsto no plano) |
| `pr_app_fbds` | PR | Ambiental | `00_PUBLICACOES/fbds_app/FeatureServer` layer 0 | Curitiba | erro/timeout | 7.560 (37 s) | 2.000 | — | **REPROVADA** |

#### Notas do Lote B

- **CRS:** DF é nativo EPSG:31983 e PR (UC/DER) EPSG:31982; a saída com
  `outSR=4674` foi confirmada em graus (GeoJSON `crs: EPSG:4674`) nas duas UFs.
- **Cobertura real das camadas `pdvt_*` do RS (RESSALVA IMPORTANTE):** o
  levantamento M2 presumiu que os serviços `pdvt_*` da SEDUR cobrissem a região
  metropolitana de Porto Alegre. A medição mostrou o contrário: o `fullExtent`
  (-52,14..-51,73 / -29,63..-29,09) e os atributos (`nm_mun`, `cod_mun`)
  indicam a **bacia do Vale do Taquari** (ex.: Arroio do Meio, `cod_mun`
  4301008); a bbox de Porto Alegre devolve **0 feições**. As três entram mesmo
  assim porque passam nas verificações do D10 com um município da UF (Arroio do
  Meio); recortes fora do Vale devolvem 0 feições e a fonte é pulada com aviso
  ("sem feicoes"). O nome no catálogo registra a cobertura real: "… (PDVT Vale
  do Taquari)".
- **`pr_app_fbds` (reprovada):** a query espacial por bbox municipal falhou de
  duas formas em medições distintas — `Error: Error performing query operation`
  (29 s) e `Wait timeout for the request exceeded` (61 s); a única resposta
  parcial (300 feats) levou **83 s**, acima do timeout de transporte de 60 s da
  pilha de rede do QGIS (NAM). O total estadual (7.560) também excede o
  `maxRecordCount` (2.000). Fora do catálogo; volta quando houver paginação por
  faixa de `objectid` e um serviço que responda em tempo útil.
- **TLS (verificação 3):** `www.geoservicos.ide.df.gov.br` → ISRG Root X1 [OK];
  `iede.rs.gov.br` → DigiCert Global Root G2 [OK]; `geopr.iat.pr.gov.br` →
  USERTrust RSA Certification Authority [OK]. Nenhum PEM precisou entrar em
  `gisbr/core/certs/`.
- Latência do `pr_rodovias_der` na bbox municipal: 14,7 s — dentro do limite de
  60 s, mas anotado como o serviço mais lento do lote aprovado.

---

## 7. Sugestões de Dados para Próximas Rodadas

Com base nas limitações de infraestrutura identificadas no levantamento de 2026-09-30, registram-se as seguintes recomendações para expansão futura do plugin:

1. **Paginação WFS e ArcGIS nos conectores:**
   - A implementação de iteração por páginas (`startIndex` no WFS 2.0.0; `resultOffset` ou particionamento por faixas de `OBJECTID`/`ID` no ArcGIS REST) permitirá destravar em escala estadual bases cruciais hoje inviabilizadas por limites de servidor: o **SICAR estadual** (MG possui ~1,18 milhão de imóveis que exigiriam 118 requisições de 10.000 feições), os **Autos de Infração do IBAMA** e as **concessões da ANM**.
2. **Regiões Geográficas Imediatas e Intermediárias (IBGE 2017):**
   - Disponibilizar na interface os recortes da divisão regional vigente do IBGE, cuja composição município-região já se encontra estruturada no arquivo CSV de apoio.
3. **Novas IDEs Estaduais do INDE com WFS Homologado:**
   - Integrar nós estaduais funcionais identificados na varredura:
     - **ES GEOBASES:** 672 camadas disponíveis.
     - **TO SEPLAN:** 1.267 camadas disponíveis.
     - **CE SEMA/PEDEA:** 145 camadas disponíveis.
     - **RJ INEA:** 4.249 camadas acessíveis via proxy GeoServer do INDE (`https://geoservicos.inde.gov.br/geoserver/INEA/ows`).
     - *(Emplasa-SP: 2.146 camadas; reavaliar caso adotem protocolo HTTPS).*
4. **Camadas Temáticas Complementares das IDEs já Conectadas:**
   - **Minas Gerais (MG):** Áreas de Preservação Permanente (APP) hídricas do MapCAR, manchas de inundação de barragens (PAE), barragens de mineração/rejeitos, licenciamento ambiental municipalizado, índice de esgotamento sanitário 2022 e tombamentos municipais.
   - **Distrito Federal (DF):** LUOS - Uso e Ocupação do Solo (~384 mil lotes cadastrais; viável sob paginação), cobertura vegetal 2019 e malha cicloviária.
   - **Rio Grande do Sul (RS):** Cartografia sistemática BASE25 (escala 1:25.000) e manchas de inundação com tempo de retorno TR50/TR100 da METROPLAN.
   - **Paraná (PR):** Outorgas de recursos hídricos SIGARH (~84 mil pontos), suscetibilidade a inundações SISMAAR e cadastro de aterros e lixões.
   - **Goiás (GO):** Nascentes mapeadas (~158 mil pontos; indicada para escala regional) e Base Hidrográfica Ottocodificada de Goiás.
5. **Zoneamento Municipal de Planos Diretores:**
   - Para regiões metropolitanas e municípios que mantêm serviços de mapas ativos (como os municípios sob METROPLAN-RS e a PDOT no DF), estruturar mecanismo de catálogo local/municipal para carregar zoneamentos urbanos e perímetros urbanos legais.
6. **Novos Temas Federais:**
   - **Recursos Hídricos:** Macrorregiões hidrográficas nacionais e ottobacias nível 4/5 (IBGE `CGMAT:qg_2021_840_MacroRegHidro`).
   - **Saúde:** Regiões e macrorregiões de saúde (`read_health_region` / `health_macro`).
   - **Defesa Civil / Riscos:** Setorização de áreas de risco geológico e hidrológico do CEMADEN e S2iD.
   - **Energia:** Linhas de transmissão e subestações do Sistema Interligado Nacional (ANEEL SIGEL).
   - **Saneamento:** Indicadores municipais agregados do SINISA (substituto do SNIS).
   - **Demografia:** Grade Estatística do Censo Demográfico 2022 (células de 200 m / 1 km particionadas por UF).
7. **MapBiomas Coleção 10:**
   - Migrar a fonte `mapbiomas_cobertura` para os novos Cloud Optimized GeoTIFFs (COGs) da Coleção 10 assim que disponibilizados no bucket oficial da iniciativa.

---

## 8. Gate nos Dois Containers (Passo 13)

Resultado medido em 2026-09-30:

- `python3 ~/.hermes/planexec.py test /home/diego/projects/gisbr both`
- **✓ verde em: qgis3, qgis4** (`suite=OK smoke=OK` nos dois)
- `qgis3/Qt5`: imagem `docker.io/qgis/qgis:3.44` (QGIS 3.44.12-Solothurn, Qt 5.15.17) — `suite=OK smoke=OK` (smoke_rc=0, 73 módulos, 0 falhas)
- `qgis4/Qt6`: imagem `docker.io/qgis/qgis:4.2.0` (QGIS 4.2.0-Belém do Pará, Qt 6.9.2) — `suite=OK smoke=OK` (smoke_rc=0, 73 módulos, 0 falhas; 4 avisos `QThreadStorage` do teardown do Qt6 suprimidos - ruído conhecido do shutdown, não é falha)
- Enums e compatibilidade Qt5/Qt6: sem pendências de enums não escopados ou quebras de sintaxe nos 73 módulos do plugin.

