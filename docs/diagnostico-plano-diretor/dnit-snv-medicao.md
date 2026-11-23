# Medição com Dado Real — DNIT SNV e DER-MG (Rede Rodoviária)

Documento de medição empírica e validação técnica da integração da malha rodoviária federal (**`dnit_snv`**, protocolo `wfs`, nova origem direta do DNIT) e estadual de Minas Gerais (**`der_mg_rodovias`**, protocolo `wfs`), executado no QGIS headless do host (`start_app`), cobrindo o município de Contagem / MG (`3118601`), a validação da vigência temporal, detecção de trechos planejados (`PLA`) e a desduplicação federal × estadual.

- **Data da medição:** 2026-11-23
- **Ambiente de teste:** Linux 6.8 (x86_64), Python 3.12, QGIS 3.x nativo (headless via `qgis.testing.start_app`), GDAL/OGR com suporte OGC e GeoPackage.
- **Fontes avaliadas:**
  - `dnit_snv`: DNIT — SNV (rodovias federais; WFS DNIT GeoServer `vgeo:vw_snv_rod`, `filtro: bbox`, EPSG:4674, vigência temporal `Versao_SNV`).
  - `der_mg_rodovias`: DER-MG — Rodovias estaduais (WFS Sisema/IDE `IDE:ide_0401_mg_rodovias_lin`, `filtro: bbox`, EPSG:4674).
- **Status do documento:** Documentação técnica interna (pasta `docs/diagnostico-plano-diretor/` em `exclude_docs`).

---

## 1. Achados Técnicos da Investigação (Rodada 26)

### 1.1. Achado 1 — Desmontagem do GeoServer da INDE
O endpoint histórico utilizado pelo GisBR na INDE (`https://geoservicos.inde.gov.br/geoserver/DNIT/ows`) passou a retornar **HTTP 404** (HTML padrão do Apache Tomcat 8.5.100).
- A falha não se deu pela substituição de uma edição específica (`snv_202507a` por outra mais recente), mas pelo encerramento do próprio workspace `DNIT` no nó central da INDE.
- A inspeção do endpoint administrativo de workspaces (`/geoserver/rest/workspaces.json`) revelou que apenas três workspaces permanecem ativos no servidor: `PEM`, `DHN` e `gn`. O documento `GetCapabilities` na raiz publica exclusivamente a camada `gn:gboundaries`.
- Outros órgãos federais associados foram afetados simultaneamente: os workspaces `MInfra` e `ICMBio` também retornam 404, afetando as fontes `minfra_ferrovias`, `icmbio_embargos` e `icmbio_uc` (cujo redirecionamento ficou registrado para tratamento em rodadas futuras).

### 1.2. Achado 2 — View Histórica no GeoServer Oficial do DNIT e Sintaxe BBOX+CRS
O Departamento Nacional de Infraestrutura de Transportes (DNIT) mantém serviço próprio e ativo de catálogo geoespacial:
- **Endpoint WFS:** `https://servicos.dnit.gov.br/dnitgeo/geoserver/wfs` (GetCapabilities HTTP 200, anunciando suporte a `application/json` e OGC WFS 2.0.0).
- **Camada Canônica:** **`vgeo:vw_snv_rod`** (CRS `EPSG:4674`, geometria `MultiCurve` convertida nativamente em `MultiLineString` no QGIS, campo geométrico **`geom`**).
- **Natureza Histórica da View:** A view `vgeo:vw_snv_rod` armazena o histórico cadastral completo do Sistema Nacional de Viação desde 2016, totalizando **343.892 feições**. Cada segmento é parametrizado pelas colunas `Versao_SNV`, `dt_ini` e `dt_fim`. As faixas de vigência são estritas e sem sobreposição temporal (ex.: `202607A` vigorou de 2026-07-28 a 2026-10-20; `202610A` vigora desde 2026-10-21 com `dt_fim` provisório em 2029-10-30). Nenhuma feição apresenta `dt_fim` nulo.
- **Filtro de Vigência Dinâmico:** Uma consulta com `CQL_FILTER=dt_ini <= '2026-11-23' AND dt_fim >= '2026-11-23'` retorna rigorosamente **7.685 feições**, número idêntico ao obtido por `Versao_SNV = '202610A'`. O filtro temporal seleciona automaticamente a malha rodoviária vigente sem necessidade de bump manual de versões no código.
- **Incompatibilidade GeoServer entre BBOX e CQL_FILTER:** No GeoServer do DNIT, o parâmetro HTTP padrão `bbox` e o parâmetro `CQL_FILTER` se anulam mutuamente. Para que a restrição espacial e a vigência temporal atuem juntas, o envelope deve ser injetado como predicado espacial `BBOX(geom, minx, miny, maxx, maxy, 'EPSG:4674')` internamente à cláusula CQL.
  - A omissão do CRS na função `BBOX()` do CQL acarreta retorno de **0 feições**, decorrente da convenção de inversão de eixos (latitude/longitude) do EPSG:4674 no OGC WFS.
  - Com a especificação explícita do CRS `'EPSG:4674'`, o GeoServer aplica a ordem longitude/latitude e devolve as feições corretas.
- **Evolução de Esquema Atributar:**
  A camada oficial `vgeo:vw_snv_rod` adota nomenclatura em *CamelCase* expandido, divergindo dos nomes legados no padrão DBF/Shapefile da INDE:

| Atributo / Papel | INDE (legado) | DNIT `vgeo:vw_snv_rod` | Exemplos no Dado Real |
|---|---|---|---|
| Identificador da BR | `vl_codigo` / `vl_br` | `Codigo_BR` | `"040"`, `"262"`, `"381"` |
| Superfície da pista | `ds_superfi` | `Superficie_Federal` | `"DUP"`, `"PAV"`, `"PLA"` (Planejada) |
| Trechos coincidentes | `ds_coinc` | `Coincidencia_Federal` | `"262BMG0610;381BMG0440"` |
| Coincidência estadual | `est_coinc` | `Estadual_Coincidente` | `"Alienado"`, `"MG-356"` |
| UF | `sg_uf` | `Unidade_Federacao` | `"MG"`, `"SP"` |

- **Certificados e TLS:** O host `servicos.dnit.gov.br` opera com certificado Let's Encrypt `YR1` emitido por autoridade cruzada com **ISRG Root X1**, validado sem inconformidades pelo script `tools/check_sources_tls.py`.

### 1.3. Achado 3 — Validação Exata com Repositório DnitCloud (7685 = 7685)
O link disponibilizado para auditoria (`https://servicos.dnit.gov.br/dnitcloud/index.php/s/oTpPRmYs5AAdiNr`) consiste em uma instância pública Nextcloud:
- **Acesso Programático:** Listagem e download via protocolo WebDAV através de `PROPFIND https://servicos.dnit.gov.br/dnitcloud/public.php/webdav/` utilizando o token do compartilhamento (`oTpPRmYs5AAdiNr`) como usuário e senha em branco.
- **Acervo Identificado:**
  - `GUIA SNV_2025.pdf` e acervo histórico do PNV (1983–2010).
  - Pasta `SNV Bases Geométricas (2013-Atual) (SHP)/`, contendo pacotes compactados por edição desde `201301A.zip` até a edição corrente **`202610A.zip`** (70,4 MB, gerado em 20/10/2026).
- **Validação Cruzada (Paridade Matemática 7685 = 7685):**
  O arquivo extraído `SNV_202610A.shp` contém exatamente **7.685 feições lineares**, confirmando equivalência exata com o total retornado pelo WFS do DNIT sob filtro de vigência na data da medição.
- **Diretriz de Uso:** A obtenção vetorial via WFS é substancialmente mais leve (transferência municipal de poucos kilobytes contra 70 MB por download nacional) e imune à caducidade de URLs estáticas. O DnitCloud permanece documentado como ambiente oficial de contingência e aferição de verdade de campo.

---

## 2. Medição em Contagem / MG (`3118601`)

A medição foi executada invocando o motor `gisbr.core.diagnostico.carregar_fontes` no ambiente headless do QGIS (`start_app`), requisitando simultaneamente `dnit_snv` e `der_mg_rodovias` com gravação em GeoPackage temporário.

- **Município:** Contagem / MG (IBGE: `3118601`).
- **BBOX Real do Município (EPSG:4674):** `(-44.162056, -19.983388, -44.005429, -19.798839)`.
- **Tempo Total de Execução do Motor:** **1,27 s**.

### 2.1. Tabela Geral de Feições e Camadas no GeoPackage

| Camada no GeoPackage | Papel no Diagnóstico | Feições Pré-Clip | Feições Pós-Clip | Feições Finais | Observações Topológicas / Atributos |
|---|---|---|---|---|---|
| **`dnit_snv_3118601`** | Rede Federal (Links) | 23 | 8 | **2** | Arcos ativos mantidos: BR-040 (DUP) e BR-262 (DUP). Colapso de 2 sobreposições coincidentes. |
| **`dnit_snv_nos_3118601`** | Nós da Rede Federal | — | — | **4** | Nós topológicos correspondentes aos extremos dos arcos federais ativos. |
| **`dnit_snv_problemas_3118601`** | Diagnóstico Federal | — | — | **3** | 1 ilha (`alta`, arco isolado na divisa) e 2 correções `coincidente_colapsado` (`corrigido`). |
| **`dnit_snv_removidos_3118601`** | Segmentos Federais Excluídos | — | — | **4** | **100% planejados (`PLA`)**: BR-040 (1), BR-262 (1) e BR-381 (2). |
| **`der_mg_rodovias_3118601`** | Rede Estadual (Links) | 27 | 14 | **10** | Arcos estaduais mantidos após desduplicação (MG-808, acessos e federais sem par). |
| **`der_mg_rodovias_nos_3118601`** | Nós da Rede Estadual | — | — | **12** | Nós conectores da malha rodoviária sob gestão estadual. |
| **`der_mg_rodovias_problemas_3118601`** | Diagnóstico Estadual | — | — | **7** | 4 `federal_sem_par` (`baixa`), 1 `ilha` (`alta`), 1 `ponta_quase_conectada` (`alta`), 1 `cruzamento_sem_no` (`media`). |
| **`der_mg_rodovias_removidos_3118601`** | Segmentos Estaduais Excluídos| — | — | **4** | **100% desduplicação federal**: 4 trechos estaduais sobrepostos à rede federal ativa mantida. |

### 2.2. Confirmação da Edição Vigente no Log
O motor registrou a edição única vigente de forma limpa, sem mensagens de aviso ou sobreposição histórica:
```text
[INFO] DNIT — SNV (rodovias federais): edição 202610A
```

### 2.3. Comportamento dos Trechos Planejados (`PLA`) no DNIT
O recorte pelo polígono municipal de Contagem capturou 8 feições brutas da camada `vgeo:vw_snv_rod`. Dessas:
- **4 feições com `Superficie_Federal = 'PLA'`** foram identificadas pelo filtro da rede rodoviária (`rede.excluir.campo = "Superficie_Federal"`, valores `["PLA"]`) e desviadas para a camada de removidos `dnit_snv_removidos_3118601`:
  1. **BR-040** (`Superficie_Federal='PLA'`, `Estadual_Coincidente=NULL`, `Versao_SNV='202610A'`)
  2. **BR-262** (`Superficie_Federal='PLA'`, `Estadual_Coincidente='Alienado'`, `Versao_SNV='202610A'`)
  3. **BR-381** (`Superficie_Federal='PLA'`, `Estadual_Coincidente='Alienado'`, `Versao_SNV='202610A'`)
  4. **BR-381** (`Superficie_Federal='PLA'`, `Estadual_Coincidente=NULL`, `Versao_SNV='202610A'`)
- **4 feições com `Superficie_Federal = 'DUP'`** seguiram para a montagem de rede. Como a BR-040 coincide fisicamente com a BR-135 e a BR-262 coincide com a BR-381 no trecho urbano de Contagem, o algoritmo `coincidente_colapsado` identificou as 2 duplicidades geométricas intrínsecas do DNIT e gerou a malha final enxuta de **2 arcos físicos** e **4 nós**.

### 2.4. Desduplicação Federal × Estadual no DER-MG
A camada estadual bruta continha 14 feições no polígono municipal. Ao confrontar com a camada federal `dnit_snv_3118601`:
- **4 trechos removidos por duplicidade:** Segmentos cadastrados pelo DER-MG sob `jurisdicao='Federal'` e códigos `040` (2 trechos) e `262` (2 trechos) sobrepostos aos arcos mantidos do DNIT dentro do limiar de 50 m (`TOL_DUP_M`) foram removidos da rede e arquivados em `der_mg_rodovias_removidos_3118601` com `motivo = 'duplicado_federal'`.
- **Preservação de trechos coincidentes com o DNIT planejado (`federal_sem_par`):** Quatro trechos cadastrados na malha estadual como jurisdição federal incidem sobre segmentos que, no cadastro do DNIT, constam como `PLA` (portanto excluídos da rede federal ativa). O motor de desduplicação preservou integralmente esses 4 trechos na rede estadual mantida (`der_mg_rodovias_3118601`), gerando 4 alertas de severidade baixa `federal_sem_par` em `der_mg_rodovias_problemas_3118601`.
- **Malha estadual ativa:** Restaram **10 arcos** e **12 nós** cobrindo a malha estadual efetiva (incluindo a rodovia MG-808 e as ligações municipais).

---

## 3. Conformidade Cartográfica e Integridade de CRS

Todas as 8 tabelas geradas no GeoPackage foram auditadas quanto ao identificador espacial registrado no cabeçalho OGC (`gpkg_contents` e `gpkg_spatial_ref_sys`):

| Tabela no GeoPackage | CRS Registrado | Validação |
|---|---|---|
| `dnit_snv_3118601` | `EPSG:4674` (SIRGAS 2000) | Conforme |
| `dnit_snv_nos_3118601` | `EPSG:4674` (SIRGAS 2000) | Conforme |
| `dnit_snv_problemas_3118601` | `EPSG:4674` (SIRGAS 2000) | Conforme |
| `dnit_snv_removidos_3118601` | `EPSG:4674` (SIRGAS 2000) | Conforme |
| `der_mg_rodovias_3118601` | `EPSG:4674` (SIRGAS 2000) | Conforme |
| `der_mg_rodovias_nos_3118601` | `EPSG:4674` (SIRGAS 2000) | Conforme |
| `der_mg_rodovias_problemas_3118601` | `EPSG:4674` (SIRGAS 2000) | Conforme |
| `der_mg_rodovias_removidos_3118601` | `EPSG:4674` (SIRGAS 2000) | Conforme |

---

## 4. Conclusão Técnica

A medição em Contagem comprova a plena operacionalidade e precisão do novo conector e modelo de dados do `dnit_snv`:
1. O acesso WFS direto ao GeoServer do DNIT contorna em definitivo a indisponibilidade do workspace DNIT na INDE.
2. O mecanismo de vigência temporal por data embutido no CQL (`_cql_vigencia`) isolou com perfeição a edição vigente `202610A` dentre mais de 340 mil feições históricas, sem ruídos ou sobreposições.
3. O filtro de exclusão por `Superficie_Federal = 'PLA'` e o tratamento de códigos de rodovia adaptado (`Codigo_BR`) operaram com fidelidade matemática absoluta, garantindo a perfeita integração e desduplicação com a malha estadual do DER-MG.
