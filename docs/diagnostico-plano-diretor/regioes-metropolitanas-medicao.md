# Medição de Suporte a Regiões Metropolitanas e Diagnóstico Multimunicipal

Documento de medição empírica e registro de arquitetura para a integração de **Regiões Metropolitanas (RMs)** e **Aglomerações Urbanas (AUs)** no plugin **GisBR**.

**Data da medição:** 2026-09-20  
**Ambiente de teste:** Linux Sandbox (Python 3.12, PyQGIS / urllib)

---

## 1. Visão Geral e Tabela de Medições

A tabela a seguir consolida as **15 medições empíricas** realizadas para avaliar o acesso a APIs oficiais de localidades, protocolos espaciais (WFS CQL, ArcGIS REST, Overpass) e agregados tabulares ao lidar com agrupamentos metropolitanos de municípios.

| # | Protocolo / Componente | Endpoint / Alvo | Data | Resultado / Métrica |
|---|---|---|---|---|
| 1 | **API de RMs (IBGE v1)** | `https://servicodados.ibge.gov.br/api/v1/localidades/regioes-metropolitanas` | 2026-09-20 | 84 entidades retornadas; payload estruturado em JSON com `id`, `nome`, `UF`, `municipios[]`, `sub-regioes-metropolitanas[]`. |
| 2 | **Abrangência de Municípios** | IBGE API v1 RMs | 2026-09-20 | **1.377 municípios únicos** (códigos IBGE de 7 dígitos) vinculados às 84 entidades metropolitanas. |
| 3 | **Verificação de Sobreposição** | IBGE API v1 RMs | 2026-09-20 | **Zero sobreposição** (`count = 0`). Cada município pertence a no máximo 1 RM na API oficial do IBGE. |
| 4 | **Presença de RIDEs** | IBGE API v1 RMs | 2026-09-20 | **Ausência de RIDE** (RIDE DF/Entorno, Petrolina-Juazeiro e Teresina-Timon não constam na API de RMs estaduais). |
| 5 | **Entidades Multi-UF** | IBGE API v1 RMs | 2026-09-20 | **Ausência de entidade multi-UF**. Todas as 84 entidades possuem exatamente 1 estado associado no objeto `UF`. |
| 6 | **WFS CQL `IN` (SICAR)** | `https://geoserver.car.gov.br/geoserver/sicar/wfs` | 2026-09-20 | **624 feições** retornadas em **0,43 s** via `CQL_FILTER=cod_municipio IN (...)` em lote metropolitano. |
| 7 | **ArcGIS REST `where ... IN` (IBAMA)** | `https://pamgia.ibama.gov.br/server/rest/services/...` | 2026-09-20 | Suporte nativo a cláusula `where=code_muni IN (...)` via HTTP GET/POST para requisição multi-município. |
| 8 | **Agregados IBGE v3 Lote** | `https://servicodados.ibge.gov.br/api/v3/agregados/...` | 2026-09-20 | Suporte nativo a lote de municípios em `localidades=N6[a,b,c]`, retornando série em requisição única. |
| 9 | **Bloqueio WAF (IBGE Geosserviços)** | `https://geoservicos.ibge.gov.br/geoserver/ows` | 2026-09-20 | **HTTP 403 (Cloudflare Challenge)** na sandbox. Ressalva: é restrição de acesso da sandbox, não erro de sintaxe. |
| 10 | **Envelope BBOX Metropolitano** | WFS Genéricos (DNIT / ICMBio / SGB) | 2026-09-20 | BBOX unificada da RM recupera dados via WFS em 1 chamada HTTP, exigindo post-clip vetorial. |
| 11 | **Filtragem em geobr (v1/v2)** | Leitura local de `.gpkg` e `.parquet` | 2026-09-20 | Filtragem vetorial PyQGIS via `setSubsetString("code_muni IN (...)")` executada em < 0,05 s. |
| 12 | **Resolução Inversa (Muni -> RM)** | Indexador `code_muni -> RM` em memória | 2026-09-20 | Resolução instantânea (< 2 ms) permitindo expandir 1 município para a RM completa na UI. |
| 13 | **Sub-regiões Metropolitanas** | IBGE API v1 RMs (`sub-regioes-metropolitanas`) | 2026-09-20 | Payload traz sub-divisões oficiais (ex.: RM São Paulo, Campinas), viabilizando recortes intermediários. |
| 14 | **Overpass OSM via BBOX da RM** | `https://overpass-api.de/api/interpreter` | 2026-09-20 | Consulta Overpass unificada por BBOX da RM obtém `osm_vias` e `osm_pois` para toda a região. |
| 15 | **GeoPackage Único Metropolitano** | Persistência Local (`diagnostico_RM_<id>.gpkg`) | 2026-09-20 | Gravação de todas as camadas dos 8 eixos em 1 único `.gpkg` regional, otimizando o diagnóstico. |

---

## 2. Detalhamento dos Achados Principais

### 2.1. API de Localidades do IBGE — Endpoint de Regiões Metropolitanas

- **URL do endpoint:** `https://servicodados.ibge.gov.br/api/v1/localidades/regioes-metropolitanas`
- **Data da consulta:** 2026-09-20
- **Formato do payload JSON:**
  ```json
  [
    {
      "id": 3101,
      "nome": "Região Metropolitana de Belo Horizonte",
      "UF": {
        "id": 31,
        "sigla": "MG",
        "nome": "Minas Gerais",
        "regiao": { "id": 3, "sigla": "SE", "nome": "Sudeste" }
      },
      "sub-regioes-metropolitanas": [],
      "municipios": [
        {
          "id": 3106200,
          "nome": "Belo Horizonte",
          "microrregiao": { ... },
          "regiao-imediata": { ... }
        },
        ...
      ]
    }
  ]
  ```

#### Estatísticas e comportamento do payload:
1. **84 entidades catalogadas:** Compreendem RMs e Aglomerações Urbanas (AUs) instituídas por leis complementares estaduais.
2. **1.377 municípios abrangidos:** De um total de 5.570 municípios brasileiros, 1.377 pertencem a alguma RM/AU estadual.
3. **Zero sobreposição territorial:** O teste empírico confirmou que nenhum município de 7 dígitos aparece em mais de uma RM no catálogo do IBGE (contagem máxima de ocorrências por `id` municipal = 1).
4. **Ausência de RIDE:** As Regiões Integradas de Desenvolvimento (RIDE DF/Entorno, RIDE Petrolina-Juazeiro e RIDE Teresina-Timon) **não são retornadas** por este endpoint. Como as RIDEs são criadas por lei federal e envolvem múltiplas UFs, o IBGE as disponibiliza em endpoints ou cadastros específicos.
5. **Ausência de entidades multi-UF:** Todas as 84 entidades retornadas pela API possuem uma única UF associada na chave `UF`.

---

### 2.2. Desempenho e Sintaxe de Consultas Multimunicipais em APIs de Dados

#### 2.2.1. Geoserver / WFS com Filtro CQL `IN` (SICAR)
- **URL:** `https://geoserver.car.gov.br/geoserver/sicar/wfs`
- **Data:** 2026-09-20
- **Sintaxe CQL:** `CQL_FILTER=cod_municipio IN ('3201308','3202206','3202405','3205002','3205101','3205200','3205309')`
- **Resultado medido:** **624 feições** retornadas em **0,43 s** para o lote de 7 municípios da RM Grande Vitória (ES).
- **Conclusão:** A filtragem via `CQL_FILTER` com a lista completa de municípios da RM é extremamente eficiente, evitando a necessidade de múltiplas chamadas HTTP por município.

#### 2.2.2. ArcGIS REST com Cláusula `where ... IN` (IBAMA)
- **URL:** `https://pamgia.ibama.gov.br/server/rest/services/app_dadosabertos/adm_auto_infracao_p/MapServer/0/query`
- **Data:** 2026-09-20
- **Sintaxe SQL:** `where=code_muni IN ('3106200','3118601','3129806',...)&f=geojson`
- **Resultado medido:** Suporte nativo completo a `IN (...)` na API do MapServer/FeatureServer do Esri ArcGIS REST.

#### 2.2.3. Agregados Tabulares IBGE v3 em Lote (`localidades=N6[...]`)
- **URL:** `https://servicodados.ibge.gov.br/api/v3/agregados/1612/periodos/-1/variaveis/default?localidades=N6[3201308,3202206,3202405,3205002,3205101,3205200,3205309]`
- **Data:** 2026-09-20
- **Resultado medido:** A API v3 de Agregados aceita uma lista de códigos IBGE separados por vírgula dentro do colchetes do nível `N6`. O retorno traz as séries tabulares de todos os municípios da RM agrupados em uma única resposta JSON.

---

### 2.3. Ressalva de Acesso: Bloqueio WAF Cloudflare em `geoservicos.ibge.gov.br`

- **URL:** `https://geoservicos.ibge.gov.br/geoserver/ows`
- **Data:** 2026-09-20
- **Comando de teste:**
  ```bash
  curl -i -s "https://geoservicos.ibge.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetCapabilities" | head -n 20
  ```
- **Saída capturada na sandbox:**
  ```http
  HTTP/2 403 
  date: Sun, 20 Sep 2026 22:05:00 GMT
  content-type: text/html; charset=UTF-8
  server: cloudflare
  cf-mitigated: challenge

  <!DOCTYPE html><html lang="en-US"><head><title>Just a moment...</title>
  ```
- **Ressalva importante:**
  > O retorno **HTTP 403 Forbidden** decorre da política de segurança/WAF da Cloudflare no ambiente de sandbox (bloqueio de faixa de IP ou User-Agent automatizado de nuvem). **Não se trata de um erro de sintaxe WFS ou de descontinuação do serviço pelo IBGE.** O acesso a `geoservicos.ibge.gov.br` deve ser reconferido na máquina do Diego (ambiente desktop Pop!_OS / Ubuntu com IP residencial/comercial).

---

## 3. Implicações para a Arquitetura do Plugin GisBR

1. **Catálogo em Memória de RMs:** O plugin pode carregar e cachear a lista de 84 RMs da API v1 do IBGE em `core/sources.py` ou utilitário dedicado.
2. **Seleção Inteligente na UI:** Permite adicionar um modo de seleção por **Região Metropolitana** no painel de diagnóstico (`diagnostico_dock.py`), expandindo os municípios da RM automaticamente para requisições em lote.
3. **Requisições em Lote (Batch Requests):** A confirmação de suporte ao operador `IN (...)` no WFS (`CQL_FILTER`), ArcGIS REST (`where`) e IBGE Agregados (`localidades=N6[...]`) garante que a extração de uma RM inteira possa ser feita com mínimo *overhead* de rede.
4. **GeoPackage Único por Usuário:** O diagnóstico (municipal e metropolitano) é gravado em **um único GeoPackage escolhido pelo usuário no painel**, onde as camadas municipais (`<fonte>_<code_muni>`) e as metropolitanas (`<fonte>_rm<id>`, mais a camada de limite `rm_<id>`) convivem no mesmo arquivo sem colidir, mantendo a organização de 1 camada por fonte e os eixos temáticos.

---

## 4. Gate (passo 14 da rodada 19)

Resultado medido em 2026-09-20, após o `/review`:

- `planexec.py test /home/diego/projects/gisbr both`
- **✓ verde em: qgis3, qgis4** (`suite=OK smoke=OK` nos dois)
- `qgis3/Qt5`: imagem `docker.io/qgis/qgis:3.44` (Qt 5) — suíte completa verde
- `qgis4/Qt6`: imagem `docker.io/qgis/qgis:4.2.0` (Qt 6) — suíte completa verde
  (4 avisos `QThreadStorage` do teardown do Qt6, ruído conhecido do shutdown,
  não é falha)
- Nota do review: a suíte do `tests/test_docs_site.py` falhava nos DOIS
  containers já antes desta rodada (o gerador escreve `CHANGELOG.md` na raiz do
  repo, que o gate monta read-only); corrigido com o parâmetro
  `changelog_raiz=` em `tools/build_docs_site.py:gerar()`, sem mudar o
  comportamento do `make docs` no host.
