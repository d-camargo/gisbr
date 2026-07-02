# geobr-qgis

Acesso **"1 linha → 1 camada"** aos dados espaciais oficiais do Brasil do pacote
[**geobr**](https://github.com/ipeaGIT/geobr) (IPEA), **dentro do QGIS**, usando
**apenas PyQGIS + a stdlib do Python** — sem `geopandas`, `requests`, `pandas`
ou `duckdb`.

> Estado atual: suporte a **Fase 1** (GeoPackage legacy v1.7.0) e **Fase 2**
> (Parquet v2.0.0 + integração com `censobr`/`join_censo`).

## Como funciona

O plugin é um **Processing Provider** (`geobr`). Cada geografia do geobr é um
algoritmo `read_*`, que:

1. baixa e parseia o metadado `metadata_1.7.0_gpkg.csv` (módulo `csv` da stdlib);
2. seleciona a(s) URL(s) por `geo` + `ano` + `simplificado`;
3. baixa o(s) `.gpkg` para o cache em disco, com **cadeia de mirrors**
   (IPEA primário → mirror GitHub, mesmo `file_id`);
4. carrega com `QgsVectorLayer(path, name, "ogr")`, concatena (`native:mergevectorlayers`)
   e filtra por código/sigla via `setSubsetString`;
5. entrega no `OUTPUT` (sink) em **SIRGAS 2000 / EPSG:4674**.

## Algoritmos (Fase 1) — 26 geografias

| Grupo | Algoritmos |
|---|---|
| Político-administrativo | `read_country`, `read_region`, `read_state`, `read_meso_region`, `read_micro_region`, `read_intermediate_region`, `read_immediate_region`, `read_municipality`, `read_municipal_seat` |
| Censitário | `read_census_tract`, `read_weighting_area`, `read_statistical_grid`, `read_neighborhood` |
| Urbano / metropolitano | `read_metro_area`, `read_urban_area`, `read_urban_concentrations`, `read_pop_arrangements` |
| Ambiental / territorial | `read_biomes`, `read_amazon`, `read_semiarid`, `read_conservation_units`, `read_indigenous_land`, `read_disaster_risk_area` |
| Setorial | `read_health_region`, `read_health_facilities`, `read_schools` |

> Fora da Fase 1: `read_comparable_areas` (assinatura `start_year`/`end_year`).
> A Fase 2 adiciona as geografias só-v2 (`read_favela`, `read_polling_places`,
> `read_quilombola_land`) e o `join_censo` para dados do `censobr`.
>
> ⚠️ `read_statistical_grid` é fatiado em ~56 arquivos de grade e, sem filtro,
> baixa o Brasil inteiro (vários GB). Use com cautela.

### Parâmetros comuns

| Param | Tipo | Observação |
|---|---|---|
| `YEAR` | enum | populado do catálogo; default = ano mais recente |
| `CODE` | string | `"all"`, sigla (`"MG"`), código IBGE (`31`, `3106200`) |
| `SIMPLIFIED` | bool | default `True` (renderização rápida) |
| `OUTPUT` | sink | camada de saída |

> Geografias fatiadas por UF (`municipality`, `census_tract`, `weighting_area`)
> baixam **só o estado** quando `CODE` é uma UF — evita baixar o Brasil inteiro.

## Instalação (desenvolvimento)

```bash
cd ~/Documentos/SIG/geobr-qgis/   # ou onde estiver o repo
make deploy        # symlink -> profiles/default/python/plugins/geobr_qgis
make test          # checagem de sintaxe (sem QGIS)
```

Recarregue no QGIS (Plugin Reloader) ou reinicie. Ative o plugin em
*Complementos → Gerenciar e Instalar*.

## Uso no Console Python do QGIS

```python
import processing
processing.run("geobr:read_municipality",
    {"YEAR": <idx_do_ano>, "CODE": "MG", "SIMPLIFIED": True, "OUTPUT": "memory:"})
```

> `YEAR` é um **enum** (índice na lista de anos disponíveis), não o ano literal.

## Cache

Os arquivos baixados ficam em `QStandardPaths.CacheLocation` →
`.../geobr-qgis/` (um arquivo por `file_id`). Apague a pasta para forçar
re-download.

## Requisitos

- QGIS 3.x (testado em 3.34 Prizren).
- Conexão para o primeiro download de cada geografia/ano (depois usa cache).
- Nenhuma dependência externa de Python.

## Licença

GPL v2+ (mesma família dos demais plugins do autor).
