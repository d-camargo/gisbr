# Fontes Candidatas — Rodada 7 (julho/2026)

Levantamento ao vivo das fontes candidatas à ampliação do catálogo `SOURCES`
(29 → 44 fontes entregues), reunido para fechar as lacunas de **risco geológico**,
**meio físico**, **processos minerários**, **hidrografia/viário BC250
2025**, **áreas urbanizadas/aglomerados subnormais IBGE** e a infraestrutura
logística do **ONTL / INFRA S.A.**

Todas as medições usaram a **bbox de Contagem/MG**
(`-44.20,-20.05,-43.90,-19.85`, EPSG:4674), no mesmo formato que os
conectores `wfs.py` / `arcgis_rest.py` já emitem, em **29/07/2026**.

## Fontes medidas

| Fonte | Protocolo / camada | `type_name` / `layer_id` | Filtro | Contagem obtida (bbox Contagem) | Data da medição |
| --- | --- | --- | --- | --- | --- |
| SGB/CPRM — Risco geológico | WFS | `gestao-territorial:risco_geologico` | bbox | 265 setores (Contagem, Betim, Nova Lima, Ibirité) — atributos `municipio`, `tipolo_g1`, `cobrade_01`, `descricao`, `grau` | 29/07/2026 |
| SGB/CPRM — Poços SIAGAS | WFS | `hidrologia:pocos_siagas` | bbox | 772 poços | 29/07/2026 |
| ANM/SIGMINE — Processos minerários | ArcGIS REST | `SIGMINE/dados_anm/MapServer/0` | bbox | 144 processos — atributos `FASE`, `SUBS`, `USO`, `AREA_HA` | 29/07/2026 |
| IBGE — BC250 2025, drenagem | WFS | `CCAR:BC250_2025_hid_trecho_drenagem_l` | bbox | 122 trechos | 29/07/2026 |
| IBGE — BC250 2025, rodovias | WFS | `CCAR:BC250_2025_rod_trecho_rodoviario_l` | bbox | 64 trechos — atributos `jurisdicao`, `revestimento`, `nrfaixas` | 29/07/2026 |
| IBGE — BC250 2025, ferrovias | WFS | `CCAR:BC250_2025_fer_trecho_ferroviario_l` | bbox | 9 trechos — atributos `jurisdicao`, `bitola`, `nrlinhas`, `concessionaria` | 29/07/2026 |
| IBGE — BC250 2025, área densamente edificada | WFS | `CCAR:BC250_2025_lml_area_densamente_edificada_a` | bbox | 9 polígonos | 29/07/2026 |
| IBGE — Áreas urbanizadas 2019 | WFS | `CGEO:AU_2022_AreasUrbanizadas2019_Municipios` | `cd_mun` | 291 polígonos — atributos `densidade`, `tipo`, `area_km2` | 29/07/2026 |
| IBGE — Aglomerados subnormais 2010 | WFS | `CGEO:AglomeradosSubnormais2010_Limites` | `cd_geocodm` | 185 polígonos — atributos `populacao`, `nm_agsn` | 29/07/2026 |
| IBGE/BDIA — Pedologia | WFS | `BDIA:pedo_area` | bbox | 35 polígonos | 29/07/2026 |
| IBGE/BDIA — Geologia | WFS | `BDIA:geol_area` | bbox | 34 polígonos | 29/07/2026 |
| IBGE/BDIA — Geomorfologia | WFS | `BDIA:geom_area` | bbox | 22 polígonos — atributos `nm_unidade`, `nm_dominio`, `categoria` | 29/07/2026 |
| IBGE/BDIA — Vegetação | WFS | `BDIA:vege_area` | bbox | 48 polígonos | 29/07/2026 |
| INFRA S.A. (ONTL) — geoportal ArcGIS | ArcGIS REST | `geo.infrasa.gov.br/server/rest/services` (pastas `Portal_Rodoviario`, `Ferroviario`, `Aeroviario`, `Portal_Aquaviario`, `Potal_Dutoviario`) | — | Público e enumerável (versão de servidor 11.5), mas **instável no dia da medição**: vários serviços respondem HTTP 200 com corpo `{"error":{"code":500,"message":"GISService not instantiated..."}}`; `Acidentes_rodoviarios_DPRF` responde metadado com `"layers": []` | 29/07/2026 |

## Host → âncora TLS

Medido com `openssl s_client -showcerts`; todos com `Verify return code: 0`.

| Host novo | Cadeia termina em | Já coberto por `gisbr/core/certs/`? |
| --- | --- | --- |
| `geoservicos.ibge.gov.br` | Sectigo Public Server Authentication Root R46 (cross USERTrust RSA) | Sim |
| `geo.infrasa.gov.br` | Sectigo CA OV R36 → Root R46 | Sim |
| `geo.anm.gov.br` | Valid Certificadora RSA OV SSL CA 2 → Sectigo Root R46 | Sim |
| `sigel.aneel.gov.br` | Sectigo CA OV R36 → Root R46 | Sim |
| `terrabrasilis.dpi.inpe.br` | ISRG Root YE → ISRG Root X2 | Sim |
| `opendata.sgb.gov.br` (já em uso) | GlobalSign Root R46 (via RNP ICPEdu) | Sim |

**Resultado que define a rodada:** nenhuma raiz nova é necessária — o
`ca_roots.pem` da Rodada 5 já cobre todas as fontes propostas acima; a
ampliação do catálogo é puramente dado, sem tocar em `ssl_support.py` nem em
`certs/`. Contraexemplo registrado abaixo (`apidadosabertos.saude.gov.br`).

## Descartadas e por quê

- **ONTL tabular (`ontl-apim.infrasa.gov.br`)** — a página pública
  `ontl.infrasa.gov.br/dados/consulta-a-base-de-dados/` é um iframe para um
  SPA Laravel. O endpoint `/api/datasets` devolve 15 registros com nomes
  genéricos (`"Dataset 127"`, `"Dataset 128"`), sem tema, sem esquema e sem
  geometria — são anexos de painéis Metabase (`metabase_id`,
  `arquivo: "128.csv"`). A resposta ainda vaza e-mails internos e um campo
  `arquivo` apontando para `../../.env`. Não é uma API publicada, é o
  backoffice de um painel: não dá para construir fonte estável em cima
  disso, e não é dado espacial.
- **API do Ministério da Saúde (`apidadosabertos.saude.gov.br`)** — ancora em
  **GlobalSign Root CA - R3**, que não está embarcada no `ca_roots.pem`
  atual. Fica fora desta rodada; é o caso que justifica o passo 41
  (`tools/check_sources_tls.py`) e o passo 42 registra a necessidade de
  cobertura futura da raiz.
- **MapBiomas** — dado raster/GEE, fora do contrato dos conectores atuais
  (WFS/ArcGIS REST vetorial).
- **TerraBrasilis** — recorte por bioma, não por município; não cabe no
  motor de recorte por polígono municipal do `diagnostico.py`.
- **ANEEL `PORTAL/Transmissão`** — a camada 0 é *Group Layer* (não
  consultável) e a camada 1 devolve atributos de KML (`OID`, `FolderPath`,
  `SymbolID`), sem valor analítico. A pasta `DadosAbertos` do mesmo servidor
  não foi varrida. Entra como pesquisa registrada, não como fonte entregue.

## Backlog — candidatos ONTL testados individualmente (passo 49, 29/07/2026)

Teste ao vivo (`.../MapServer?f=json` e `.../FeatureServer?f=json`, com
verificação TLS padrão — a cadeia já confere com a Rodada 7) dos 9 serviços
candidatos do Eixo 1 listados no plano. **Nenhum devolveu feições**, então
**nenhum entrou em `SOURCES`** nesta rodada:

| Serviço | Resultado (29/07/2026) |
| --- | --- |
| `Portal_Rodoviario/Pracas_de_pedagio_ABCR` | Timeout (sem resposta em 15–30s) |
| `Portal_Rodoviario/Equipamento_de_Fiscalizacao` | Timeout (sem resposta em 15s) |
| `Ferroviario/Base_Ferroviaria` | Timeout (sem resposta em 15s) |
| `Ferroviario/Estacoes_Ferroviarias_ANTT` | Timeout (sem resposta em 15s) |
| `Ferroviario/Terminais_Ferroviarios` | Timeout (sem resposta em 15–30s) |
| `Aeroviario/Aerodromos` | HTTP 200 com corpo de erro: `{"error":{"code":500,"message":"GISService not instantiated..."}}` |
| `Portal_Aquaviario/Terminais_portuarios` | Timeout (sem resposta em 15s) |
| `Portal_Aquaviario/Hidrovias_Navegaveis_Rios_Priorizados` | Timeout (sem resposta em 15s) |
| `Potal_Dutoviario/Dutovias_MINFRA` | Timeout (sem resposta em 15–30s) |

Reavaliar numa rodada futura — o servidor `geo.infrasa.gov.br` pode
estabilizar. Nenhuma mudança em `gisbr/core/sources.py` decorre deste
resultado.

*Nota: este material serve como referência de arquitetura para o plugin
GisBR e não é empacotado na versão distribuída no QGIS (§10 do CLAUDE.md).*
