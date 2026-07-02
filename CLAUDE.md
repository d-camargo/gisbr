# CLAUDE.md — geobr-qgis

> Documento de contexto persistente para o Claude Code.
> Plugin QGIS que replica a funcionalidade do pacote **geobr** (IPEA) usando **apenas a API nativa do QGIS/Qt**, sem dependências externas (`geopandas`, `requests`, `pandas`, `duckdb`).

---

## 1. Visão geral do projeto

**Objetivo:** trazer para dentro do QGIS o acesso "1 linha → 1 camada" aos dados espaciais oficiais do Brasil que o `geobr` oferece em R/Python, reutilizando a **mesma infraestrutura de dados do IPEA** (Opção 1), porém sem instalar nada além do que já vem no QGIS.

**Autor:** Diego Camargo (@d-camargo)
**Repositório alvo:** `github.com/d-camargo/geobr-qgis`
**Caminho local:** `~/Documentos/SIG/geobr-qgis/`
**Ambiente:** Pop!_OS (desktop) / Ubuntu (notebook), QGIS 3.x via instalação do sistema.
**Região de trabalho:** Belo Horizonte / Contagem, MG.

**Princípio inegociável:** o máximo possível com a API do QGIS e a stdlib do Python. Nada de `pip install`. As únicas "dependências" aceitas são as que **já acompanham o QGIS** (PyQGIS, Qt/PyQt, e a stdlib).

---

## 1.1. Evolução de escopo e publicação (decisões de 2026-06-29)

> Esta seção registra a virada de escopo discutida com o Diego. O núcleo (espelho do geobr, §2–§10) continua valendo; o que vem abaixo é a camada que cresce por cima.

**Evolução para sistema de Diagnóstico de Plano Diretor.** Além de espelhar o geobr, o plugin vai evoluir para um **sistema de diagnóstico de cidades que precisam elaborar/revisar o Plano Diretor**, subindo dados de bases oficiais organizados em **6 eixos**: (1) Infraestrutura de transportes, (2) Drenagem e Saneamento, (3) Demografia (já coberto via geobr/censobr), (4) Ambiental (MMA/SICAR/MapBiomas/…), (5) Educação (já temos `read_schools`; agregar INEP/IBGE), (6) Saúde (já temos `read_health_*`; agregar DataSUS/CNES/MS).

- **Decisão de arquitetura:** **evoluir o próprio plugin** (não plugin separado, não repo novo). A evolução acontece em **branch** (`feat/diagnostico-plano-diretor`), mantendo a `main` sempre publicável.
- **Reaproveitamento mapeado:** o projeto irmão `~/Drive/02_Projetos_Tecnicos/haCARthon/desafio-2/src/plugin-qgis/` tem peças prontas a portar — `core/wfs.py` (loader WFS robusto: pilha de rede do QGIS p/ contornar SSL de GeoServer, fallback `/vsicurl/`, grava `data_extracao`, filtro `CQL_FILTER`), `core/parecer.py`+`layout_parecer.py` (relatório), `gui/kpis_dock.py` (painel de KPIs), e a disciplina de **data de extração** de `docs/referencias.md`. Código portado entra primeiro em `desafio-2-port/` (staging, fora do pacote).
- **Geoservers de interesse:** federais e estaduais e, quando disponíveis, municipais (provavelmente só municípios grandes — manter a referência mesmo assim).
- **Pesquisa primeiro:** a varredura de geoservers + taxonomia de cidades (REGIC etc.) + panorama de dados abertos é registrada como ACTIONS e salva como `.md` de referência em `docs/diagnostico-plano-diretor/`. É ela que informa a arquitetura de código dos eixos.

**Publicação no repositório oficial do QGIS (plugins.qgis.org).** Será feita **várias vezes**, começando pelo estado atual (Fases 1 e 2).

- **Skill de empacotamento:** `build-qgis-zip` (`.claude/skills/build-qgis-zip/`) gera `dist/gisbr-<version>.zip` com a estrutura exigida (uma pasta de topo `gisbr/` com `metadata.txt` na raiz) e **exclui** docs/pesquisa/`*.pdf`/arquivos de processo. Toda geração de zip usa essa skill; a submissão final é passo **manual do Diego** (conta OSGeo).
- **Higiene de empacotamento:** material de pesquisa (`docs/`), ports do haCARthon (`desafio-2-port/`) e arquivos de processo (`ACTIONS/AGENTS/INSTRUCTIONS/CLAUDE.md`, `Makefile`, `STRUCTURE.md`) **não entram** no pacote publicado.
- **Idioma (constraint do QGIS):** o repositório oficial espera o plugin em **inglês**. Feito: `metadata.txt` reescrito em inglês. Pendente: i18n da UI (nomes/grupos de algoritmos ainda em PT-BR) via Qt (`tr()`/`.ts`/`.qm`) com PT-BR como tradução. Cogitado um "botão/opção de idioma".
- **Nome — DECIDIDO (2026-06-29): `GisBR`** (disponibilidade conferida no repo do QGIS; remote git já é `d-camargo/gisbr`). Aplicado: `metadata.txt name=GisBR`, provider `id()="gisbr"`/`name()="GisBR"`, `PLUGINNAME=gisbr` (Makefile), `PLUGIN_DIR="gisbr"` (skill). Algoritmos agora em `gisbr:read_*`. Observação registrada: "GeoBR" é o pacote R/Python do IPEA; vale consultar a equipe deles, mas o nome do plugin passou a ser GisBR (distinto).
- **Licença — DECIDIDA: GPL-3.0** (arquivo `LICENSE` na raiz, texto completo).
- **`metadata.txt` — ATUALIZADO:** versão **0.2.0**, `experimental=True` (mantido), descrição/about/changelog refletindo Fases 1+2 (55 algoritmos), em inglês. Repos apontando para `github.com/d-camargo/gisbr`.

**Fluxo de trabalho planejador→executor.** O projeto adota o trio `AGENTS.md` (papel do senior), `INSTRUCTIONS.md` (papel do junior) e `ACTIONS.md` (tarefas concretas com status). O senior planeja e registra ACTIONS; o junior executa só as marcadas `status: pronta`.

---

## 1.2. Estado implementado do diagnóstico (branch `feat/diagnostico-plano-diretor`, 2026-06-30)

> **ATUALIZADO 2026-07-02:** a `feat/diagnostico-plano-diretor` foi **mergeada na `main`** (merge commit; árvore da main = feat). A `main` agora **é** o plugin completo (diagnóstico + i18n), não mais só o espelho geobr. A branch `feat` segue no remoto como backup. Detalhe de cada tarefa (T-003…T-029) em `ACTIONS.md`; desenho em `docs/diagnostico-plano-diretor/ARQUITETURA.md`. **Submissão ao QGIS: a 0.3.0 foi BLOQUEADA pelo scan de segurança** (o dir `scratch/` vazou pro zip; ver §10); corrigido na **0.3.1** (pendente de re-upload pelo Diego).

**Arquitetura (declarativa, município-cêntrica):**
- `core/sources.py` — catálogo declarativo `SOURCES` (**29 fontes**): 8 WFS + 5 ArcGIS REST + 15 geobr + 1 basemap. Cada fonte é um dict (`id, eixo, nome, protocolo, …`). Filtro: `{"tipo":"cql_codigo"|"cql_nome"|"bbox", ...}` (WFS/ArcGIS) ou `recorte: "code"|"bbox"` + `algo` (geobr). v2-only (`favela`/`polling_places`/`quilombola_land`) marcadas `requer_parquet`.
- `core/connectors/` — um por protocolo: `wfs.py` (GeoJSON via `QgsBlockingNetworkRequest` + fallback `/vsicurl/`, `CQL_FILTER`/bbox, portado do `desafio-2`), `arcgis_rest.py` (query `f=geojson`, `where=`/`geometry=`), `basemap.py` (XYZ Esri World Imagery via `QgsRasterLayer(..., "wms")`).
- `core/diagnostico.py` — **motor** `carregar_fontes(source_ids, code_muni, nome_muni, bbox, gpkg_path, add_basemap, force, feedback)`: para cada fonte, busca filtrada pelo município → grava no **GeoPackage** (1 camada/fonte, nome `id_codemuni`; display "<fonte> - <cidade>") → adiciona ao projeto. Protocolos `wfs|arcgis|geobr`.
- `gui/diagnostico_dock.py` — **painel (dock)**, UX principal: combos **UF → Município** (busca por nome, `QCompleter`), árvore de fontes com **checkbox por eixo** (grupos ordenados 1..8 por `_EIXO_NOMES`), caminho do GeoPackage, opção satélite, checkbox "Atualizar bases já baixadas", log. Ligado em `geobr_qgis_plugin.py` (`initGui` adiciona ação na barra/menu "GisBR"; `initProcessing` intacto).

**Regras de recorte / robustez (decisões empíricas do teste em Contagem/RMBH):**
- **Recorte por código** (`code_muni`) para Demografia (municipality/census_tract/weighting_area).
- **Recorte pelo POLÍGONO do município** (`native:clip`, não a bbox-retângulo) para todas as fontes filtradas por bbox — senão traz vizinhos (BH/Betim) e a mancha urbana transborda.
- **Pula camadas com 0 feições** (entram em `pulou` com aviso no log) — não cria camada-tabela vazia.
- **Skip-exists**: fonte já no GeoPackage é pulada (salvo checkbox "Atualizar"); gravação por existência do arquivo (não recria o `.gpkg`).
- **`requer_parquet`**: as 3 fontes v2 pulam com aviso se não houver driver GDAL Parquet/`pyarrow`.

**6 eixos no painel:** 1. Transportes · 2. Drenagem e Saneamento · 3. Demografia · 4. Ambiental · 5. Educação · 6. Saúde · 7. Urbano · 8. Político-administrativo.

**Validado no QGIS (Diego):** SICAR (WFS por código), painel + combos UF/Município, GeoPackage, recorte por polígono (Contagem), ordem dos grupos. **A validar:** endpoints ArcGIS (ANA/IBAMA), v2 com `pyarrow`, performance do download nacional de escolas/saúde (geobr v1, sem filtro por município → baixa nacional e recorta).

**Fora do escopo (registrado):** `read_statistical_grid` (nacional ~GB; pra depois), `read_health_region`/`read_metro_area`/etc. (multi-município), parecer/KPIs (painel do haCARthon não entra agora).

**Publicação:** **0.3.0 BLOQUEADA (2026-07-02)** pelo scan de segurança do plugins.qgis.org — o dir `scratch/` (scripts de pesquisa com `urllib.request`/`ssl`/`xml.etree`) vazou pro zip → 14 findings. O **código do plugin (core/algorithms/gui) estava limpo**; os achados eram todos do `scratch/`. Corrigido na **0.3.1**: `build-qgis-zip` passou a excluir `scratch/`/`test/`/`tests/`, o `scratch/` foi destrackeado do git, e o `dist/gisbr-0.3.1.zip` foi re-scaneado (0 triggers). **Pendente: Diego re-subir a 0.3.1.** O `.zip` sai da `main` via skill, com i18n EN/PT-BR (`i18n/gisbr_pt.qm`) e `qgisMinimumVersion=3.16`. **A validar no QGIS pelo Diego** (antes de tirar o `experimental`): satélite ao fundo, quilombola só-BH, reload sem erro, endpoints ArcGIS, v2 com pyarrow.

---

## 2. Como o geobr funciona por baixo (arquitetura de referência)

O geobr **não faz geoprocessamento** — é um **catálogo + downloader + loader**. Toda a lógica é:

1. Baixar um **arquivo de metadados** que mapeia `geografia + ano + simplificado` → **URL de download**.
2. Filtrar esse metadado pelos argumentos do usuário.
3. Baixar o arquivo de dados para um **cache local** (evita rebaixar).
4. Carregar como camada vetorial, opcionalmente filtrando por código (estado/município).

> ⚠️ **Descoberta crítica (verificada no código-fonte do pacote Python):** o geobr está em **transição de backend**. Há **dois pipelines coexistindo**:
>
> | | **Legacy (v1.7.0)** | **Atual (v2.0.0)** |
> |---|---|---|
> | Formato | **GeoPackage** (`.gpkg`) | **Parquet** (`.parquet`) |
> | Metadados | `http://www.ipea.gov.br/geobr/metadata/metadata_1.7.0_gpkg.csv` (CSV) | release `geobr_prep_data` no GitHub (API de releases) |
> | Como ler no QGIS | **Nativo** (`QgsVectorLayer(path, name, "ogr")`) | Exige driver Parquet do GDAL **ou** DuckDB |
> | Status no pacote | usado como **fallback** | pipeline **principal** (`read_geobr_v2`) |
>
> O pacote Python implementa `read_geobr_hybrid()`: tenta v2 (parquet), e em caso de falha cai para v1.7.0 (gpkg). **Essa dualidade é exatamente o que define as duas fases deste plugin.**

### Colunas do metadado v1.7.0 (CSV)
```
geo, year, code, download_path, code_abbrev
```
- `geo` → categoria da geografia (ex.: `state`, `municipality`, `census_tract`, `biome`...).
- `year` → ano.
- `download_path` → **URL direta do .gpkg** (contém a substring `simplified` quando é a versão simplificada).
- O geobr filtra simplificado via `download_path.str.contains("simplified")`.

### Mirrors / fallback de URL (do código real)
```
Primário:  http://www.ipea.gov.br/geobr/...
Mirror:    https://github.com/ipeaGIT/geobr/releases/download/v1.7.0/<file_id>
```
O `url_solver()` tenta o primário e, se falhar (status != 200), tenta o mirror do GitHub com o mesmo nome de arquivo. **Replicar essa cadeia de fallback no plugin.**

### CRS e escala
- Todos os dados em **SIRGAS 2000 / EPSG:4674** (geográfico).
- Escala ~1:250.000 na maioria dos casos.
- Para análises métricas em BH, reprojetar para **EPSG:31983 (SIRGAS 2000 / UTM 23S)** — mesma convenção dos projetos `desire_lines` e `pyqgis_113-2021`.

---

## 3. ⚠️ geobr ≠ dados do Censo

**Importante para evitar confusão de escopo:** o geobr entrega **somente geometrias** (polígonos/limites territoriais). **Não há variáveis do censo** (população, renda, domicílios) dentro dele.

Os dados tabulares do censo ficam no **pacote irmão `censobr`** (mesmo time do IPEA), com funções como `read_population()`, `read_households()`, `read_tracts()`. O `censobr` serve **Parquet/Arrow** e enriquece tudo com colunas-chave no padrão do geobr (`code_muni`, `code_state`, `code_weighting`, `code_tract`), feitas justamente para o **join** geometria ↔ tabela.

→ A integração com censo é **Fase 2 / roadmap** (ver §6), não a entrega principal.

---

## 4. Mapeamento geobr → API nativa do QGIS

| Tarefa do geobr | Equivalente nativo no QGIS/Qt/stdlib |
|---|---|
| HTTP GET (metadado/dados) | `QgsBlockingNetworkRequest` + `QNetworkRequest` (ou `QgsFileDownloader` para assíncrono com barra de progresso) |
| Parsear CSV de metadados | módulo `csv` (stdlib) **ou** `QgsVectorLayer` sobre o CSV |
| Cache em disco | `QStandardPaths.writableLocation(CacheLocation)` + `QDir`/`pathlib` → `~/.cache/geobr-qgis/` |
| Carregar `.gpkg` | `QgsVectorLayer(path, name, "ogr")` |
| Filtrar por estado/município | `layer.setSubsetString("code_state = 'MG'")` ou `QgsFeatureRequest` + `QgsExpression` |
| Concatenar múltiplos arquivos | `QgsVectorLayer` em memória + `addFeatures()`, ou `native:mergevectorlayers` via `processing.run` |
| Reprojetar (opcional) | `QgsCoordinateTransform` / `native:reprojectlayer` |
| Adicionar ao projeto | `QgsProject.instance().addMapLayer(layer)` |

**Observação sobre o cache:** o geobr Python usa `~/.cache/geobr/`. Manter um diretório **separado** `~/.cache/geobr-qgis/` para não colidir, mas o layout (um arquivo por `geo_ano_simplificado`) pode ser o mesmo.

---

## 5. Empacotamento: Processing Provider (decisão tomada)

Seguir o estilo do `desire_lines`, mas como **Processing Provider** (mais alinhado a fluxos batch/modelo/console que o Diego usa com OSM2GMNS/NetworkX). Cada `read_*` vira um `QgsProcessingAlgorithm`.

Vantagens: roda na Caixa de Ferramentas, em modelos gráficos, em batch, e via `processing.run("gisbr:read_municipality", {...})` no console Python.

### Estrutura de diretórios alvo
```
geobr-qgis/
├── CLAUDE.md                      # este arquivo
├── metadata.txt                   # metadados do plugin QGIS
├── __init__.py                    # classmethod classFactory(iface)
├── geobr_qgis_plugin.py           # registra/desregistra o provider
├── provider.py                    # GeobrProvider(QgsProcessingProvider)
├── core/
│   ├── __init__.py
│   ├── catalog.py                 # download + parse do metadado, filtro por geo/ano/simplified
│   ├── downloader.py              # QgsBlockingNetworkRequest + cadeia de mirrors + cache
│   ├── loader.py                  # bytes/path .gpkg -> QgsVectorLayer, filtro por código
│   └── constants.py               # URLs, EPSG, mapa geo->função, anos disponíveis
├── algorithms/
│   ├── __init__.py
│   ├── base_read_algorithm.py     # classe-base com params comuns (ano, código, simplified, output)
│   ├── read_state.py
│   ├── read_municipality.py
│   ├── read_census_tract.py
│   └── ...                        # demais geografias
├── resources.qrc / icon.png
├── Makefile                       # compile/deploy via symlink (padrão dos outros plugins)
└── README.md
```

### Classe-base dos algoritmos (parâmetros comuns)
Todos os `read_*` compartilham:
- `YEAR` (`QgsProcessingParameterEnum` populado a partir do catálogo) — default = ano mais recente.
- `CODE` (`QgsProcessingParameterString`) — `"all"`, sigla (`"MG"`), código IBGE (`31`, `3106200`).
- `SIMPLIFIED` (`QgsProcessingParameterBoolean`) — default `True` (renderização rápida).
- `OUTPUT` (`QgsProcessingParameterFeatureSink` ou `QgsProcessingParameterVectorDestination`).

Fluxo do `processAlgorithm()`:
1. `catalog.select(geo, year, simplified)` → URL(s).
2. `downloader.fetch(url)` → caminho local no cache (com fallback de mirror).
3. `loader.load(path, code)` → `QgsVectorLayer` já filtrado por `setSubsetString`.
4. materializar no `sink` (iterar features) e retornar `{OUTPUT: dest_id}`.

> ⚠️ **Lembrete de padrão do Diego (visto no `desire_lines`):** assinaturas de algumas APIs do PyQGIS variam entre versões do QGIS 3.x. Validar `QgsBlockingNetworkRequest` e `setSubsetString` no QGIS local antes de assumir comportamento.

---

## 6. Plano em DUAS FASES

### 🟢 FASE 1 — Backend GPKG legacy (v1.7.0) — entrega principal

**Meta:** espelho fiel do geobr, 100% API nativa, **sem nenhuma surpresa de driver**.

1. **`core/catalog.py`**
   - Baixar `metadata_1.7.0_gpkg.csv` (via `downloader`), parsear com `csv` da stdlib.
   - Funções: `download_metadata()`, `select(geo, year=None, simplified=True)`.
   - `select_year`: se `year` for `None`, usar `max(year)`; senão validar e listar anos disponíveis em erro amigável.
   - `select_simplified`: filtrar por substring `"simplified"` em `download_path`.
   - Cachear o CSV na sessão (memória) e em disco.

2. **`core/downloader.py`**
   - `fetch(url) -> Path`: checar cache em disco primeiro; se ausente, baixar via `QgsBlockingNetworkRequest`.
   - **Cadeia de mirrors** (replicar `url_solver`): tentar IPEA primário → mirror GitHub `releases/download/v1.7.0/<file_id>`.
   - Gravar em `~/.cache/geobr-qgis/<file_id>`; validar `size > 0`.

3. **`core/loader.py`**
   - `load(path, code="all") -> QgsVectorLayer`: abrir com driver `ogr`.
   - `filter_by_code`: traduzir sigla→código quando necessário e montar `setSubsetString` na coluna certa (`code_state`, `abbrev_state`, `code_muni`...). Tabela de siglas/códigos IBGE (UF 11–53, exceto 20/30/40) já mapeada no `_filter.py` do geobr — portar.

4. **`algorithms/`** — começar pelas geografias mais usadas:
   - `read_state`, `read_municipality`, `read_census_tract`, `read_weighting_area`, `read_metro_area`, `read_biomes`.
   - Depois expandir para o catálogo completo (ver lista em §7).

5. **`provider.py` + `metadata.txt` + `Makefile`** — registrar todos os algoritmos; deploy por symlink para `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`.

**Critério de pronto da Fase 1:** `processing.run("gisbr:read_municipality", {"CODE": "MG", "SIMPLIFIED": True})` retorna camada de municípios de MG no QGIS, em EPSG:4674, sem nenhum pacote externo. (`YEAR` é índice do enum de anos; omitido, usa o mais recente.)

---

### 🟡 FASE 2 — Backend Parquet (v2.0.0) + integração censobr — roadmap

**Meta:** acessar o catálogo mais novo/completo (v2) e habilitar **join com dados do censo**.

> 🔧 **Progresso Fase 2 (2026-06-23) — camada independente do driver, implementada e validada:**
> - `core/capabilities.py` — `parquet_available()` (testa drivers `Parquet`/`Arrow` do OGR) + `install_hint()`. **Resultado na máquina do Diego: driver AUSENTE.**
> - `core/catalog_v2.py` — lista assets `.parquet` do release `ipea/geobr_prep_data` via API do GitHub (`json` da stdlib + `QgsBlockingNetworkRequest`), parse `geo/year/simplified`, suporte a `zone` (setores 2000), cache em disco. **Validado contra os 503 assets reais do v2.0.0** (anos até 2025).
> - `constants.py` — `GEO_BY_FUNCTION_V2` (mapa função→token v2, **plural**: `states`, `municipalities`, `censustracts`...), **28/28 tokens conferidos** contra os assets; URLs/relase v2; cadeia **invertida** (GitHub primário → IPEA fallback `data_v2.0.0/`).
> - ✅ **Leitura v2 IMPLEMENTADA (2026-06-23, decisão: backend `pyarrow`):** em vez de exigir o driver GDAL, o plugin lê GeoParquet via **cadeia de backends** — driver GDAL nativo (Windows/Mac/conda) → **`pyarrow`** (fallback Linux apt/flatpak) → erro orientado. Decisão do Diego: pode instalar pacote python (`pip install --user pyarrow`); manter o "máximo QGIS" como caminho primário.
>   - `core/capabilities.py`: + `pyarrow_available()`, `parquet_backend()` ('gdal'|'pyarrow'|None).
>   - `core/loader_v2.py`: lê .parquet → QgsVectorLayer. Backend pyarrow decodifica WKB (coluna do metadado GeoParquet `geo`) → `QgsGeometry.fromWkb`, monta camada em memória; CRS do metadado ou default 4674; **arquivos sem geometria (censobr) viram camada NoGeometry**. Validado end-to-end com geoparquet sintético.
>   - `core/downloader.py`: + `fetch_v2()` (cadeia invertida GitHub→IPEA) + `_fetch_to_cache()` reusável.
>   - `algorithms/base_read_v2_algorithm.py` + `algorithms/v2_factory.py`: **28 algoritmos `read_*_v2`** gerados dinamicamente (grupo "Geografias (Parquet / v2.0.0)", ids com sufixo `_v2`). Filtro por código é **pós-load** (arquivos v2 são nacionais), via `QgsExpression` (funciona em camada OGR e em memória). Inclui as 3 só-v2: `read_favela_v2`, `read_polling_places_v2`, `read_quilombola_land_v2`.
>   - **Validado:** 54 algoritmos (26 v1 + 28 v2) instanciam, nomes únicos; `read_state_v2` CODE=MG → 1 feição, geom válida, EPSG:4674 (backend pyarrow, download mockado).
> - ✅ **`join_censo` IMPLEMENTADO (2026-06-23) — critério de pronto da Fase 2 atingido:**
>   - `core/catalog_censo.py`: lista os datasets de setor (`*_tracts_*`) dos releases do `ipeaGIT/censobr`; anos **2000, 2010, 2022**; datasets por ano (ex.: 2010 → Basico, Domicilio, **DomicilioRenda**, Pessoa, PessoaRenda...). Dedup por versão mais alta.
>   - `algorithms/join_censo.py` (grupo "Censo (censobr)"): recebe camada de setores do geobr + ano + dataset, baixa o parquet do censobr (`downloader.fetch_asset`), lê como tabela (loader_v2) e junta por **`code_tract`** via `native:joinattributestable` (METHOD 1, prefixo configurável). Avisa se os **tipos da chave divergirem** e reporta `JOINED_COUNT`/`UNJOINABLE_COUNT` (evita o "join silencioso vazio").
>   - **Validado end-to-end** (pyarrow): setor geobr + censobr DomicilioRenda → camada com `censo_V001`/`censo_V002`; 2 de 3 setores casaram, não-match = NULL. **55 algoritmos no total** (26 v1 + 28 v2 + join).
> - ⏭️ **Pendência única:** validar com **dados reais** na máquina do Diego (download real do parquet geobr v2 + censobr). pyarrow já confirmado lendo setores de MG reais. Atenção: arquivos de setor do censobr são NACIONAIS (download pesado); o join mantém só os setores da camada de entrada.
> - ✅ **Mismatch de tipo da chave RESOLVIDO (2026-06-23, com dados reais):** confirmado na máquina do Diego que `code_tract` é **double** no geobr v2 e **string** no censobr → join nativo dava 0. O `join_censo` agora **normaliza a chave para texto nos dois lados** (`to_string(to_int(...))` via `native:fieldcalculator`), junta pela chave normalizada e remove a coluna auxiliar (`native:deletecolumn`). Validado: input double × censo string → casa corretamente. Também confirmado com dados reais que `read_census_tract_v2 CODE=3106200` → 5167 setores de BH (filtro `code_muni`).
>
> ⚠️ **CORREÇÃO empírica sobre o driver (verificado no Pop!_OS 'noble', GDAL 3.8.4):** o caminho via apt **NÃO funciona** nesta build:
> - `gdal-plugins` (3.8.4) **está instalado mas não traz nenhum `.so`** (só um `drivers.ini`) — ou seja, não inclui o driver arrow/parquet.
> - **Não há** `libarrow-dev`/`libparquet-dev`/`libarrow-glib-dev` no apt do noble para compilar o plugin.
> - `ubuntugis-unstable` historicamente também não distribui o plugin arrow.
>
> **Caminhos reais (Pop!_OS/Ubuntu):** (a) ~~**QGIS via Flatpak**~~ — **TESTADO E DESCARTADO**; ou (b) **conda-forge** `libgdal-arrow-parquet` casando a versão do GDAL. A mensagem do `capabilities.install_hint()` já reflete isso. Mantida a decisão: **não montar pipeline de conversão.**
>
> ❌ **Flatpak descartado empiricamente (2026-06-23):** o build flathub `org.qgis.qgis` **não embute o driver GeoParquet de vetor** — testado em GDAL 3.5.2 (LTS antigo) e GDAL **3.13.0** (Stable atual). Em `/app/lib/gdalplugins/` há `ogr_ADBC.so` (Arrow *Database* Connectivity ≠ leitura de arquivo Parquet), mas **não** `ogr_Parquet.so`/`ogr_Arrow.so`. `ogrinfo --formats | grep -i parquet` volta vazio. → **Restou conda-forge** como caminho confiável. Ideia enxuta: `conda create -n qgis-parquet -c conda-forge qgis libgdal-arrow-parquet`, e fazer o deploy do plugin no perfil desse QGIS.

> ⚠️ **Dependência da Fase 2 — driver Parquet do GDAL:** o QGIS só lê Parquet se o driver `Parquet`/`Arrow` do GDAL estiver presente. As builds **oficiais do QGIS (Windows/Linux)** normalmente já vêm com suporte a GeoParquet; a build do **apt do Ubuntu/Pop!_OS pode não vir** (há relatos no Ubuntu 24.04). O driver é distribuído **à parte** do GDAL core (`libgdal-arrow-parquet`).
>
> **Decisão (Diego):** se faltar, **instalar o driver** — não montar pipeline de conversão. Detectar primeiro, e se ausente, orientar a instalação.
>
> **Detecção** (no startup do provider):
> ```python
> from osgeo import ogr
> has_parquet = ogr.GetDriverByName("Parquet") is not None
> ```
> ou via PyQGIS: `"Parquet" in [d.shortName() for d in QgsProviderRegistry.instance()...]` — na prática o teste do `ogr` acima é o mais direto.
>
> **Instalação do driver (Ubuntu / Pop!_OS):**
> ```bash
> # Opção A — apt (build do sistema). Pode exigir o PPA ubuntugis:
> sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable
> sudo apt update
> sudo apt install gdal-plugins        # fornece o driver Parquet/Arrow
> # verificar:
> ogrinfo --formats | grep -i parquet
>
> # Opção B — conda-forge (se o QGIS/GDAL for de ambiente conda):
> conda install -c conda-forge libgdal-arrow-parquet
> ```
> **Importante:** a versão do `libgdal-arrow-parquet` precisa **casar exatamente** com a versão do GDAL do QGIS, senão o plugin não carrega. Conferir `gdalinfo --version` antes.
>
> Como isso depende do ambiente da máquina (não é `pip`), a Fase 2 continua como **roadmap separado**: o plugin **detecta** o driver e, se ausente, mostra mensagem amigável com o comando de instalação acima — em vez de quebrar.

1. **Detecção de capacidade** (`core/catalog.py`):
   - Checar driver Parquet do GDAL no startup. Expor flag `PARQUET_AVAILABLE`.
   - Se indisponível, os algoritmos v2 ficam desabilitados/avisam, e o plugin opera só em Fase 1.

2. **Metadado v2** (`core/catalog_v2.py`):
   - Listar assets via API de releases do GitHub: `api.github.com/repos/ipea/geobr_prep_data/releases/latest`.
   - Extrair `geo`, `year`, `simplified` do nome do arquivo `.parquet` (regex, como no `download_metadata_v2`).
   - Fallback para tag fixa `v2.0.0` se `latest` falhar.

3. **Leitura Parquet** (se driver disponível):
   - `QgsVectorLayer(path, name, "ogr")` funciona sobre `.parquet` quando o driver existe.
   - Filtro por código continua via `setSubsetString`.

4. **Integração censobr (join geometria ↔ censo):**
   - Algoritmo `join_censo`: recebe uma camada do geobr + um dataset censobr (`read_tracts`, `read_population`...).
   - Baixar parquet do censobr (releases do `censobr`), juntar pela chave (`code_tract` / `code_muni` / `code_weighting`) via `native:joinattributestable` ou `QgsVectorLayer.addJoin`.
   - Com o driver Parquet instalado (§ ressalva acima), o censobr abre direto como camada/tabela (`QgsVectorLayer(path, name, "ogr")`) — sem etapa de conversão. A única exigência é o mesmo driver da Fase 2 já estar presente.

**Critério de pronto da Fase 2:** dado o setor censitário de BH (geometria, Fase 1) + `read_tracts(2010, "DomicilioRenda")` (censobr), produzir um mapa coroplético de renda por setor — tudo dentro do QGIS.

---

## 7. Catálogo de geografias (do `list_geobr` real)

Geografias a implementar como algoritmos (ordem de §6.4 prioriza as primeiras):

`read_country`, `read_region`, **`read_state`**, `read_meso_region`, `read_micro_region`, `read_intermediate_region`, `read_immediate_region`, **`read_municipality`**, `read_municipal_seat`, **`read_weighting_area`**, **`read_census_tract`**, `read_statistical_grid`, **`read_metro_area`**, `read_urban_area`, `read_amazon`, **`read_biomes`**, `read_conservation_units`, `read_disaster_risk_area`, `read_indigenous_land`, `read_semiarid`, `read_health_facilities`, `read_health_region`, `read_neighborhood`, `read_schools`, `read_comparable_areas`, `read_urban_concentrations`, `read_pop_arrangements`, `read_favela`, `read_polling_places`, `read_quilombola_land`.

Fontes: IBGE (maioria), MMA (amazônia/UCs), FUNAI (terras indígenas), CNES/DataSUS (saúde), INEP (escolas), TSE (locais de votação), INCRA (quilombolas).

> ⚠️ O nome da `geo` no metadado v1.7.0 **difere** do nome da função (ex.: função `read_state` → `geo == "state"`; `read_municipality` → `geo == "municipality"`). Em caso de dúvida, baixar o CSV e inspecionar os valores únicos de `geo` antes de hardcodar. Em v2 os nomes mudam de novo (ex.: `"municipalities"` no plural). Manter um **dicionário de mapeamento** em `constants.py` por backend.

---

## 8. Stack / APIs PyQGIS de referência

- `qgis.core`: `QgsVectorLayer`, `QgsProject`, `QgsFeatureRequest`, `QgsExpression`, `QgsCoordinateReferenceSystem`, `QgsCoordinateTransform`, `QgsBlockingNetworkRequest`, `QgsFileDownloader`, `QgsProcessingProvider`, `QgsProcessingAlgorithm`, `QgsProcessingParameter*`, `QgsProcessingParameterFeatureSink`.
- `qgis.PyQt.QtCore`: `QStandardPaths`, `QDir`, `QUrl`, `QEventLoop`.
- `qgis.PyQt.QtNetwork`: `QNetworkRequest`, `QNetworkReply`.
- stdlib: `csv`, `pathlib`, `tempfile`, `re`, `unicodedata` (para `strip_accents` em nomes), `json` (releases v2).
- `processing`: `processing.run(...)` para reaproveitar `native:*` (merge, join, reproject) em vez de reimplementar.

**CRS:** entrada EPSG:4674; reprojeção opcional para EPSG:31983 (UTM 23S, BH).

---

## 9. Fluxo de desenvolvimento (CLI, padrão Diego)

```bash
# Clonar / posicionar
cd ~/Documentos/SIG/geobr-qgis/

# Compilar resources (se houver .qrc) e fazer deploy por symlink
make compile
make deploy        # symlink -> profiles/default/python/plugins/geobr_qgis

# Recarregar no QGIS: usar o Plugin Reloader, ou reiniciar o QGIS.
# Testar no Console Python do QGIS:
#   import processing
#   processing.run("gisbr:read_state", {"CODE":"all","SIMPLIFIED":True,"OUTPUT":"memory:"})  # YEAR omitido = ano mais recente (enum)
```

- Desenvolvimento e testes rodam na **máquina principal Pop!_OS** (mesmo fluxo do `desire_lines`).
- Versionar tudo; `CLAUDE.md` é o documento de contexto persistente — manter atualizado a cada mudança de backend do IPEA.

---

## 9.1. Status da Fase 1 (implementado) — 2026-06-23

🟢 **Fase 1 concluída e validada** (QGIS 3.34 Prizren, GDAL 3.8.4, sem driver Parquet).

- Provider `geobr` com **26 algoritmos `read_*`** registrados, cobrindo **26 dos 29** valores de `geo` do metadado v1.7.0.
- Núcleo 100% PyQGIS + stdlib: `core/{constants,downloader,catalog,loader}.py`. Cache em `~/.cache/geobr-qgis/`.
- Descobertas verificadas no CSV real (já refletidas no código):
  - `meso_region` e `micro_region` **também são fatiados por UF** (`UF_SLICED`), como `municipality`/`census_tract`/`weighting_area`/`state` (recente).
  - Geografias de **pontos sem versão simplificada** (`schools`, `health_facilities`, `municipal_seat`, `statistical_grid`): `catalog.select()` tem **fallback** simplificado↔não-simplificado.
  - `statistical_grid` é fatiado em ~56 arquivos de grade → sem filtro baixa o Brasil inteiro (vários GB). Marcado com aviso; sem recorte fino na Fase 1.

### ⏸️ Itens do catálogo NÃO implementados (talvez mais pra frente)
Decisão consciente — não é esquecimento. Reavaliar quando houver demanda:

| Item | Função geobr | Motivo de ter ficado de fora |
|---|---|---|
| `amc` | `read_comparable_areas` | Assinatura diferente: `start_year` + `end_year` (áreas mínimas comparáveis entre dois censos). Exige classe-base própria com dois parâmetros de ano — não encaixa na `BaseReadAlgorithm` de `YEAR` único. |
| `health_region_macro` | (variante de `read_health_region`) | No geobr é um parâmetro `macro=True` da mesma função, não geografia separada. Encaixar depois como booleano `MACRO` no `read_health_region`. |
| `lookup_muni` | `lookup_muni()` | **Não é geometria** — tabela de consulta código↔nome. Candidata a virar helper interno (tradução sigla/código), não um `read_*`. |

Geografias **só-v2** (não existem no metadado v1.7.0, ficam para a Fase 2): `read_favela`, `read_polling_places`, `read_quilombola_land`.

---

## 10. Notas / armadilhas conhecidas

- **Backend instável:** o IPEA já migrou de GPKG→Parquet uma vez. **Não hardcodar URLs sem fallback.** Sempre cadeia: primário IPEA → mirror GitHub.
- **`verify=False` no geobr Python:** o pacote desativa verificação SSL em alguns downloads. No QGIS, preferir a verificação padrão; se houver erro de certificado no IPEA, documentar e decidir conscientemente — não copiar o `verify=False` cegamente.
- **Tamanho dos arquivos:** geografias nacionais não-simplificadas (ex.: todos os setores censitários do Brasil) são pesadas. Default `simplified=True`; baixar por estado quando possível (passar `CODE` antes de baixar nacional inteiro só não é possível no v1.7.0, onde o filtro é pós-download — avaliar baixar por UF quando o metadado tiver granularidade por estado).
- **Nomes de `geo` divergentes entre v1.7.0 e v2.0.0:** manter mapeamentos separados.
- **Parquet via driver instalável:** a Fase 2 depende do driver GDAL Parquet (`libgdal-arrow-parquet` / `gdal-plugins`). Builds oficiais do QGIS costumam trazer; apt do Ubuntu pode não. **Detectar e, se faltar, orientar a instalação** (comandos em §6) — a versão do driver deve casar com a do GDAL do QGIS.
- **censobr é Parquet/Arrow:** com o driver instalado, abre direto como tabela no QGIS e o join com a geometria roda via `native:joinattributestable` — sem conversão intermediária.
- **`%` literal no `metadata.txt` quebra o upload (plugins.qgis.org):** o validador do repo oficial usa `configparser` com interpolação, então `%` é lido como início de token e falha com `'%' must be followed by '%' or '('`. Aconteceu com "100% native"/"100% PyQGIS" no `about`/`changelog` (v0.3.0). **Regra: evitar `%` no `metadata.txt`** (reescrever, ex.: "fully native"); se for inevitável, escapar como `%%`. Validar antes de subir: `python3 -c "import configparser as c; p=c.ConfigParser(); p.read('metadata.txt'); [p.get('general',k) for k in ('about','description','changelog')]"` — não pode lançar erro.
- **Scan de segurança do plugins.qgis.org (tipo Bandit) — NÃO deixar scripts de pesquisa no pacote:** o repo roda um scanner que **BLOQUEIA** o plugin por padrões como `urllib.request.urlopen` (B310), `xml.etree`/`ElementTree.parse` (B314/B405), `ssl._create_unverified_context`/`CERT_NONE` (B323), `eval`/`exec`/`pickle`/`subprocess`/`yaml.load`. Aconteceu na **0.3.0**: o dir `scratch/` (scripts de varredura de geoservers) vazou pro zip → 14 findings, upload bloqueado. **Regra: `scratch/` (e qualquer script de pesquisa/dev) NÃO entra no pacote** — a skill `build-qgis-zip` exclui `scratch/`/`test/`/`tests/`, e o `scratch/` está no `.gitignore`. **Antes de subir, re-scaneie os `.py` do zip** por esses padrões (o núcleo do plugin usa a pilha de rede do QGIS, não `urllib.request`, então deve dar limpo).
- **i18n (Qt tr) — contexto tem de casar entre runtime e extração:** classes `QgsProcessingAlgorithm`/`QgsProcessingProvider` **não** têm `tr` nativo do QObject por padrão (o provider tem; o **algoritmo não** — precisa `def tr` próprio). O `pylupdate5` grava a string pelo **nome da classe**; então o `tr` custom deve usar `QCoreApplication.translate("<NomeDaClasse>", ...)`, não um contexto genérico, senão a tradução não é encontrada. Usar **`pylupdate5`** (não `lupdate`) para capturar `self.tr` em Python. Ver T-023/T-025/T-027.

---

## 11. Referências

- geobr (repo): `github.com/ipeaGIT/geobr` — código Python em `python-package/geobr/`, lógica de backend em `utils.py`, `_cache.py`, `_filter.py`.
- censobr (repo): `github.com/ipeaGIT/censobr` — funções `read_tracts`, `read_population` etc.
- Metadado legacy: `metadata_1.7.0_gpkg.csv` (IPEA).
- Dados v2: releases do repo `ipea/geobr_prep_data`.
- PyQGIS Cookbook (Processing providers, network). Validar APIs na versão local do QGIS.
