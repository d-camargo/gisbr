# GisBR

**English** | [Português](#português)

GisBR brings official Brazilian spatial data **into QGIS**, using **only PyQGIS and the Python stdlib** (with one optional exception for Parquet). It does two things:

1. **Master Plan Diagnostic** — a dock panel that, given a municipality, loads the official layers a city needs to draft or review its *Plano Diretor*, organized in 8 thematic axes.
2. **geobr / censobr mirror** — "1-line → 1-layer" access to the datasets of the [**geobr**](https://github.com/ipeaGIT/geobr) and [**censobr**](https://github.com/ipeaGIT/censobr) (IPEA) packages, as Processing algorithms.

All data is output in **SIRGAS 2000 / EPSG:4674**.

## Master Plan Diagnostic

Open the **GisBR** panel (toolbar button / *Plugins → GisBR*). Pick a **state → municipality**, choose the sources you want (checkboxes grouped by axis), a destination **GeoPackage**, and click **Load**. GisBR downloads each source **filtered to that municipality**, clips it to the municipality polygon, saves one layer per source in the GeoPackage, and adds them to the project.

- **8 axes**: Transport · Drainage & Sanitation · Demography · Environment · Education · Health · Urban · Administrative.
- **Connectors** (one per protocol): **WFS** (`CQL_FILTER`, GeoJSON via the QGIS network stack + `/vsicurl/` fallback), **ArcGIS REST** (`where=` query), **geobr** (v1/v2), and an optional **Esri World Imagery** satellite basemap (added at the bottom of the layer tree).
- **Server-side filter** by municipality when the service supports it, plus a **client-side clip to the municipality polygon** (avoids pulling neighbors). Empty layers are skipped; already-downloaded layers are skipped unless you tick *Update*.

## geobr / censobr mirror

The plugin also acts as a QGIS **Processing Provider** (`gisbr`) with **55 algorithms**:

- **Phase 1 (GeoPackage legacy v1.7.0)** — 26 `read_*` algorithms: `read_country`, `read_state`, `read_municipality`, `read_census_tract`, `read_biomes`, `read_amazon`, `read_health_facilities`, `read_schools`, etc.
- **Phase 2 (Parquet v2.0.0 + censobr)** — 28 `read_*_v2` algorithms (loaded via the GDAL Parquet driver or an optional `pyarrow` fallback), plus v2-only geographies (`read_favela_v2`, `read_polling_places_v2`, `read_quilombola_land_v2`).
- **Integration** — `join_censo` joins geobr census tracts with censobr demographic tables using `code_tract`.

Each `read_*` algorithm parses the official IPEA metadata catalog, selects the right URL by `geo`/`year`/`simplified`, downloads to a local disk cache with a **mirror fallback chain** (IPEA primary → GitHub mirror), and loads the result as a QGIS vector layer, filtered by code/state.

### Common parameters

| Param | Type | Note |
|---|---|---|
| `YEAR` | enum | Populated from the catalog; default is the most recent year. |
| `CODE` | string | `"all"`, state abbreviation (`"MG"`), or IBGE code (`31`, `3106200`). |
| `SIMPLIFIED` | bool | Default `True` for faster rendering. |
| `OUTPUT` | sink | Output layer. |

> Geographies split by state (e.g., `municipality`, `census_tract`) download **only that state** when `CODE` is provided, avoiding a full-country download.

## Language

The UI follows the **QGIS locale**: Portuguese (pt) shows the **PT-BR** translation; any other locale shows **English** (the source language). Change it in *Settings → Options → General → Override system locale* and restart QGIS. There is no in-plugin language button.

## Data vintage (reference year)

Distinguish the **reference year of the data** (vintage) from the **extraction date** (when the download happened):

- **geobr**: Phase 1 references IBGE data up to ~2020; Phase 2 up to 2022/2025.
- **Diagnostic**: each source has its own reference year (e.g., DNIT SNV is `snv_202507a`, July 2025). See [docs/diagnostico-plano-diretor/fontes-detalhe.md](docs/diagnostico-plano-diretor/fontes-detalhe.md).

Downloaded layers store the download date in a custom property `data_extracao`, distinct from the dataset's vintage.

## Requirements

- QGIS **3.16+**.
- Internet connection for the first download (subsequent uses are cached).
- **For Parquet (Phase 2 and the v2-only diagnostic sources)**: QGIS with GDAL Parquet support, or `pyarrow` installed as an optional fallback.

## Installation (development)

```bash
cd ~/Documents/GIS/gisbr/   # or where the repository is located
make deploy        # symlinks to profiles/default/python/plugins/gisbr
make test          # syntax check (without QGIS)
```

Reload with the Plugin Reloader or restart QGIS. Enable it via *Plugins → Manage and Install Plugins*.

## Usage in the QGIS Python Console

```python
import processing
processing.run("gisbr:read_municipality",
    {"CODE": "MG", "SIMPLIFIED": True, "OUTPUT": "memory:"})
```

> `YEAR` is an **enum**: the index in the available-years list, **not** the literal year. Omit it to use the most recent year.

## Cache

Downloaded files are stored in `QStandardPaths.CacheLocation` → `.../geobr-qgis/`. Delete the folder to force a re-download.

## License

**GPL-3.0**.

---

# Português

[English](#gisbr) | **Português**

O GisBR traz dados espaciais oficiais do Brasil **para dentro do QGIS**, usando **apenas PyQGIS e a stdlib do Python** (com uma exceção opcional para Parquet). Ele faz duas coisas:

1. **Diagnóstico de Plano Diretor** — um painel (dock) que, dado um município, sobe as camadas oficiais que uma cidade precisa para elaborar ou revisar o *Plano Diretor*, organizadas em 8 eixos temáticos.
2. **Espelho geobr / censobr** — acesso **"1 linha → 1 camada"** aos dados dos pacotes [**geobr**](https://github.com/ipeaGIT/geobr) e [**censobr**](https://github.com/ipeaGIT/censobr) (IPEA), como algoritmos de Processamento.

Todos os dados são entregues em **SIRGAS 2000 / EPSG:4674**.

## Diagnóstico de Plano Diretor

Abra o painel **GisBR** (botão na barra / *Complementos → GisBR*). Escolha **UF → Município**, marque as fontes desejadas (checkboxes agrupados por eixo), um **GeoPackage** de destino e clique em **Carregar**. O GisBR baixa cada fonte **filtrada pelo município**, recorta pelo polígono do município, grava uma camada por fonte no GeoPackage e adiciona ao projeto.

- **8 eixos**: Transportes · Drenagem e Saneamento · Demografia · Ambiental · Educação · Saúde · Urbano · Político-administrativo.
- **Conectores** (um por protocolo): **WFS** (`CQL_FILTER`, GeoJSON pela pilha de rede do QGIS + fallback `/vsicurl/`), **ArcGIS REST** (consulta `where=`), **geobr** (v1/v2) e um **basemap de satélite** opcional (Esri World Imagery, adicionado ao fundo da árvore de camadas).
- **Filtro no servidor** por município quando o serviço permite, mais um **recorte pelo polígono do município** no cliente (evita trazer vizinhos). Camadas vazias são puladas; bases já baixadas são puladas, salvo se marcar *Atualizar*.

## Espelho geobr / censobr

O plugin também é um **Processing Provider** (`gisbr`) com **55 algoritmos**:

- **Fase 1 (GeoPackage legacy v1.7.0)** — 26 algoritmos `read_*`: `read_country`, `read_state`, `read_municipality`, `read_census_tract`, `read_biomes`, `read_amazon`, `read_health_facilities`, `read_schools`, etc.
- **Fase 2 (Parquet v2.0.0 + censobr)** — 28 algoritmos `read_*_v2` (lidos via driver GDAL Parquet ou fallback opcional `pyarrow`), mais geografias só-v2 (`read_favela_v2`, `read_polling_places_v2`, `read_quilombola_land_v2`).
- **Integração** — `join_censo` une os setores censitários do geobr com as tabelas demográficas do censobr pela chave `code_tract`.

Cada `read_*` lê o catálogo oficial de metadados do IPEA, seleciona a URL por `geo`/`ano`/`simplificado`, baixa para um cache em disco com **cadeia de mirrors** (IPEA primário → espelho GitHub) e carrega como camada vetorial, filtrada por código/UF.

### Parâmetros comuns

| Param | Tipo | Observação |
|---|---|---|
| `YEAR` | enum | Populado do catálogo; default é o ano mais recente. |
| `CODE` | string | `"all"`, sigla (`"MG"`) ou código IBGE (`31`, `3106200`). |
| `SIMPLIFIED` | bool | Default `True` para renderização rápida. |
| `OUTPUT` | sink | Camada de saída. |

> Geografias particionadas por UF (ex.: `municipality`, `census_tract`) baixam **apenas o estado** quando `CODE` é fornecido, evitando o download do Brasil inteiro.

## Idioma

A interface segue a **localização do QGIS**: em português (pt) aparece a tradução **PT-BR**; em qualquer outro idioma, o **inglês** (idioma-fonte). Troque em *Configurações → Opções → Geral → Sobrepor localização do sistema* e reinicie o QGIS. Não há botão de idioma dentro do plugin.

## Vintage dos dados (ano de referência)

Distinga o **ano de referência dos dados** (vintage) da **data de extração** (quando o download foi feito):

- **geobr**: a Fase 1 referencia dados do IBGE até ~2020; a Fase 2, até 2022/2025.
- **Diagnóstico**: cada fonte tem sua própria vintage (ex.: a malha do DNIT é `snv_202507a`, julho/2025). Veja [docs/diagnostico-plano-diretor/fontes-detalhe.md](docs/diagnostico-plano-diretor/fontes-detalhe.md).

As camadas baixadas gravam a data do download na propriedade `data_extracao`, distinta do ano de referência do conjunto de dados.

## Requisitos

- QGIS **3.16+**.
- Conexão com a internet para o primeiro download (usos seguintes usam o cache local).
- **Para Parquet (Fase 2 e as fontes só-v2 do diagnóstico)**: QGIS com suporte ao driver GDAL Parquet, ou `pyarrow` instalado como fallback opcional.

## Instalação (desenvolvimento)

```bash
cd ~/Documentos/SIG/gisbr/   # ou onde estiver o repositório
make deploy        # symlink -> profiles/default/python/plugins/gisbr
make test          # checagem de sintaxe (sem QGIS)
```

Recarregue com o Plugin Reloader ou reinicie o QGIS. Ative em *Complementos → Gerenciar e Instalar*.

## Uso no Console Python do QGIS

```python
import processing
processing.run("gisbr:read_municipality",
    {"CODE": "MG", "SIMPLIFIED": True, "OUTPUT": "memory:"})
```

> `YEAR` é um **enum**: o índice na lista de anos disponíveis, **não** o ano literal. Omita-o para usar o ano mais recente.

## Cache

Os arquivos baixados ficam em `QStandardPaths.CacheLocation` → `.../geobr-qgis/`. Apague a pasta para forçar um re-download.

## Licença

**GPL-3.0**.
