# GisBR

**English** | [Português](#português)

"1-line → 1-layer" access to official spatial data from Brazil provided by the [**geobr**](https://github.com/ipeaGIT/geobr) and [**censobr**](https://github.com/ipeaGIT/censobr) (IPEA) packages, **directly inside QGIS**, using **only PyQGIS and the Python stdlib** (with one optional exception for Parquet).

The plugin provides 55 algorithms in total, divided in two phases:
- **Phase 1 (GeoPackage legacy v1.7.0)**: 26 `read_*` algorithms.
- **Phase 2 (Parquet v2.0.0 + censobr)**: 28 `read_*_v2` algorithms, loaded via GDAL Parquet driver (or optionally `pyarrow`), plus the `join_censo` algorithm for demographic data.

All data is output in **SIRGAS 2000 / EPSG:4674**.

## How it works

The plugin acts as a QGIS **Processing Provider** (`gisbr`). Each geography is provided as a processing algorithm that:

1. Parses the official IPEA metadata catalog.
2. Selects the appropriate URL based on parameters (`geo`, `year`, `simplified`).
3. Downloads the data to a local disk cache with a built-in **mirror fallback chain** (Primary source → GitHub mirror).
4. Loads the downloaded `.gpkg` or `.parquet` directly as a QGIS Vector Layer, merging and filtering by code/state.
5. Returns the processed layer.

## Algorithms

The plugin provides 55 algorithms, including:
- **Phase 1 (26 algorithms)**: `read_country`, `read_state`, `read_municipality`, `read_census_tract`, `read_biomes`, `read_amazon`, `read_health_facilities`, `read_schools`, etc.
- **Phase 2 (28 algorithms)**: `read_country_v2`, `read_state_v2`, `read_municipality_v2`, `read_census_tract_v2`, etc., plus new geographies available only in v2.0.0 like `read_favela_v2`, `read_polling_places_v2`, `read_quilombola_land_v2`.
- **Integration**: `join_censo` (joins geobr geometries with censobr demographic tables using `code_tract`).

### Common Parameters

| Param | Type | Note |
|---|---|---|
| `YEAR` | enum | Populated from the catalog; default is the most recent year. |
| `CODE` | string | `"all"`, state abbreviation (`"MG"`), or IBGE code (`31`, `3106200`). |
| `SIMPLIFIED` | bool | Default `True` for faster rendering. |
| `OUTPUT` | sink | Output layer. |

## Data Vintage (Reference Year)

It is important to distinguish the **reference year of the data** (vintage) from the **extraction date** (when the download was performed):
- **geobr**: Phase 1 algorithms load from the v1.7.0 legacy catalog (referencing IBGE data up to ~2020). Phase 2 algorithms load from the v2.0.0 catalog (referencing data up to 2022/2025).
- **Plano Diretor Diagnostic**: Each theme/source has its own distinct reference year (e.g., DNIT SNV is `snv_202507a` from July 2025). See [docs/diagnostico-plano-diretor/fontes-detalhe.md](file:///home/diegocamargo/Drive/02_Projetos_Tecnicos/GISBR/docs/diagnostico-plano-diretor/fontes-detalhe.md) for details on each source.

Downloaded layers will store the download date in a custom property called `data_extracao`, which is different from the actual reference year (vintage) of the dataset.

## Requirements

- QGIS 3.x.
- Internet connection for the first download (subsequent uses are cached).
- **For Phase 2 (Parquet)**: Requires QGIS to be compiled with GDAL Parquet support. If the native driver is unavailable, the plugin accepts `pyarrow` as an optional fallback dependency.

## Installation (Development)

```bash
cd ~/Documents/GIS/gisbr/   # or where the repository is located
make deploy        # symlinks to profiles/default/python/plugins/gisbr
make test          # syntax check (without QGIS)
```

Reload QGIS using the Plugin Reloader or restart it. Enable the plugin via *Plugins → Manage and Install Plugins*.

## Usage in QGIS Python Console

```python
import processing
processing.run("gisbr:read_municipality",
    {"CODE": "MG", "SIMPLIFIED": True, "OUTPUT": "memory:"})
```

> `YEAR` is an **enum**: the index in the available-years list, **not** the literal year. Omit it to use the most recent year (the default), or pass an index to choose another.

## Cache

Downloaded files are stored in `QStandardPaths.CacheLocation` → `.../geobr-qgis/`. Delete the folder to force a re-download.

## License

**GPL-3.0**.

---

# Português

[English](#gisbr) | **Português**

Acesso **"1 linha → 1 camada"** aos dados espaciais oficiais do Brasil dos pacotes [**geobr**](https://github.com/ipeaGIT/geobr) e [**censobr**](https://github.com/ipeaGIT/censobr) (IPEA), **diretamente no QGIS**, usando **apenas PyQGIS e a stdlib do Python** (com uma exceção opcional para Parquet).

O plugin oferece 55 algoritmos no total, divididos em duas fases:
- **Fase 1 (GeoPackage legacy v1.7.0)**: 26 algoritmos `read_*`.
- **Fase 2 (Parquet v2.0.0 + censobr)**: 28 algoritmos `read_*_v2`, lidos via driver GDAL Parquet (ou opcionalmente `pyarrow`), mais o algoritmo `join_censo` para dados demográficos.

Todos os dados são entregues no sistema de referência **SIRGAS 2000 / EPSG:4674**.

## Como funciona

O plugin é um **Processing Provider** (`gisbr`). Cada geografia é um algoritmo de processamento que:

1. Lê e interpreta o catálogo oficial de metadados do IPEA.
2. Seleciona a URL apropriada com base nos parâmetros (`geo`, `ano`, `simplificado`).
3. Baixa os dados para um cache em disco com uma **cadeia de mirrors** (Fonte primária → Espelho no GitHub).
4. Carrega o `.gpkg` ou `.parquet` baixado diretamente como uma camada vetorial no QGIS, concatenando e filtrando por código/estado.
5. Retorna a camada final.

## Algoritmos

O plugin possui 55 algoritmos, incluindo:
- **Fase 1 (26 algoritmos)**: `read_country`, `read_state`, `read_municipality`, `read_census_tract`, `read_biomes`, `read_amazon`, `read_health_facilities`, `read_schools`, etc.
- **Fase 2 (28 algoritmos)**: `read_country_v2`, `read_state_v2`, `read_municipality_v2`, `read_census_tract_v2`, etc., além de geografias disponíveis apenas na v2.0.0 como `read_favela_v2`, `read_polling_places_v2` e `read_quilombola_land_v2`.
- **Integração**: `join_censo` (une as geometrias do geobr com as tabelas demográficas do censobr através do `code_tract`).

### Parâmetros comuns

| Param | Tipo | Observação |
|---|---|---|
| `YEAR` | enum | Populado do catálogo; default é o ano mais recente. |
| `CODE` | string | `"all"`, sigla (`"MG"`) ou código IBGE (`31`, `3106200`). |
| `SIMPLIFIED` | bool | Default `True` para renderização rápida. |
| `OUTPUT` | sink | Camada de saída. |

> **Nota**: Geografias particionadas por UF (ex: `municipality`, `census_tract`) baixarão **apenas o estado** quando `CODE` for fornecido, evitando o download do Brasil inteiro.

## Vintage dos Dados (Ano de Referência)

É importante distinguir o **ano de referência dos dados** (vintage) da **data de extração** (quando o download foi realizado):
- **geobr**: Os algoritmos da Fase 1 carregam do catálogo legado v1.7.0 (referenciando anos do IBGE até ~2020). Os algoritmos da Fase 2 carregam do catálogo v2.0.0 (referenciando anos até 2022/2025).
- **Diagnóstico Plano Diretor**: Cada fonte possui sua própria vintage de referência (ex: a malha rodoviária do DNIT é `snv_202507a` de Julho/2025). Consulte [docs/diagnostico-plano-diretor/fontes-detalhe.md](file:///home/diegocamargo/Drive/02_Projetos_Tecnicos/GISBR/docs/diagnostico-plano-diretor/fontes-detalhe.md) para detalhes de cada base.

As camadas baixadas gravam a data do download na propriedade personalizada `data_extracao`, a qual é diferente do ano de referência original (vintage) do conjunto de dados.

## Requisitos

- QGIS 3.x.
- Conexão com a internet para o primeiro download (usos subsequentes utilizam o cache local).
- **Para a Fase 2 (Parquet)**: Requer que o QGIS tenha suporte ao driver GDAL Parquet. Caso o driver nativo não esteja disponível, o plugin aceita a instalação de `pyarrow` como dependência externa opcional (fallback).

## Instalação (Desenvolvimento)

```bash
cd ~/Documentos/SIG/gisbr/   # ou onde estiver o repositório
make deploy        # symlink -> profiles/default/python/plugins/gisbr
make test          # checagem de sintaxe (sem QGIS)
```

Recarregue no QGIS (Plugin Reloader) ou reinicie o programa. Ative o plugin em *Complementos → Gerenciar e Instalar*.

## Uso no Console Python do QGIS

```python
import processing
processing.run("gisbr:read_municipality",
    {"CODE": "MG", "SIMPLIFIED": True, "OUTPUT": "memory:"})
```

> `YEAR` é um **enum**: o índice na lista de anos disponíveis, **não** o ano literal. Omita-o para usar o ano mais recente (default), ou passe um índice para escolher outro.

## Cache

Os arquivos baixados ficam em `QStandardPaths.CacheLocation` → `.../geobr-qgis/`. Apague a pasta para forçar um re-download.

## Licença

**GPL-3.0**.
