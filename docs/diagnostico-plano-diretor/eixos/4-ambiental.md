# Eixo 4: Ambiental

Este eixo compreende as bases de vegetação, uso e cobertura do solo, áreas protegidas, áreas vulneráveis de risco geológico/hidrológico, e o cadastro ambiental rural (CAR) de propriedades privadas. Serve para o zoneamento ambiental, definição de áreas non-aedificandi e mitigação de desastres no Plano Diretor.

## Catálogo de Geoservers e Serviços

| Fonte / Órgão | Nível | Serviço | Endpoint / URL | Camadas Principais | CRS | Licença | Data de Acesso | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **SICAR** | Federal | WFS | `https://geoserver.car.gov.br/geoserver/sicar/wfs?service=WFS&version=2.0.0&request=GetCapabilities` | `sicar:sicar_imoveis_<uf>` (ex: `sicar:sicar_imoveis_mg` para Minas Gerais) | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. Filtrar via `cod_municipio_ibge (int)` ou `municipio (string)` |
| **ICMBio** | Federal | WFS | `https://geoservicos.inde.gov.br/geoserver/ICMBio/ows?service=WFS&version=2.0.0&request=GetCapabilities` | `ICMBio:limiteucsfederais_a` (Unidades de Conservação Federais)<br>`ICMBio:embargos_icmbio` (Embargos ICMBio) | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. `limiteucsfederais_a` requer bbox; `embargos_icmbio` filtra por `municipio (string)` |
| **MapBiomas Alertas** | Nacional (ONG) | WMS | `https://production.alerta.mapbiomas.org/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities` | `mapbiomas-alertas:crew_alerts` (Polígonos de Alertas de Desmatamento)<br>`mapbiomas-alertas:crew_alerts-within-rural-properties` | EPSG:4326 | CC-BY-SA | 29/06/2026 | Online - GetCapabilities verificado. Filtrar por BBOX espacial |
| **IBAMA** | Federal | ArcGIS REST | `https://pamgia.ibama.gov.br/server/rest/services/app_dadosabertos/adm_auto_infracao_p/MapServer` | `0` (Autos de Infração e Embargos) | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. Filtrar via `cod_municipio (integer)` ou `municipio (string)` |
| **IDE-Sisema (MG)** | Estadual | WFS | `https://geoserver.meioambiente.mg.gov.br/IDE/wfs?service=WFS&version=2.0.0&request=GetCapabilities` | Camadas de ZEE (Zoneamento Ecológico-Econômico de MG), UCs Estaduais e Áreas de Preservação | EPSG:4674 | Pública / Open Data | 29/06/2026 | Online - GetCapabilities verificado. Filtrar por BBOX espacial |

## Integração no GisBR
- **Cobertura Atual: Média.** O GisBR já possui algoritmos locais para baixar biomas (`read_biomes`), Amazônia Legal (`read_amazon`), unidades de conservação (`read_conservation_units`) e terras indígenas (`read_indigenous_land`).
- **Próximos Passos:** 
  - Desenvolver conector WFS para obter os imóveis do SICAR filtrados dinamicamente por município (usando `CQL_FILTER` na camada `sicar:sicar_imoveis_<uf>`).
  - Integrar os alertas de desmatamento do MapBiomas Alertas para cruzamento com os polígonos do CAR.
- **Validação no QGIS (a validar):** No QGIS, baixar os imóveis de um município via WFS do SICAR aplicando filtro pelo nome do município.
