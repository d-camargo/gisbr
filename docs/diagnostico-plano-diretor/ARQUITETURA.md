# Arquitetura — GisBR: Diagnóstico para Plano Diretor

> Documento de desenho. A partir daqui desmembramos as ACTIONS para o Junior.
> Status: **rascunho para revisão do Diego** — itens marcados _(a confirmar)_ são
> decisões dele. Fonte de dados: pesquisa em `docs/diagnostico-plano-diretor/`
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

### 3.3 Algoritmos (`algorithms/diagnostico/`)

- **Factory declarativo** (espelhando `v2_factory.py`): para cada fonte do
  catálogo, gera um `QgsProcessingAlgorithm` no grupo do seu eixo. Parâmetro
  comum: `MUNICIPIO` (`code_muni`), + `OUTPUT`. O protocolo decide o conector.
- **Orquestrador** `diagnostico_municipio` _(Fase C)_: dado um `code_muni`,
  carrega o conjunto de camadas disponíveis dos 6 eixos num **grupo de camadas**,
  combinando conectores novos + os `read_*` do geobr (demografia/educação/saúde).

### 3.4 Relatório / KPIs — **FORA do escopo atual** _(decisão Diego, 2026-06-29)_

O painel/parecer do haCARthon (`parecer.py`/`kpis_dock.py`) **não** entra agora.
Por ora o diagnóstico **só carrega as camadas** organizadas por eixo (+ basemap
de satélite). Indicadores/relatório ficam para uma fase futura, se houver demanda.

## 4. Filtro por município (peça-chave)

| Protocolo | Como filtrar pelo município | Observação |
|---|---|---|
| WFS | `CQL_FILTER` no GET (server-side) | ideal; precisa do **campo** certo (T-007) |
| ArcGIS REST | `where=<campo>='<code>'` na query | idem |
| WMS | não filtra (raster) | carrega como overlay; recorte visual |
| geobr (já) | pós-download (`setSubsetString`) ou fatiado por UF | como hoje |

Quando a fonte **não** tiver campo municipal, cair para **bbox do município**
(obtido do `read_municipality` do próprio GisBR) como filtro espacial.

## 5. Fases de implementação _(proposta)_

- **Fase A — Catálogo declarativo + conector WFS + basemap.** `core/sources.py` +
  `core/connectors/wfs.py` (portado) + `core/connectors/basemap.py` (satélite
  XYZ Esri) + factory que gera os algoritmos WFS por eixo (transportes,
  ambiental/SICAR+ICMBio, saneamento/CPRM). MVP que já entrega. (O basemap é um
  ganho rápido e pode aterrissar logo no início da Fase A.)
- **Fase B — ArcGIS REST.** ANA (BHO), IBAMA. _(WMS temático fica fora — ver §3.4
  e §6.)_
- **Fase C — Orquestrador `diagnostico_municipio`.** Junta tudo num grupo de
  camadas a partir de um `code_muni`, incluindo os eixos já cobertos pelo geobr,
  e adiciona o basemap de satélite ao fundo.
- ~~**Fase D — Parecer/KPIs.**~~ **Fora do escopo atual** (decisão Diego).

## 6. Decisões (resolvidas em 2026-06-29)

1. **Modelo declarativo** (registry + factory). ✅ **Sim.**
2. **Fase A só com WFS** (+ basemap). ✅ **Sim.**
3. **Parecer/KPIs:** ❌ **Fora por ora** — diagnóstico só carrega camadas. O
   painel/parecer do haCARthon não entra agora.
4. **WMS temático (MapBiomas/OSM):** ❌ **Fora.** No lugar entra um **basemap de
   satélite (XYZ Esri World Imagery)** como fundo (ver §3.2 e
   `referencia-satelite-hacarthon.md`).
5. **Grupos no Toolbox em PT-BR** agora (`Diagnóstico — <Eixo>`); i18n junto com o
   resto da UI depois. ✅

## 7. Roadmap de ACTIONS (a desmembrar após §6)

- **T-007 — Hardening do catálogo de fontes** _(pronta agora; paralela ao
  planejamento)_: confirmar `GetCapabilities`/`DescribeFeatureType` e extrair, por
  fonte, `type_name` exato, CRS, `outputFormat` (tem GeoJSON?) e **o campo de
  filtro municipal**. Saída alimenta `core/sources.py`.
- **T-008 — Branch + scaffolding** `feat/diagnostico-plano-diretor`: criar
  `core/connectors/`, `core/sources.py` (esqueleto) e `algorithms/diagnostico/`
  sem lógica ainda. (Senior entrega esqueleto mastigado.)
- **T-009 — Portar `wfs.py`** do `desafio-2` para `core/connectors/wfs.py` +
  `core/connectors/basemap.py` (satélite XYZ Esri) e um algoritmo "Adicionar
  imagem de satélite (fundo)". (Senior fornece o código exato.)
- **T-010 — Registry + factory WFS (Fase A):** `core/sources.py` preenchido (a
  partir da T-007) + factory de algoritmos por eixo. (Senior documenta MUITO bem
  a API QGIS.)
- **T-011 — ArcGIS REST (Fase B):** ANA (BHO), IBAMA.
- **T-012 — Orquestrador `diagnostico_municipio` (Fase C).**
- ~~Parecer/KPIs~~ — fora do escopo atual (§6.3).

> **Tarefa que o Junior pode fazer JÁ, em paralelo:** **T-007** (acima). É
> pesquisa/verificação (forte dele), independe das decisões de §6 e produz
> exatamente os dados que o `core/sources.py` vai precisar.
