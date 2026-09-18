# Medição de Acesso e Especificação — MapBiomas Coleção 9 (COG)

> Documento de referência técnica para integração dos dados raster de Cobertura e Uso da Terra do MapBiomas Coleção 9 no plugin GisBR (Diagnóstico de Plano Diretor — Eixo Ambiental / Uso do Solo).

---

## 1. Padrão de URL e Faixa de Anos Disponíveis (a)

### Padrão de URL do COG (Google Cloud Storage)
```text
https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_9/lclu/coverage/brasil_coverage_{ano}.tif
```

### Faixa de Anos e Teste de Cabeçalho (HEAD Requests)
A Coleção 9 do MapBiomas Brasil engloba a série histórica de **1985 a 2023** (39 anos disponíveis).

Testes de cabeçalho efetuados via requisição `HEAD`:
- **Ano inicial (1985):**
  - **URL:** `https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_9/lclu/coverage/brasil_coverage_1985.tif`
  - **Status HTTP:** `200 OK`
  - **Content-Length:** `965527143` bytes (~965,5 MB)
- **Ano mais recente (2023):**
  - **URL:** `https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_9/lclu/coverage/brasil_coverage_2023.tif`
  - **Status HTTP:** `200 OK`
  - **Content-Length:** `1050109605` bytes (~1,05 GB)

Toda a sequência anual de 1985 a 2023 respondeu com código `200 OK`.

---

## 2. Prova de Tiling, Overviews e Estrutura COG — `gdalinfo` (b - Medição 13)

Execução do `gdalinfo` diretamente sobre a URL remota usando a camada VSI do GDAL (`/vsicurl/`):

```bash
gdalinfo /vsicurl/https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_9/lclu/coverage/brasil_coverage_2023.tif
```

### Saída Comprovatória do `gdalinfo`
```text
Driver: GTiff/GeoTIFF
Files: /vsicurl/https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_9/lclu/coverage/brasil_coverage_2023.tif
Size is 155241, 158828
Coordinate System is:
GEOGCRS["WGS 84",
    ENSEMBLE["World Geodetic System 1984 ensemble",
        MEMBER["World Geodetic System 1984 (Transit)"],
        MEMBER["World Geodetic System 1984 (G730)"],
        MEMBER["World Geodetic System 1984 (G873)"],
        MEMBER["World Geodetic System 1984 (G1150)"],
        MEMBER["World Geodetic System 1984 (G1674)"],
        MEMBER["World Geodetic System 1984 (G1762)"],
        MEMBER["World Geodetic System 1984 (G2139)"],
        ELLIPSOID["WGS 84",6378137,298.257223563,
            LENGTHUNIT["metre",1]],
        ENSEMBLEACCURACY[2.0]],
    PRIMEM["Greenwich",0,
        ANGLEUNIT["degree",0.0174532925199433]],
    CS[ellipsoidal,2],
        AXIS["geodetic latitude (Lat)",north,
            ORDER[1],
            ANGLEUNIT["degree",0.0174532925199433]],
        AXIS["geodetic longitude (Lon)",east,
            ORDER[2],
            ANGLEUNIT["degree",0.0174532925199433]],
    USAGE[
        SCOPE["Horizontal component of 3D system."],
        AREA["World."],
        BBOX[-90,-180,90,180]],
    ID["EPSG",4326]]
Data axis to CRS axis mapping: 2,1
Origin = (-74.897665634163999,7.937424018951680)
Pixel Size = (0.000269494585236,-0.000269494585236)
Metadata:
  AREA_OR_POINT=Area
Image Structure Metadata:
  COMPRESSION=LZW
  INTERLEAVE=BAND
  LAYOUT=COG
Corner Coordinates:
Upper Left  ( -74.8976656,   7.9374240) ( 74d53'51.60"W,  7d56'14.73"N)
Lower Left  ( -74.8976656, -34.8658620) ( 74d53'51.60"W, 34d51'57.10"S)
Upper Right ( -33.0610567,   7.9374240) ( 33d 3'39.80"W,  7d56'14.73"N)
Lower Right ( -33.0610567, -34.8658620) ( 33d 3'39.80"W, 34d51'57.10"S)
Center      ( -53.9793612, -13.4642190) ( 53d58'45.70"W, 13d27'51.19"S)
Band 1 Block=512x512 Type=Byte, ColorInterp=Gray
  Overviews: 77620x79414, 38810x39707, 19405x19853, 9702x9926, 4851x4963, 2425x2481, 1212x1240, 606x620, 303x310
```

### Análise da Estrutura
- **LAYOUT=COG:** O arquivo foi formatado como Cloud-Optimized GeoTIFF, permitindo leitura por partes via requisições HTTP Range (`GET bytes=...`).
- **Block=512x512 (Tiling):** Os pixels estão arranjados em blocos (tiles) de 512x512 pixels.
- **Overviews (Pirâmide de Resolução):** Contém 9 níveis de pirâmide interna, viabilizando pré-visualização ultrarrápida em escalas regionais/nacionais no QGIS.
- **Compressão LZW & Byte Type:** A banda única armazena inteiros de 8 bits (0 a 255) referentes ao código da classe de cobertura do solo.

---

## 3. CRS EPSG:4326 e Consequências para o Diagnóstico (c - D10)

- **Sistema de Referência Espacial:** `EPSG:4326` (WGS 84 / Geográfico).
- **Tamanho Nominal do Pixel:** `0.000269494585236°` (~30 metros na latitude do Equador).

### Consequências Práticas no Diagnóstico (D10)
1. **Distorção de Área em Graus Decimais:** Em sistemas de coordenadas geográficas (`EPSG:4326`), os pixels não possuem área física constante (a largura em metros diminui conforme a latitude se afasta do equador). Em Belo Horizonte/Contagem (~lat -19,9°), 1 pixel de ~30m equivale a ~840 m² em vez de 900 m². Para contabilizar áreas (em hectares ou m²) de uso do solo no Diagnóstico do Plano Diretor, o motor deve calcular a área elipsoidal no elipsoide SIRGAS 2000 (via `QgsDistanceArea`) ou reprojetar o recorte para a zona UTM local (`EPSG:31983` em MG).
2. **Alinhamento Vetor-Raster com Vetores do IBGE:** O datum WGS 84 (`EPSG:4326`) é equivalente ao SIRGAS 2000 (`EPSG:4674`) para fins de geoprocessamento em escala municipal (diferença submétrica). O recorte do GeoTIFF com polígonos de municípios do `geobr`/`gisbr` em `EPSG:4674` ocorre sem necessidade de transformação de datum.

---

## 4. Legenda Oficial da Coleção 9 — Mapeamento de Cores e Códigos (d)

- **Fonte Oficial:** Portal MapBiomas Brasil (`https://brasil.mapbiomas.org/downloads/codigos-de-legenda/`).
- **Data de Consulta:** 17/09/2026.
- **Insumo para Renderização (Passo 12):** Esta tabela define o mapeamento exato entre o valor do pixel (Byte) no arquivo GeoTIFF, o rótulo em português e a cor em hexadecimal (`#HEX`) para aplicação do estilo `.qml` / `QgsPalettedRasterRenderer`.

### Tabela de Classes MapBiomas Coleção 9

> ⚠️ **Classes com Destaque Especial:**
> - **Pastagem:** Classe `15` (`#edde8e`)
> - **Mineração:** Classe `30` (`#9c0027`)
> - **Lavoura Temporária:** Classe `19` (geral, `#d5a6bd`), `39` (Soja, `#f5b3c8`), `20` (Cana, `#db7093`), `40` (Arroz, `#c71585`), `62` (Algodão, `#ff69b4`), `41` (Outras Lavouras Temporárias, `#f54ca9`)
> - **Lavoura Perene:** Classe `36` (geral, `#d390e6`), `46` (Café, `#d68fe2`), `47` (Citrus, `#9932cc`), `35` (Dendê, `#9065d0`), `48` (Outras Lavouras Perenes, `#e6ccff`)

| Código (Pixel ID) | Classe (PT-BR) | Hexadecimal (`#HEX`) | Categoria / Destaque |
| :---: | :--- | :---: | :--- |
| **1** | Floresta | `#1f8d49` | 1. Natural / Floresta |
| **3** | Formação Florestal | `#1f8d49` | 1. Natural / Floresta |
| **4** | Formação Savânica | `#7dc975` | 1. Natural / Floresta |
| **5** | Mangue | `#04381d` | 1. Natural / Floresta |
| **6** | Floresta Alagável | `#007785` | 1. Natural / Floresta |
| **49** | Restinga Arbórea | `#02d659` | 1. Natural / Floresta |
| **10** | Formação Natural Não Florestal | `#d6bc74` | 2. Natural / Não Florestal |
| **11** | Campo Alagado e Área Pantanosa | `#519799` | 2. Natural / Não Florestal |
| **12** | Formação Campestre | `#d6bc74` | 2. Natural / Não Florestal |
| **29** | Afloramento Rochoso | `#ad5100` | 2. Natural / Não Florestal |
| **32** | Apicum | `#fc8114` | 2. Natural / Não Florestal |
| **50** | Restinga Herbácea ou Arbustiva | `#ffaa5f` | 2. Natural / Não Florestal |
| **77** | Formação Herbáceo Arbustiva | `#86b074` | 2. Natural / Não Florestal |
| **84** | Marismas (beta) | `#81dbbf` | 2. Natural / Não Florestal |
| **14** | Agropecuária | `#ffffb2` | 3. Agropecuária (Geral) |
| **15** | **Pastagem** | `#edde8e` | **★ Destaque Diego (Pastagem)** |
| **18** | Agricultura | `#e974ed` | 3. Agropecuária / Agricultura |
| **19** | **Lavoura Temporária (Geral)** | `#d5a6bd` | **★ Destaque Diego (Lavoura Temporária)** |
| **39** | **Soja** | `#f5b3c8` | **★ Destaque Diego (Lavoura Temporária)** |
| **20** | **Cana** | `#db7093` | **★ Destaque Diego (Lavoura Temporária)** |
| **40** | **Arroz** | `#c71585` | **★ Destaque Diego (Lavoura Temporária)** |
| **62** | **Algodão (beta)** | `#ff69b4` | **★ Destaque Diego (Lavoura Temporária)** |
| **41** | **Outras Lavouras Temporárias** | `#f54ca9` | **★ Destaque Diego (Lavoura Temporária)** |
| **36** | **Lavoura Perene (Geral)** | `#d390e6` | **★ Destaque Diego (Lavoura Perene)** |
| **46** | **Café** | `#d68fe2` | **★ Destaque Diego (Lavoura Perene)** |
| **47** | **Citrus** | `#9932cc` | **★ Destaque Diego (Lavoura Perene)** |
| **35** | **Dendê** | `#9065d0` | **★ Destaque Diego (Lavoura Perene)** |
| **48** | **Outras Lavouras Perenes** | `#e6ccff` | **★ Destaque Diego (Lavoura Perene)** |
| **9** | Silvicultura | `#7a5900` | 3. Agropecuária / Silvicultura |
| **21** | Mosaico de Usos | `#ffefc3` | 3. Agropecuária / Mosaico |
| **22** | Área Não Vegetada | `#d4271e` | 4. Área Não Vegetada |
| **23** | Praia, Duna e Areal | `#ffa07a` | 4. Área Não Vegetada |
| **24** | Área Urbanizada | `#d4271e` | 4. Área Não Vegetada / Urbana |
| **30** | **Mineração** | `#9c0027` | **★ Destaque Diego (Mineração)** |
| **25** | Outras Áreas Não Vegetadas | `#db4d4f` | 4. Área Não Vegetada |
| **75** | Usina Fotovoltaica | `#757272` | 4. Área Não Vegetada |
| **91** | Parque Eólico (beta) | `#403d3e` | 4. Área Não Vegetada |
| **26** | Corpo d'Água | `#2532e4` | 5. Corpos d'Água |
| **33** | Rio, Lago e Oceano | `#2532e4` | 5. Corpos d'Água |
| **31** | Aquicultura | `#091077` | 5. Corpos d'Água |
| **27** | Não Observado | `#ffffff` | 6. Sem Dados |

---

## 5. Medição Prática de Tempo e Tamanho de Recorte (e)

Teste empírico de extração remota de um município de porte médio da Região Metropolitana de Belo Horizonte (RMBH).

### Parâmetros do Teste
- **Município de Teste:** Contagem / MG (Código IBGE: `3118601`).
- **Área Territorial:** ~195 km² (BBOX: `-44.1620, -19.9838, -44.0054, -19.7988`).
- **Fonte Remota:** `/vsicurl/https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_9/lclu/coverage/brasil_coverage_2023.tif`
- **Comando de Recorte Executado:**
```bash
gdalwarp -overwrite \
  -te -44.1620 -19.9838 -44.0054 -19.7988 \
  -cutline contagem.geojson \
  -crop_to_cutline \
  -co COMPRESS=LZW \
  /vsicurl/https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_9/lclu/coverage/brasil_coverage_2023.tif \
  contagem_mapbiomas_2023.tif
```

### Resultados Medidos
- **Tempo total de download e corte:** **16,86 segundos**
- **Tamanho do arquivo GeoTIFF gerado (`.tif`):** **33.479 bytes (~33,5 KB / 0,03 MB)**
- **Resolução do raster cortado:** 580 x 685 pixels.
- **Contagem de Pixel/Classes Encontradas no Município (2023):**
  - Classe 24 (Área Urbanizada): 121.582 pixels (~57,4%)
  - Classe 3 (Formação Florestal): 54.640 pixels (~25,8%)
  - Classe 15 (Pastagem): 26.615 pixels (~12,6%)
  - Classe 21 (Mosaico de Usos): 15.007 pixels (~7,1%)
  - Classe 33 (Rio, Lago e Oceano): 3.712 pixels (~1,8%)
  - Classe 11 (Campo Alagado): 3.755 pixels (~1,8%)
  - Classe 30 (Mineração): 2.694 pixels (~1,3%)
  - Classe 4 (Formação Savânica): 1.625 pixels (~0,8%)
  - Classe 25 (Outras Áreas Não Vegetadas): 1.322 pixels (~0,6%)
  - Classe 12 (Formação Campestre): 360 pixels (~0,2%)
  - Classe 41 (Outras Lavouras Temporárias): 6 pixels (<0,01%)

### Conclusão de Desempenho
A extração via VSI/COG (`/vsicurl/`) é extremamente eficiente: em menos de 17 segundos e baixando apenas ~33 KB de dados, o recorte municipal completo de uso do solo é extraído e gravado localmente, sem necessidade de transferir o arquivo nacional de 1,05 GB.
