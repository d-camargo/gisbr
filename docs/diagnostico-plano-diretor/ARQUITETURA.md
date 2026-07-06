# Arquitetura — GisBR: Diagnóstico para Plano Diretor

> Documento de desenho. As decisões foram tomadas e a Fase A/B está
> **implementada** na branch `feat/diagnostico-plano-diretor` (T-008…T-019).
> O estado implementado (módulos, motor, painel, 29 fontes, regras de recorte)
> está resumido em `CLAUDE.md` §1.2; o detalhe de cada tarefa em `ACTIONS.md`.
> Este doc mantém o desenho/decisões que guiaram a implementação.
> Fonte de dados: pesquisa em `docs/diagnostico-plano-diretor/`
> (taxonomia, panorama, e os 6 eixos com endpoints `GetCapabilities` verificados).

## 1. Objetivo

Evoluir o GisBR de "espelho do geobr" para um **sistema de diagnóstico
municipal** voltado ao Plano Diretor: dado **um município** (`code_muni`, IBGE 7
dígitos), subir no QGIS as camadas oficiais dos **8 eixos** (transportes,
saneamento, demografia, ambiental, educação, saúde, urbano, político-administrativo),
reaproveitando o que já existe e adicionando conectores para fontes externas.

## 2. Princípios (herdados + novos)

- **Mantém o espelho geobr intacto.** Os `read_*`/`read_*_v2`/`join_censo`
  continuam como estão; o diagnóstico cresce **ao lado**, no mesmo provider.
- **PyQGIS + stdlib primeiro.** Rede pela pilha do QGIS (`QgsBlockingNetworkRequest`),
  sem libs novas. `pyarrow` segue como única exceção (Parquet).
- **Município-cêntrico.** O eixo organizador é `code_muni`. Sempre que o serviço
  permitir, **filtrar no servidor** (WFS `CQL_FILTER`, ArcGIS `where`) para baixar
  só o município — não o Brasil inteiro.
- **Declarativo > imperativo.** Fontes descritas como **dados** (um catálogo),
  não uma função escrita à mão por fonte. Generaliza a filosofia de catálogo do
  geobr e reduz o código QGIS por fonte (importante: o Junior é mais forte em
  pesquisa/dados do que em PyQGIS).
- **Rastreabilidade.** Toda camada carregada grava `data_extracao` e `fonte`
  (disciplina herdada do `desafio-2`).

## 3. Visão em camadas

```
                ┌─────────────────────────────────────────────┐
                │  Provider "gisbr" (QgsProcessingProvider)    │
                │                                              │
   geobr (já)   │  Grupos existentes:                          │
   ───────────► │   • Geografias (GPKG / v1.7.0)   26 alg      │
                │   • Geografias (Parquet / v2.0.0) 28 alg     │
                │   • Censo (censobr)  join_censo              │
                │                                              │
   NOVO         │  Grupos novos (Diagnóstico), 1 por eixo:     │
   ───────────► │   • Diagnóstico — Transportes               │
                │   • Diagnóstico — Saneamento                │
                │   • ... (8 eixos)                            │
                └───────────────┬──────────────────────────────┘
                                │ algoritmos gerados por factory
                                ▼
   core/sources.py  ── catálogo declarativo de FONTES (registry)
                                │  {id, eixo, protocolo, endpoint,
                                │   layer/typeName, crs, campo_muni, licença}
                                ▼
   core/connectors/ ── 1 conector por PROTOCOLO:
        wfs.py        (vetor; GeoJSON via rede do QGIS + CQL_FILTER; /vsicurl fallback)
        arcgis_rest.py(vetor; FeatureServer query where=; ou GDAL)
        basemap.py    (raster; QgsRasterLayer provider "wms" — XYZ Esri World Imagery)
        geobr (já existe via catalog/loader) — para eixos já cobertos
```

### 3.1 Catálogo de fontes (`core/sources.py`) _(proposta)_

Uma estrutura declarativa (lista de dicts) é a **espinha** do diagnóstico. Ex.:

```python
SOURCES = [
  {
    "id": "transportes_dnit_snv",
    "eixo": "transportes",
    "nivel": "federal",
    "protocolo": "wfs",
    "endpoint": "https://geoservicos.inde.gov.br/geoserver/DNIT/ows",
    "type_name": "DNIT:snv_202507a",
    "crs": "EPSG:4674",
    "campo_muni": None,          # filtro por UF/bbox quando não houver campo muni
    "output_format": "application/json",
    "licenca": "Open Data",
    "fonte": "DNIT (via INDE)",
  },
  # ... uma entrada por fonte verificada nos eixos
]
```

> O preenchimento fiel de `type_name`, `crs`, `output_format` e **`campo_muni`**
> vem da T-007 (hardening do catálogo) — ver §6.

### 3.2 Conectores (`core/connectors/`)

- **`wfs.py`** — **portar/adaptar do `desafio-2`** (`src/plugin-qgis/core/wfs.py`,
  já em `desafio-2-port/` como referência). Padrão validado: GeoJSON por
  `QgsBlockingNetworkRequest` (respeita SSL/proxy do QGIS), fallback GDAL
  `/vsicurl/`, `CQL_FILTER` por município, `data_extracao` na camada.
- **`arcgis_rest.py`** — provider nativo `arcgisfeatureserver` do QGIS (ou GDAL
  `ESRIJSON`), com `where` por código municipal. Para ANA (BHO) e IBAMA.
- **`basemap.py`** — **imagem de satélite de fundo** via **XYZ tiles** (Esri
  World Imagery): `QgsRasterLayer("type=xyz&url=...World_Imagery.../tile/{z}/{y}/{x}",
  "Esri World Imagery", "wms")`. **Decisão do Diego:** WMS temático (MapBiomas
  Alertas, OSM) fica **fora** do MVP; o que entra é só este **basemap de
  satélite**. Precedente e detalhes em `referencia-satelite-hacarthon.md`.

### 3.3 Motor de orquestração (`core/diagnostico.py`)

Função central reutilizada pelo painel **e** por qualquer algoritmo de Processing:

```python
def carregar_fontes(source_ids, code_muni, nome_muni, bbox, gpkg_path,
                    add_basemap=False, force=False, feedback=None):
    # para cada fonte selecionada: conector busca (filtrado por code_muni/bbox)
    #   -> recorta pelo POLIGONO do municipio (native:clip), pula se 0 feicoes
    #   -> grava a camada no GeoPackage (uma camada por fonte; skip se ja existe,
    #      salvo force=True) -> adiciona ao projeto a partir do .gpkg
    # eixos ja cobertos pelo geobr (demografia/educacao/saude) usam os read_* atuais
    # opcional: adiciona o basemap de satelite ao fundo
```

### 3.4 Painel de diagnóstico (`gui/diagnostico_dock.py`) — **UX principal**

**Decisão do Diego:** a interface principal é um **dock (painel)**, para não abrir
várias janelas/diálogos do Processing. Hoje o plugin é só Processing provider
(`geobr_qgis_plugin.py` → `initGui` só registra o provider); vamos **adicionar**
ali um botão de barra/menu que abre um `QgsDockWidget`.

Conteúdo do painel (proposta):
- **Município alvo**: campo `code_muni` (IBGE 7 díg.) — ou busca por nome/UF.
- **Seleção de bases**: árvore agrupada por eixo, com **checkbox por fonte**
  (multi-seleção) + "marcar todas do eixo". _(Recomendado vs. "uma por vez" —
  ver §6.)_ As fontes vêm do `core/sources.py`.
- **GeoPackage de saída**: seletor de arquivo `.gpkg` (ver §3.5).
- **Opção** "adicionar imagem de satélite ao fundo" (basemap XYZ Esri).
- Botão **"Carregar selecionadas"** → chama `core.diagnostico.carregar_fontes(...)`
  com barra de progresso; reporta o que casou/falhou por fonte.

> KPIs/parecer continuam **fora** (ver §3.6). O painel aqui é **carregador de
> camadas**, não relatório de indicadores.

### 3.5 Persistência: **GeoPackage local** _(decisão Diego)_

Tudo que for baixado é **gravado num GeoPackage local** (uma camada por fonte),
e o painel **pede o caminho de salvamento**. Padrão sugerido de nome:
`diagnostico_<code_muni>.gpkg`.

- Escrita: `QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, ctx, options)`
  com `options.driverName="GPKG"`, `options.layerName=<id_da_fonte>`, e
  `actionOnExistingFile = CreateOrOverwriteFile` na 1ª camada e
  `CreateOrOverwriteLayer` (append de camadas) nas seguintes.
- Vantagens: um único arquivo por município (portátil), camadas reusáveis sem
  rebaixar, e o diagnóstico fica reproduzível.
- O basemap de satélite **não** vai pro GeoPackage (é raster XYZ remoto; entra só
  como camada de fundo no projeto).

### 3.6 Relatório / KPIs — **FORA do escopo atual** _(decisão Diego)_

Os **indicadores/parecer** do haCARthon (`parecer.py`/`kpis_dock.py`) **não**
entram agora. (Isto é diferente do **painel de carregamento** do §3.4, que
está IN.) Por ora o diagnóstico só **carrega e persiste** as camadas por eixo.

## 4. Filtro por município (peça-chave)

| Protocolo | Como filtrar pelo município | Observação |
|---|---|---|
| WFS | `CQL_FILTER` no GET (server-side) | ideal; precisa do **campo** certo (T-007) |
| ArcGIS REST | `where=<campo>='<code>'` na query | idem |
| basemap (satélite) | não filtra (raster XYZ) | fundo global; usuário dá zoom no município |
| geobr (já) | pós-download (`setSubsetString`) ou fatiado por UF | como hoje |

Quando a fonte **não** tiver campo municipal, filtrar por **bbox do município**
no servidor e, no cliente, **recortar pelo POLÍGONO do município** (`native:clip`,
não a bbox-retângulo) — senão vêm vizinhos (BH/Betim) e a mancha urbana transborda
(decisão empírica em Contagem/RMBH). Camadas com **0 feições** após o recorte são
**puladas** (não vira camada-tabela vazia).

## 5. Fases de implementação _(proposta)_

- **Fase A — Motor WFS + persistência GeoPackage + basemap.** `core/sources.py`
  + `core/connectors/wfs.py` (portado) + `core/connectors/basemap.py` +
  `core/diagnostico.py` (motor: busca → grava no `.gpkg` → adiciona ao projeto).
  MVP de engine, testável pelo Console antes da GUI.
- **Fase B — Painel (dock).** `gui/diagnostico_dock.py`: município + seleção por
  checkbox (por eixo) + caminho do GeoPackage + botão "Carregar". Ligado em
  `initGui`. **É a UX principal** (decisão Diego).
- **Fase C — ArcGIS REST.** ✅ **feita** — `core/connectors/arcgis_rest.py` +
  5 fontes `arcgis` no `SOURCES` (ANA/BHO, IBAMA), no mesmo motor/painel.
- ~~Parecer/KPIs~~ — **fora do escopo atual** (decisão Diego).

> Nota: o painel subiu para a Fase B (logo após o motor) porque é a interface que
> o Diego quer usar. Algoritmos de Processing por fonte (factory) ficam
> **opcionais/secundários** — o motor `carregar_fontes` já serve a GUI; expor
> como Processing pode vir depois, de graça, a partir do mesmo registry.

## 6. Decisões (resolvidas em 2026-06-29)

1. **Modelo declarativo** (registry como dados). ✅ **Sim.**
2. **Fase A só com WFS** (+ basemap). ✅ **Sim.**
3. **UX = painel (dock)**, não diálogos de Processing. ✅ **Sim** — o usuário não
   quer abrir várias janelas. (Atenção: isto é o **painel carregador**, ≠ KPIs.)
4. **Seleção de bases no painel:** **checkbox multi-seleção por eixo.** ✅ **Sim**
   (decisão Diego) — marca-se várias e carrega de uma vez; combina com "não abrir
   várias janelas".
5. **Persistência:** tudo baixado vai para um **GeoPackage local** (1 camada por
   fonte); o painel **pede o caminho** de salvamento. ✅ **Sim.**
6. **Parecer/KPIs:** ❌ **Fora por ora** (≠ painel carregador, que está IN).
7. **WMS temático (MapBiomas/OSM):** ❌ **Fora.** Entra só o **basemap de satélite
   (XYZ Esri World Imagery)** como fundo (ver §3.2 e `referencia-satelite-hacarthon.md`).
8. **UI em PT-BR** agora; i18n (inclusive o painel) junto com o resto depois. ✅

## 7. Roadmap de ACTIONS (a desmembrar após §6)

## 8. Proposta nova: ingestão municipal de vias OSM inspirada em OSM2GMNS/GMNS

Esta seção registra uma proposta arquitetural para uma futura função de OSM no
GisBR. A referência conceitual é o fluxo do **OSM2GMNS/GMNS** (extrair, limpar,
normalizar e montar rede), mas a implementação do GisBR deve continuar
**nativa em PyQGIS + stdlib**, sem novas dependências externas, e sempre
recortada ao **polígono do município escolhido**.

### 8.1 Objetivo da função

Adicionar uma capacidade municipal de OSM para:

- buscar vias OpenStreetMap apenas do município selecionado;
- tratar os dados com regras simples e previsíveis;
- gerar uma rede mínima útil para diagnóstico urbano/viário;
- persistir o resultado em GeoPackage para reuso no projeto QGIS.

O foco não é replicar todo o OSM2GMNS, e sim aproveitar a ideia de pipeline em
camadas para construir uma rede municipal enxuta, auditável e fácil de manter.

### 8.2 Como obter o recorte municipal

A função deve reutilizar o fluxo municipal já existente no plugin:

1. identificar o município selecionado (`code_muni`);
2. recuperar ou carregar a geometria do município no projeto;
3. derivar o polígono de recorte a partir dessa camada;
4. usar esse polígono como limite obrigatório para download, filtro e recorte.

Se a origem OSM não permitir filtro espacial server-side, o processo pode baixar
uma área um pouco maior por bbox, mas o resultado final precisa ser cortado pelo
**polígono municipal**, nunca por bbox apenas. Isso evita vazamento de vias de
municípios vizinhos.

### 8.3 Estratégia de download OSM sem dependências novas

O GisBR não deve introduzir bibliotecas como osmium, osmnx, geopandas ou
requests. A estratégia preferencial deve usar:

- a rede do QGIS (`QgsBlockingNetworkRequest`) para chamadas HTTP;
- a stdlib (`json`, `csv`, `zipfile`, `tempfile`, `pathlib`, `urllib.parse`)
  quando fizer sentido;
- formatos simples de resposta, preferencialmente GeoJSON ou JSON;
- cache local para evitar downloads repetidos.

A fonte OSM escolhida deve ser consumida por um conector próprio, com fallback
claro e URL explícita, mas sem codificar uma solução dependente de uma nova
pilha Python. Se a origem suportar consulta por bbox ou por geometria, isso deve
ser usado só como etapa de redução inicial; o recorte final segue sendo local.

### 8.4 Pipeline em camadas inspirado no OSM2GMNS

O fluxo proposto pode ser dividido em cinco etapas:

1. **Extração** — baixar vias OSM do recorte municipal ou da bbox mínima de
   apoio.
2. **Normalização** — padronizar atributos, CRS e geometria em uma forma
   interna única.
3. **Filtragem** — manter apenas modos/tipos de via relevantes para diagnóstico
   municipal (por exemplo, rodovias, arteriais, coletoras, locais e conexões
   essenciais).
4. **Construção topológica básica** — quebrar interseções, gerar nós, enlaces e
   segmentos conectáveis sem tentar resolver toda a complexidade do grafo OSM.
5. **Persistência** — salvar nós, links e metadados em GeoPackage e reutilizar
   o resultado no projeto.

Essa estrutura preserva a lógica do OSM2GMNS, mas evita dependências de grafo
ou modelagem pesada demais para a finalidade do GisBR.

#### 8.4.1 Regra de desenho para o GisBR

O GisBR deve tratar a rede OSM como um insumo municipal de diagnóstico, não
como uma cópia fiel do OSM2GMNS. A implementação precisa continuar nativa em
PyQGIS + stdlib, sem bibliotecas externas novas, e o recorte final sempre deve
ser o polígono do município escolhido.

### 8.5 Proposta de módulos e arquivos

Uma organização mínima e coerente com o projeto pode ser:

- `core/connectors/osm.py` — download e leitura da origem OSM;
- `core/osm_schema.py` — schema interno mínimo de nós, links e metadados;
- `core/osm_pipeline.py` — pipeline de extração, limpeza, recorte e geração da
  rede;
- `algorithms/diagnostico/read_osm_municipal.py` ou ação equivalente no painel —
  ponto de entrada para o usuário;
- `gui/diagnostico_dock.py` — checkbox/opção para carregar a camada OSM
  municipal junto do diagnóstico.

O desenho deve permanecer simples: um conector para dados, um pipeline para
processamento e uma ação de interface para disparo.

#### 8.5.1 Sequência mínima sugerida

1. montar o conector OSM municipal;
2. normalizar a resposta para o schema interno;
3. aplicar o recorte pelo polígono do município;
4. persistir em GeoPackage;
5. expor a ação no painel ou como algoritmo do provider.

### 8.6 Esquema mínimo de atributos em estilo GMNS

O schema interno deve ser enxuto e focado em diagnóstico. Sugestão:

- **Nós**: `node_id`, `x`, `y`, `geometry`, `municipio_id`, `source`, `data_extracao`.
- **Links**: `link_id`, `from_node`, `to_node`, `road_name`, `highway`,
  `mode_class`, `oneway`, `length_m`, `geometry`, `municipio_id`, `source`,
  `data_extracao`.
- **Metadados**: `osm_source`, `bbox`, `municipio_id`, `code_muni`,
  `generated_at`, `crs`.

Se necessário, pode haver campos extras como `lanes` ou `maxspeed`, mas o
núcleo deve ficar restrito ao essencial para não virar um clone completo do
GMNS.

O objetivo é só permitir diagnóstico urbano municipal com atributos mínimos
compatíveis com uma rede simples de vias; não há compromisso com cobertura
total do padrão GMNS.

### 8.7 Regras de recorte

As regras de recorte devem ser explícitas:

- só entram feições dentro do polígono do município selecionado;
- a bbox serve apenas como apoio de busca inicial, nunca como resultado final;
- feições parcialmente externas devem ser cortadas no limite municipal;
- segmentos sem pertinência após o corte devem ser descartados;
- o resultado final precisa ser consistente com o `code_muni` escolhido.

Se a geometria vier em partes ou com interseções, o recorte deve continuar
municipal: primeiro a seleção inicial por bbox/consulta, depois o corte final por
polígono e a eliminação do que sobrar fora do limite.

### 8.8 Cache e saída em GeoPackage

O resultado da função OSM deve ser persistido localmente em GeoPackage, com
cache por município e por origem.

Proposta prática:

- cache bruto da resposta OSM em pasta local do projeto ou cache do usuário;
- camada processada final em `.gpkg` com nomes estáveis por município;
- reaproveitamento do cache quando o mesmo município e a mesma origem forem
  solicitados novamente;
- invalidação simples por data de extração ou mudança de parâmetros.

Assim o usuário não precisa baixar nem recalcular a rede a cada execução.

O cache deve ser leve e previsível: um arquivo bruto por consulta e um arquivo
processado por município/origem, para não multiplicar download nem cálculo.

### 8.9 Riscos e limitações

- OSM varia muito em cobertura e padronização entre municípios.
- A topologia básica pode ser suficiente para diagnóstico, mas não para análise
  de tráfego avançada.
- Algumas origens OSM podem impor limites de consulta, tempo ou tamanho.
- Regras de recorte por polígono podem exigir cuidado com geometrias válidas e
  CRS.
- Excesso de atributos pode tornar o processo lento e difícil de manter.

Também existe risco de dependência excessiva de uma origem OSM específica; a
arquitetura deve aceitar trocar o conector sem reescrever o pipeline.

### 8.10 Fases pequenas e verificáveis

1. **Fase 1 — conector e cache**: buscar OSM municipal e salvar a resposta bruta.
2. **Fase 2 — recorte e normalização**: transformar a resposta em camada vetorial
   municipal válida.
3. **Fase 3 — filtragem viária**: manter apenas tipos de via relevantes.
4. **Fase 4 — topologia mínima**: gerar nós e links conectáveis.
5. **Fase 5 — persistência e GUI**: gravar no GeoPackage e expor no painel.

Cada fase deve ser pequena o bastante para validar no QGIS antes da próxima.

Critério de aceite da proposta: a implementação futura deve poder começar por
um único conector, sem nova dependência, com recorte municipal fechado e saída
em GeoPackage, antes de qualquer refinamento topológico maior.

### 8.11 Respostas já observadas no projeto OSM2GMNS

A inspeção do projeto de referência mostra que algumas das dúvidas desta
arquitetura já têm respostas úteis no próprio OSM2GMNS, ainda que a
implementação do GisBR precise ser reescrita de forma nativa em PyQGIS/stdlib.

**1. Origem de download OSM:** o `osm2gmns/downloader.py` usa a **Overpass API**
(`www.overpass-api.de/api/interpreter`) e baixa dados por **`area_id` de relação
OSM**, salvando um arquivo local `.osm/.xml`. Isso responde qual família de
origem pode embasar o conector municipal do GisBR: uma API OSM consultável por
área, com resposta bruta persistível em disco.

**2. Contrato de entrada do pipeline:** o `osm2gmns.py` trabalha com a ideia de
**arquivo bruto local** como fronteira entre download e tratamento
(`getNetFromFile(filepath, ...)`). Para o GisBR, isso reforça a decisão de ter um
cache bruto da resposta OSM antes do processamento vetorial.

**3. Filtragem viária por modo e tipo:** o projeto já explicita parâmetros como
`mode_types`, `link_types` e `connector_link_types`, com tipos suportados como
`motorway`, `trunk`, `primary`, `secondary`, `tertiary`, `residential`,
`service`, `cycleway`, `footway`, `track`, `unclassified`, `railway` e
`aeroway`. Isso responde boa parte da dúvida sobre a regra de classificação: o
GisBR pode começar com um subconjunto viário municipal inspirado nessa mesma
família de classes OSM.

**4. Regra de recorte de borda:** o parâmetro `strict_boundary=True` em
`getNetFromFile(...)` deixa explícito que o OSM2GMNS trata o recorte da área como
uma decisão de pipeline. Para o GisBR, a adaptação natural é manter a regra mais
estrita: consulta inicial por área/bbox quando necessário, mas corte final pelo
**polígono do município**.

**5. Topologia mínima e consolidação:** o projeto separa a montagem da rede de
pós-processamentos como `consolidateComplexIntersections(...)`,
`generateNodeActivityInfo(...)` e `fillLinkAttributesWithDefaultValues(...)`.
Isso responde a dúvida sobre a ordem do tratamento: primeiro construir a rede
básica, depois aplicar enriquecimentos topológicos e defaults em etapas
separadas.

**6. Atributos mínimos úteis:** o próprio OSM2GMNS prevê extração opcional de
`osm_node_attributes`, `osm_link_attributes` e preenchimento posterior de valores
padrão para `lanes`, `speed` e `capacity`. Para o GisBR, isso confirma que o
schema mínimo pode nascer pequeno (`node_id`, `link_id`, `from_node`, `to_node`,
`highway`, `oneway`, `length_m`) e só depois ganhar atributos extras como
`lanes` e `maxspeed`.

**7. Saída estruturada da rede:** o `outputNetToCSV(...)` mostra que o produto do
OSM2GMNS é uma separação clara entre **nós** e **links** em formato GMNS. Isso
responde diretamente a dúvida de persistência: no GisBR, mesmo sem CSV/GMNS
completo, a saída deve continuar separando ao menos duas camadas lógicas
(`osm_nodes` e `osm_links`) dentro do GeoPackage municipal.

**Implicação para a task:** o OSM2GMNS já responde conceitualmente as perguntas
sobre origem de dados, fronteira download→tratamento, filtros por tipo/modo,
recorte estrito, topologia em etapas, defaults de atributos e separação
nó/link. O que ele **não** resolve para o GisBR é a parte específica de
integração com PyQGIS, recorte por município brasileiro no fluxo atual do plugin
e persistência direta em GeoPackage.

### 8.12 Arquitetura executável de nível 2

A partir do desenho atual do plugin (`gui/diagnostico_dock.py`,
`core/diagnostico.py`, `core/sources.py`) e das respostas observadas no
OSM2GMNS, a próxima etapa já pode ser especificada em nível executável, sem
fechar ainda a implementação.

#### 8.12.1 Fonte e consulta OSM adotadas

A primeira implementação deve assumir um único conector OSM municipal baseado em
**Overpass API**, por ser o caminho mais coerente com o OSM2GMNS e por não exigir
nova dependência Python além da infraestrutura já disponível no QGIS.

Decisão inicial:

- fonte primária: **Overpass API**;
- transporte HTTP: `QgsBlockingNetworkRequest`;
- formato bruto persistido: **JSON do Overpass**;
- estratégia de consulta: **bbox do município como redução inicial**;
- estratégia de verdade espacial final: **clip obrigatório pelo polígono do
  município** obtido via `gisbr:read_municipality`.

Consulta-base sugerida para a Fase 1:

- endpoint: `https://overpass-api.de/api/interpreter`
- método: `POST`
- corpo: consulta Overpass QL com `way["highway"]({south},{west},{north},{east});`

Exemplo lógico de payload:

```text
[out:json][timeout:180];
(
  way["highway"]({south},{west},{north},{east});
);
(._;>;);
out body;
```

Observação: a bbox serve só para reduzir o universo de download. A regra do
GisBR continua sendo a mesma do `core/diagnostico.py`: o resultado final só vale
após recorte pelo polígono municipal.

#### 8.12.2 Conversão município → geometria → bbox

O plugin já resolve município por `code_muni` no `diagnostico_dock.py` e no
`core/diagnostico.py`. A função OSM deve reaproveitar exatamente essa lógica:

1. receber `code_muni` na ação/pipeline;
2. carregar o município via `gisbr:read_municipality`;
3. guardar duas saídas derivadas:
   - **polígono do município** (fonte de verdade para clip);
   - **bbox em EPSG:4674** (apoio para a consulta Overpass);
4. rejeitar a execução se o polígono municipal não puder ser obtido.

Contrato interno mínimo sugerido:

- entrada: `code_muni`
- saída: `{code_muni, nome_muni, bbox_4674, poligono_layer}`

Isso deixa a função OSM alinhada com o padrão já usado em `carregar_fontes(...)`.

#### 8.12.3 Contrato do novo conector `core/connectors/osm.py`

O conector deve seguir o mesmo espírito dos conectores `wfs` e `arcgis_rest`:
ficar responsável apenas por buscar e devolver um artefato bruto ou quase bruto,
sem misturar persistência final nem lógica de GUI.

Proposta de API mínima:

- `fetch_overpass_json(bbox, timeout=180) -> dict`
- `save_overpass_cache(payload, cache_path) -> str`
- `load_overpass_cache(cache_path) -> dict`
- `overpass_cache_key(code_muni, bbox, filters) -> str`

Responsabilidades do conector:

- montar a query Overpass;
- executar `POST` via rede do QGIS;
- validar HTTP/status/JSON mínimo;
- devolver o JSON bruto;
- opcionalmente salvar o bruto em cache.

Responsabilidades que **não** devem ficar no conector:

- gerar nós e links finais;
- recortar pelo polígono municipal;
- gravar `osm_nodes`/`osm_links` no GeoPackage final;
- adicionar camada ao projeto.

Essa separação replica a fronteira observada em `downloadOSMData(...)` →
`getNetFromFile(...)` do OSM2GMNS.

#### 8.12.4 Contrato do pipeline `core/osm_pipeline.py`

O pipeline é o equivalente GisBR da fase de tratamento do OSM2GMNS. Ele deve
receber município + bruto OSM e devolver camadas vetoriais prontas para gravação.

Proposta de função principal:

- `build_osm_municipal_network(code_muni, nome_muni, gpkg_path, force=False, feedback=None) -> dict`

Retorno sugerido:

```python
{
    "raw_cache": "/abs/path/cache/osm/<arquivo>.json",
    "layers": {
        "osm_links_raw": <QgsVectorLayer>,
        "osm_links": <QgsVectorLayer>,
        "osm_nodes": <QgsVectorLayer>,
    },
    "metadata": {
        "code_muni": "...",
        "nome_muni": "...",
        "bbox": (...),
        "source": "overpass",
        "generated_at": "...",
    },
}
```

Etapas obrigatórias do pipeline:

1. resolver município (`code_muni` → polígono + bbox);
2. carregar cache bruto ou consultar Overpass;
3. converter JSON OSM em feições lineares temporárias;
4. filtrar apenas `way` com `highway`;
5. recortar linhas pelo polígono do município;
6. descartar geometrias vazias ou inválidas;
7. aplicar classificação viária mínima;
8. quebrar a rede em links e nós mínimos;
9. devolver camadas prontas para persistência.

#### 8.12.5 Regra inicial de classificação viária

Inspirado em `link_types` do OSM2GMNS, o GisBR deve começar com uma tabela local,
pequena e explícita, sem tentar cobrir todos os casos do OSM logo na primeira
entrega.

Tabela inicial proposta:

- `motorway`, `trunk` → `mode_class = rodovia_estruturante`
- `primary`, `secondary` → `mode_class = arterial_regional`
- `tertiary` → `mode_class = coletora`
- `residential`, `unclassified`, `living_street` → `mode_class = local`
- `service` → `mode_class = servico`
- `track` → `mode_class = vicinal`
- `cycleway` → `mode_class = cicloviaria`
- `footway`, `pedestrian`, `path`, `steps` → `mode_class = pedonal`

Regra operacional da Fase 1:

- manter só feições com `highway` conhecido nessa tabela;
- tudo que ficar fora vira descarte controlado ou `mode_class = outros`, conforme
  volume observado nos primeiros testes.

#### 8.12.6 Algoritmo mínimo para `osm_links` e `osm_nodes`

Não é necessário reproduzir toda a topologia do OSM2GMNS. A primeira entrega
precisa apenas gerar uma rede municipal conectável, auditável e estável.

Algoritmo mínimo proposto:

1. cada `way` OSM vira uma ou mais linhas temporárias com os tags essenciais;
2. após o clip municipal, cada geometria linear passa por normalização;
3. cada segmento linear recebe:
   - `link_id`
   - `osm_way_id`
   - `highway`
   - `road_name`
   - `oneway`
   - `length_m`
   - `mode_class`
4. o `from_node` é o ponto inicial da linha;
5. o `to_node` é o ponto final da linha;
6. nós são deduplicados por coordenada quantizada/tolerância pequena;
7. cada nó recebe:
   - `node_id`
   - `x`
   - `y`
   - `municipio_id`
   - `is_boundary` (opcional na Fase 2)

Escopo explícito da Fase 1:

- **sim**: nós de extremidade e links simples;
- **sim**: respeito ao `oneway` como atributo;
- **não ainda**: consolidação de interseções complexas;
- **não ainda**: divisão automática em todos os cruzamentos intermediários;
- **não ainda**: conectores especiais ou análise multimodal.

Ou seja: a primeira topologia é "mínima GMNS-like", suficiente para persistir
nós/links e evoluir depois.

#### 8.12.7 Schema final de persistência no GeoPackage

A persistência deve seguir o padrão já usado pelo plugin: GeoPackage com nomes de
camada estáveis e adição posterior ao projeto QGIS.

Camadas mínimas da primeira entrega:

- `osm_links_<code_muni>`
- `osm_nodes_<code_muni>`
- opcionalmente `osm_links_raw_<code_muni>` para auditoria interna

Campos mínimos sugeridos:

**osm_links**
- `link_id`
- `osm_way_id`
- `from_node`
- `to_node`
- `road_name`
- `highway`
- `mode_class`
- `oneway`
- `length_m`
- `code_muni`
- `source`
- `generated_at`

**osm_nodes**
- `node_id`
- `x`
- `y`
- `code_muni`
- `source`
- `generated_at`

A separação em duas camadas mantém a compatibilidade conceitual com GMNS sem
obrigar exportação CSV na primeira fase.

#### 8.12.8 Integração com `core/diagnostico.py`

Há dois caminhos aceitáveis, mas o primeiro é o mais coerente com o projeto
atual:

**Caminho preferido**
- adicionar uma fonte declarativa em `core/sources.py`, por exemplo `osm_vias`;
- ampliar `carregar_fontes(...)` para reconhecer `protocolo = "osm"`;
- quando selecionada no painel, a fonte executa o pipeline OSM e grava as
  camadas no mesmo GeoPackage do diagnóstico.

**Alternativa**
- criar um algoritmo separado `algorithms/diagnostico/read_osm_municipal.py`;
- a GUI chama esse algoritmo quando o usuário marcar a opção OSM.

Decisão recomendada agora: começar pelo **protocolo novo em `carregar_fontes(...)`**,
porque isso preserva o padrão já existente de seleção de fontes pelo painel.

#### 8.12.9 Integração com `gui/diagnostico_dock.py`

O painel atual já suporta seleção de fontes por árvore e destino `.gpkg`. Então a
integração OSM não exige redesenho de GUI.

Mudança mínima sugerida:

- adicionar `osm_vias` ao catálogo de fontes;
- deixar a fonte aparecer na árvore por eixo (ex.: `transportes` ou `urbano`);
- reutilizar o mesmo botão **Carregar**;
- logar no `txt_log` etapas como:
  - consulta Overpass,
  - uso de cache,
  - total de links brutos,
  - total de links após recorte,
  - total de nós gerados.

Ou seja: a GUI atual já é suficiente; a mudança principal está no backend.

#### 8.12.10 Critérios de aceite da implementação inicial

A Fase 1 executável deve ser considerada pronta quando conseguir:

1. receber um `code_muni` válido pelo fluxo atual do painel;
2. consultar Overpass por bbox municipal;
3. salvar o bruto em cache local;
4. gerar uma camada `osm_links_<code_muni>` recortada pelo polígono municipal;
5. gerar uma camada `osm_nodes_<code_muni>` com nós de extremidade deduplicados;
6. gravar ambas no GeoPackage escolhido pelo usuário;
7. recarregar as camadas válidas no projeto QGIS;
8. rodar sem dependências além de QGIS/Qt/stdlib.

#### 8.12.11 Pontos deliberadamente adiados

Para não inflar a primeira entrega, ficam fora da Fase 1:

- `area_id` de relation OSM como estratégia principal de consulta;
- suporte a modos além de vias `highway`;
- defaults avançados de `lanes`, `speed`, `capacity`;
- consolidação de interseções complexas ao estilo `consolidateComplexIntersections`;
- exportação GMNS em CSV;
- tuning fino de conectividade e snapping em cruzamentos.

Esses itens entram só depois que a rede municipal mínima já estiver estável no
GeoPackage.


- **T-007 — Hardening do catálogo de fontes** _(pronta agora; paralela ao
  planejamento)_: confirmar `GetCapabilities`/`DescribeFeatureType` e extrair, por
  fonte, `type_name` exato, CRS, `outputFormat` (tem GeoJSON?) e **o campo de
  filtro municipal**. Saída alimenta `core/sources.py`.
- **T-008 — Branch + scaffolding** `feat/diagnostico-plano-diretor` ✅ **feita**:
  criou `core/connectors/`, `core/sources.py`, `algorithms/diagnostico/`
  (stubs). `core/diagnostico.py` e `gui/` serão criados nas tarefas T-010/T-011.
- **T-009 — Portar `wfs.py`** do `desafio-2` para `core/connectors/wfs.py` +
  `core/connectors/basemap.py` (satélite XYZ Esri). (Senior fornece o código exato.)
- **T-010 — Registry (a partir da T-007) + motor `core/diagnostico.py`** (Fase A):
  `SOURCES` preenchido + `carregar_fontes()` (busca via conector → grava no
  GeoPackage → adiciona ao projeto). Testável pelo Console. (Senior documenta
  MUITO bem a API QGIS, incl. `QgsVectorFileWriter` para GPKG.)
- **T-011 — Painel (dock)** (Fase B): `gui/diagnostico_dock.py` + ligação no
  `initGui` (botão/menu). Município + checkboxes por eixo + caminho do GeoPackage
  + "Carregar". (Senior fornece o esqueleto Qt.)
- **T-012 — ArcGIS REST (Fase C):** ✅ **feita** — `arcgis_rest.py` + fontes
  `arcgis` no `SOURCES` (ANA/BHO, IBAMA).
- ~~Parecer/KPIs~~ — fora do escopo atual (§6.6).

> **Tarefa que o Junior pode fazer JÁ, em paralelo:** **T-007** (acima). É
> pesquisa/verificação (forte dele), independe das decisões de §6 e produz
> exatamente os dados que o `core/sources.py` vai precisar.
