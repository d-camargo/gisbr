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
dígitos), subir no QGIS as camadas oficiais dos **6 eixos** (transportes,
saneamento, demografia, ambiental, educação, saúde), reaproveitando o que já
existe e adicionando conectores para fontes externas.

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
                │   • ... (6 eixos)                            │
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
        wms.py        (raster; QgsRasterLayer provider "wms" — overlay/base)
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
def carregar_fontes(selecionadas, code_muni, gpkg_path, add_basemap, feedback):
    # para cada fonte selecionada: conector busca (filtrado por code_muni)
    #   -> grava a camada no GeoPackage (uma camada por fonte)
    #   -> adiciona ao projeto a partir do .gpkg
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

Quando a fonte **não** tiver campo municipal, cair para **bbox do município**
(obtido do `read_municipality` do próprio GisBR) como filtro espacial.

## 5. Fases de implementação _(proposta)_

- **Fase A — Motor WFS + persistência GeoPackage + basemap.** `core/sources.py`
  + `core/connectors/wfs.py` (portado) + `core/connectors/basemap.py` +
  `core/diagnostico.py` (motor: busca → grava no `.gpkg` → adiciona ao projeto).
  MVP de engine, testável pelo Console antes da GUI.
- **Fase B — Painel (dock).** `gui/diagnostico_dock.py`: município + seleção por
  checkbox (por eixo) + caminho do GeoPackage + botão "Carregar". Ligado em
  `initGui`. **É a UX principal** (decisão Diego).
- **Fase C — ArcGIS REST.** ANA (BHO), IBAMA — novas fontes no mesmo motor/painel.
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
- **T-012 — ArcGIS REST (Fase C):** ANA (BHO), IBAMA.
- ~~Parecer/KPIs~~ — fora do escopo atual (§6.6).

> **Tarefa que o Junior pode fazer JÁ, em paralelo:** **T-007** (acima). É
> pesquisa/verificação (forte dele), independe das decisões de §6 e produz
> exatamente os dados que o `core/sources.py` vai precisar.
