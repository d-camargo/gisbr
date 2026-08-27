# GisBR

**English** | [Português](#português) | [Documentation](https://gisbr.dcamargo.com.br)

GisBR brings official Brazilian spatial data **into QGIS**, using **only PyQGIS and the Python stdlib** (with one optional exception for Parquet). It does two things:

1. **Master Plan Diagnostic** — a dock panel that, given a municipality, loads the official layers a city needs to draft or review its *Plano Diretor*, organized in 8 thematic axes.
2. **geobr / censobr mirror** — "1-line → 1-layer" access to the datasets of the [**geobr**](https://github.com/ipeaGIT/geobr) and [**censobr**](https://github.com/ipeaGIT/censobr) (IPEA) packages, as Processing algorithms.

All data is output in **SIRGAS 2000 / EPSG:4674**.

## Master Plan Diagnostic

Open the **GisBR** panel (toolbar button / *Plugins → GisBR*). Pick a **state → municipality**, choose the sources you want (checkboxes grouped by axis), a destination **GeoPackage**, and click **Load**. GisBR downloads each source **filtered to that municipality**, clips it to the municipality polygon, saves one layer per source in the GeoPackage, and adds them to the project.

- **45 sources** across **8 axes**: Transport · Drainage & Sanitation · Demography · Environment · Education · Health · Urban · Administrative. Since 0.5.0 the catalog also covers geological risk (SGB/CPRM), mining claims (ANM/SIGMINE), groundwater wells (SIAGAS), IBGE BC250 2025 layers, IBGE urbanised areas (2019), subnormal agglomerations (2010), and the IBGE BDIA physical-environment set (soil, geology, geomorphology, vegetation).
- **Connectors** (one per protocol): **WFS** (`CQL_FILTER`, GeoJSON via the QGIS network stack + `/vsicurl/` fallback), **ArcGIS REST** (`where=` query), **OSM/Overpass** (municipal road network — links and node topology, same skip-if-exists behavior as the other sources), **geobr** (v1/v2), and an optional **Esri World Imagery** satellite basemap (added at the bottom of the layer tree).
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

## SIGEF / INCRA bases

The SIGEF certified parcels have no public endpoint: the INCRA export service (`https://certificacao.incra.gov.br/csv_shp/export_shp.py`) answers with a gov.br login page, and no official mirror (INDE, geoservicos.incra.gov.br, dados.gov.br) publishes them anonymously (measured on 2026-08-23, see [docs/diagnostico-plano-diretor/incra-sigef-acesso.md](docs/diagnostico-plano-diretor/incra-sigef-acesso.md)). GisBR therefore never asks for and never stores credentials. Workflow:

1. Logged in with your own gov.br account, download the certified parcels Shapefile from the INCRA export service;
2. Point the "Manual downloads folder" field of the diagnostic panel to that folder (it defaults to the system Downloads folder);
3. Check the "INCRA/SIGEF" source (8. Administrative axis) — GisBR picks the newest matching file in that folder, clips it to the municipality polygon and saves it to the GeoPackage like any other source. If the file is missing, the source is skipped with a note telling you where to get it.

## Requirements

- QGIS **3.16+** and **QGIS 4.x (Qt6)** — the plugin declares `supportsQt6=True` and is tested against both Qt5 and Qt6 builds.
- Internet connection for the first download (subsequent uses are cached).
- **For Parquet (Phase 2 and the v2-only diagnostic sources)**: QGIS with GDAL Parquet support, or `pyarrow` installed as an optional fallback.

## Network robustness

- **Bundled certificates**: the plugin ships the CA trust anchors for the servers it talks to and injects them **additively** on top of the system trust store (it never relaxes certificate verification). This is what fixes the "unable to find issuer certificate" error on a freshly installed Windows/OSGeo4W, where the OpenSSL stack used by QGIS doesn't pull root/intermediate certificates from the Windows certificate store the way a browser does.
- **Truncation warnings**: when a service cuts off the response short of the full result (WFS `numberMatched`, ArcGIS `maxRecordCount`), the log shows a warning and the resulting layer carries a `truncado` custom property, instead of silently loading a partial dataset.
- **Errors reported over HTTP 200**: ArcGIS REST and WFS servers can answer `200 OK` with an error body instead of failing at the HTTP level. The connectors inspect that body and surface the server's own code and message, instead of a generic "failed to open the layer".

## Installation (development)

```bash
cd ~/Documents/GIS/gisbr/   # or where the repository is located
make deploy        # symlinks to profiles/default/python/plugins/gisbr
make test          # syntax check only (ast.parse, no QGIS) — not the compatibility gate
```

The actual compatibility check is a **smoke test that imports every plugin module under both Qt5 (QGIS 3.x) and Qt6 (QGIS 4.x)**; `make test` only catches syntax errors.

Reload with the Plugin Reloader or restart QGIS. Enable it via *Plugins → Manage and Install Plugins*.

The full documentation site is built locally with `make docs` (dependencies in `requirements-docs.txt`).

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

[English](#gisbr) | **Português** | [Documentação](https://gisbr.dcamargo.com.br)

O GisBR traz dados espaciais oficiais do Brasil **para dentro do QGIS**, usando **apenas PyQGIS e a stdlib do Python** (com uma exceção opcional para Parquet). Ele faz duas coisas:

1. **Diagnóstico de Plano Diretor** — um painel (dock) que, dado um município, sobe as camadas oficiais que uma cidade precisa para elaborar ou revisar o *Plano Diretor*, organizadas em 8 eixos temáticos.
2. **Espelho geobr / censobr** — acesso **"1 linha → 1 camada"** aos dados dos pacotes [**geobr**](https://github.com/ipeaGIT/geobr) e [**censobr**](https://github.com/ipeaGIT/censobr) (IPEA), como algoritmos de Processamento.

Todos os dados são entregues em **SIRGAS 2000 / EPSG:4674**.

## Diagnóstico de Plano Diretor

Abra o painel **GisBR** (botão na barra / *Complementos → GisBR*). Escolha **UF → Município**, marque as fontes desejadas (checkboxes agrupados por eixo), um **GeoPackage** de destino e clique em **Carregar**. O GisBR baixa cada fonte **filtrada pelo município**, recorta pelo polígono do município, grava uma camada por fonte no GeoPackage e adiciona ao projeto.

- **45 fontes** em **8 eixos**: Transportes · Drenagem e Saneamento · Demografia · Ambiental · Educação · Saúde · Urbano · Político-administrativo. Desde a 0.5.0 o catálogo também cobre risco geológico (SGB/CPRM), processos minerários (ANM/SIGMINE), poços (SIAGAS), camadas BC250 2025 do IBGE, áreas urbanizadas (2019) e aglomerados subnormais (2010) do IBGE, e o conjunto de meio físico do BDIA/IBGE (pedologia, geologia, geomorfologia, vegetação).
- **Conectores** (um por protocolo): **WFS** (`CQL_FILTER`, GeoJSON pela pilha de rede do QGIS + fallback `/vsicurl/`), **ArcGIS REST** (consulta `where=`), **OSM/Overpass** (malha viária municipal — vias e a topologia de nós, com o mesmo skip-if-exists das demais fontes), **geobr** (v1/v2) e um **basemap de satélite** opcional (Esri World Imagery, adicionado ao fundo da árvore de camadas).
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

## SIGEF / bases do INCRA

As parcelas certificadas do SIGEF não têm endpoint público: o serviço de exportação do INCRA (`https://certificacao.incra.gov.br/csv_shp/export_shp.py`) responde com a página de login do gov.br, e nenhum espelho oficial (INDE, geoservicos.incra.gov.br, dados.gov.br) as publica de forma anônima (medição de 23/08/2026 em [docs/diagnostico-plano-diretor/incra-sigef-acesso.md](docs/diagnostico-plano-diretor/incra-sigef-acesso.md)). Por isso o GisBR não pede e não guarda credencial nenhuma. Fluxo:

1. Logado com a sua conta gov.br, baixe o Shapefile das parcelas certificadas no serviço de exportação do INCRA;
2. Aponte o campo "Pasta de downloads manuais" do painel de diagnóstico para essa pasta (o padrão é a pasta Downloads do sistema);
3. Marque a fonte "INCRA/SIGEF" (eixo 8. Político-Administrativo) — o GisBR escolhe o arquivo mais recente que casar na pasta, recorta pelo polígono do município e grava no GeoPackage como qualquer outra fonte. Sem o arquivo, a fonte é pulada com um aviso dizendo onde obtê-lo.

## Requisitos

- QGIS **3.16+** e **QGIS 4.x (Qt6)** — o plugin declara `supportsQt6=True` e é testado nos dois ambientes, Qt5 e Qt6.
- Conexão com a internet para o primeiro download (usos seguintes usam o cache local).
- **Para Parquet (Fase 2 e as fontes só-v2 do diagnóstico)**: QGIS com suporte ao driver GDAL Parquet, ou `pyarrow` instalado como fallback opcional.

## Robustez de rede

- **Certificados embarcados**: o plugin traz as âncoras de confiança (CA) dos servidores que usa e as injeta de forma **aditiva**, por cima da loja de confiança do sistema (a verificação de certificado nunca é relaxada). É isso que resolve o erro "unable to find issuer certificate" numa instalação recente do Windows/OSGeo4W, onde a pilha OpenSSL usada pelo QGIS não busca raízes/intermediários na loja de certificados do Windows do jeito que um navegador faz.
- **Avisos de truncamento**: quando um serviço corta a resposta antes do total (WFS `numberMatched`, ArcGIS `maxRecordCount`), o log mostra um aviso e a camada resultante recebe a custom property `truncado`, em vez de carregar um conjunto parcial silenciosamente.
- **Erros reportados com HTTP 200**: servidores ArcGIS REST e WFS podem responder `200 OK` com um corpo de erro em vez de falhar no nível HTTP. Os conectores inspecionam esse corpo e propagam o código e a mensagem do próprio servidor, em vez de um "falha genérica ao abrir a camada".

## Instalação (desenvolvimento)

```bash
cd ~/Documentos/SIG/gisbr/   # ou onde estiver o repositório
make deploy        # symlink -> profiles/default/python/plugins/gisbr
make test          # checagem de sintaxe (ast.parse, sem QGIS) — não é o portão de compatibilidade
```

A verificação real de compatibilidade é um **smoke test que importa todos os módulos do plugin sob Qt5 (QGIS 3.x) e Qt6 (QGIS 4.x)**; o `make test` só pega erro de sintaxe.

Recarregue com o Plugin Reloader ou reinicie o QGIS. Ative em *Complementos → Gerenciar e Instalar*.

O site de documentação completo é gerado localmente com `make docs` (dependências em `requirements-docs.txt`).

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
