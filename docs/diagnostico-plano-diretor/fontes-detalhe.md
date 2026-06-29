# Consolidação do Catálogo de Fontes (Hardening)

Esta tabela consolidada mapeia os metadados exatos de todas as fontes geoespaciais ativas (WFS e ArcGIS REST) identificadas para subsidiar o diagnóstico municipal do Plano Diretor. Ela serve como especificação direta para o futuro registro de fontes `core/sources.py`.

## Tabela Consolidada de Fontes

| id | eixo | protocolo | endpoint | type_name/layer | crs | output_format | campo_muni (nome exato + tipo) | licenca | status (data) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **dnit_snv** | 1. Transportes | WFS | `https://geoservicos.inde.gov.br/geoserver/DNIT/ows` | `DNIT:snv_202507a` | EPSG:4674 | application/json | `sem campo muni -> filtrar por bbox` *(tem sg_uf)* | Pública | Online (29/06/2026) |
| **dnit_cide** | 1. Transportes | WFS | `https://geoservicos.inde.gov.br/geoserver/DNIT/ows` | `DNIT:cide_2024_25` | EPSG:4674 | application/json | `sem campo muni -> filtrar por bbox` *(tem uf)* | Pública | Online (29/06/2026) |
| **minfra_ferrovias** | 1. Transportes | WFS | `https://geoservicos.inde.gov.br/geoserver/ows` | `MInfra:Ferrovias` | EPSG:4674 | application/json | `municipio (string)` / `uf (string)` | Pública | Online (29/06/2026) |
| **minfra_rodovias** | 1. Transportes | WFS | `https://geoservicos.inde.gov.br/geoserver/ows` | `MInfra:Rodovias Federais` | EPSG:4674 | application/json | `sem campo muni -> filtrar por bbox` *(tem sg_uf)* | Pública | Online (29/06/2026) |
| **der_mg_rodovias** | 1. Transportes | WFS | `https://geoserver.meioambiente.mg.gov.br/IDE/wfs` | `IDE:ide_0401_mg_rodovias_lin` | EPSG:4674 | application/json | `sem campo muni -> filtrar por bbox` *(tem unidade_fe)* | Pública | Online (29/06/2026) |
| **der_mg_ferrovias** | 1. Transportes | WFS | `https://geoserver.meioambiente.mg.gov.br/IDE/wfs` | `IDE:ide_0402_mg_ferrovias_lin` | EPSG:4674 | application/json | `sem campo muni -> filtrar por bbox` | Pública | Online (29/06/2026) |
| **ana_municipios** | 3. Demografia | ArcGIS REST | `https://www.snirh.gov.br/arcgis/rest/services/DADOSABERTOS/Municipios/MapServer` | `0` | EPSG:4674 | JSON | `CD_MUNIBGE (esriFieldTypeInteger)` / `CD_GEOCMU (string)` | Pública | Online (29/06/2026) |
| **ana_hidrografia** | 2. Drenagem/San. | ArcGIS REST | `https://www.snirh.gov.br/arcgis/rest/services/DADOSABERTOS/Hidrografia/MapServer` | `0` | EPSG:4674 | JSON | `sem campo muni -> filtrar por bbox` | Pública | Online (29/06/2026) |
| **sgb_rios** | 2. Drenagem/San. | WFS | `https://opendata.sgb.gov.br/geoserver/ows` | `p3m:vw_ibge_rios` | EPSG:4674 | application/json | `sem campo muni -> filtrar por bbox` | Pública | Online (29/06/2026) |
| **sgb_bacias** | 2. Drenagem/San. | WFS | `https://opendata.sgb.gov.br/geoserver/ows` | `p3m:vw_ibge_bacia_hidro_6` | EPSG:4674 | application/json | `sem campo muni -> filtrar por bbox` | Pública | Online (29/06/2026) |
| **sgb_hidrogeologia** | 2. Drenagem/San. | WFS | `https://opendata.sgb.gov.br/geoserver/ows` | `p3m:vw_cprm_pol_a_hidrog` | EPSG:4674 | application/json | `sem campo muni -> filtrar por bbox` | Pública | Online (29/06/2026) |
| **sicar_imoveis** | 4. Ambiental | WFS | `https://geoserver.car.gov.br/geoserver/sicar/wfs` | `sicar:sicar_imoveis_<uf>` | EPSG:4674 | application/json | `cod_municipio_ibge (int)` / `municipio (string)` | Pública | Online (29/06/2026) |
| **icmbio_uc** | 4. Ambiental | WFS | `https://geoservicos.inde.gov.br/geoserver/ICMBio/ows` | `ICMBio:limiteucsfederais_a` | EPSG:4674 | application/json | `sem campo muni -> filtrar por bbox` *(tem ufabrang)* | Pública | Online (29/06/2026) |
| **icmbio_embargos** | 4. Ambiental | WFS | `https://geoservicos.inde.gov.br/geoserver/ICMBio/ows` | `ICMBio:embargos_icmbio` | EPSG:4674 | application/json | `municipio (string)` / `uf (string)` | Pública | Online (29/06/2026) |
| **ibama_autos** | 4. Ambiental | ArcGIS REST | `https://pamgia.ibama.gov.br/server/rest/services/app_dadosabertos/adm_auto_infracao_p/MapServer` | `0` | EPSG:4674 | JSON | `cod_municipio (esriFieldTypeInteger)` / `municipio (string)` | Pública | Online (29/06/2026) |
| **ibama_esgoto** | 2. Drenagem/San. | ArcGIS REST | `https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Sistema_de_Esgotamento_Sanit%C3%A1rio/MapServer` | `6` | EPSG:4674 | JSON | `sem campo muni -> filtrar por bbox` | Pública | Online (29/06/2026) |
| **ibama_agua** | 2. Drenagem/San. | ArcGIS REST | `https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Sistema_de_Abastecimento_de_%C3%81gua/MapServer` | `5` | EPSG:4674 | JSON | `sem campo muni -> filtrar por bbox` | Pública | Online (29/06/2026) |
| **ibama_aterro** | 2. Drenagem/San. | ArcGIS REST | `https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Aterro_Sanit%C3%A1rio/MapServer` | `8` | EPSG:4674 | JSON | `sem campo muni -> filtrar por bbox` | Pública | Online (29/06/2026) |

---

## Detalhamento de Estratégias de Filtragem

### 1. Filtragem por Código/Nome Municipal (CQL_FILTER / where=)
Fontes que possuem atributos municipais nativos e exatos permitem realizar requisições leves, extraindo apenas os dados de interesse direto do servidor:
*   **SICAR (`sicar_imoveis`):** Filtrar via CQL `cod_municipio_ibge = <codigo_ibge_7_digitos>` ou `municipio = '<NOME_MUNICIPIO>'`.
*   **IBAMA Autos (`ibama_autos`):** Filtrar via parâmetro `where=cod_municipio=<codigo_ibge_7_digitos>` ou `where=municipio='<NOME_MUNICIPIO>'`.
*   **MInfra Ferrovias (`minfra_ferrovias`):** Filtrar via CQL `municipio = '<NOME_MUNICIPIO>'`.
*   **ICMBio Embargos (`icmbio_embargos`):** Filtrar via CQL `municipio = '<NOME_MUNICIPIO>'`.
*   **ANA Municípios (`ana_municipios`):** Filtrar via parâmetro `where=CD_MUNIBGE=<codigo_ibge_7_digitos>` ou `where=CD_GEOCMU='<codigo_ibge_7_digitos>'`.

### 2. Filtragem Espacial por Bounding Box (BBOX / geometry=)
Fontes que não possuem campo municipal explícito ou padronizado no nível de feição exigem filtragem geográfica. O fluxo de integração consistirá em obter a Bounding Box (BBOX) do município (utilizando a camada do GisBR via `read_municipality`) e repassar as coordenadas da BBOX para a requisição do serviço:
*   **Para WFS (ex: DNIT, CPRM, DER-MG, ICMBio UCs):** Passar o parâmetro `bbox=<minx>,<miny>,<maxx>,<maxy>,urn:ogc:def:crs:EPSG::4674` na URL do `GetFeature`.
*   **Para ArcGIS REST (ex: ANA Hidrografia, IBAMA Saneamento):** Passar os parâmetros `geometry=<minx>,<miny>,<maxx>,<maxy>&geometryType=esriGeometryEnvelope&spatialRel=esriSpatialRelIntersects&inSR=4674`.
*   **Nota de Otimização:** Opcionalmente, pode-se combinar a filtragem de BBOX com a filtragem por Estado/UF (ex: `sg_uf = 'MG'` no DNIT ou `unidade_fe = 'MG'` no DER-MG) para diminuir ainda mais o volume de varredura no banco do servidor.
