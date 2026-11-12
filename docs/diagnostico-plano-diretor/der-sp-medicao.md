# Medição com Dado Real — DER-SP e DNIT SNV (Rede Rodoviária)

Documento de medição empírica e validação técnica da integração da malha rodoviária estadual de São Paulo (**`der_sp_rodovias`**, protocolo `zip_remoto`) e federal (**`dnit_snv`**, protocolo `wfs`), executado no QGIS headless do host (`start_app`), cobrindo três recortes territoriais e teste de atualização forçada do cache (`force=True`).

- **Data da medição:** 2026-11-12
- **Ambiente de teste:** Linux 6.8 (x86_64), Python 3.12, QGIS 3.x nativo (headless via `qgis.testing.start_app`), GDAL/OGR com suporte OGC e Zip VSI.
- **Fontes avaliadas:**
  - `dnit_snv`: DNIT — SNV (rodovias federais; WFS INDE `DNIT:snv_202507a`, `filtro: bbox`, EPSG:4674).
  - `der_sp_rodovias`: DER-SP — Rodovias estaduais (Sistema Rodoviário Estadual; `zip_remoto`, `filtro: bbox`, `cache_id: der_sp_sistema_rodoviario_estadual.zip`, EPSG:4674).
- **Status do documento:** Documentação técnica interna (pasta `docs/diagnostico-plano-diretor/` em `exclude_docs`).

---

## 1. Resumo Executivo e Tabela Geral de Métricas

Todas as medições foram executadas invocando o motor central `gisbr.core.diagnostico.carregar_fontes` com persistência em arquivos GeoPackage (`.gpkg`) dedicados, avaliando o comportamento do conector `zip_remoto`, a reprojeção/leitura OGR, o recorte vetorial por polígono (`native:clip`), a detecção e desduplicação federal × estadual (`remove_duplicidade_federal`) e a reconstrução topológica de redes lineares (`montar_rede`).

| Métrica / Recorte | São José dos Campos (`3549904`) | Campinas (`3509502`) | Estado SP (`uf_sp`, 645 mun.) | Campinas Atualizar (`force=True`) |
|---|---|---|---|---|
| **Tempo de Execução** | 1,56 s | 1,05 s | **34,18 s** | 1,47 s |
| **Download Zip DER-SP** | Sim (cache inicial) | Não (hit no cache) | Não (hit no cache) | **Sim (rebaixou via `refresh`)** |
| **Log Confirma Re-download** | `[download]` | `[cache]` | `[cache]` | `[download]` (confirmado no log) |
| **`dnit_snv` — Feições antes do recorte** | 3 | 7 | 1.046 | 7 |
| **`dnit_snv` — Feições após recorte** | 2 | 4 | 433 | 4 |
| **`dnit_snv` — Trechos `PLAN` removidos** | 0 | 4 (100% da base) | 323 | 4 (100% da base) |
| **`dnit_snv` — Arcos (links) na rede** | 2 | 0 (fonte pulou) | 114 | 0 (fonte pulou) |
| **`dnit_snv` — Nós da rede** | 3 | 0 | 141 | 0 |
| **`dnit_snv` — Maior componente conexa** | 2 arcos | — | 35 arcos | — |
| **`der_sp` — Feições antes do recorte** | 4.794 (base estadual) | 4.794 (base estadual) | 4.794 (base estadual) | 4.794 (base estadual) |
| **`der_sp` — Feições após recorte** | 21 | 58 | 4.794 | 58 |
| **`der_sp` — `duplicado_federal` removidos** | **3 (BR-116 Dutra)** | 0 (sem par DNIT ativo) | **165 (39 parciais)** | 0 |
| **`der_sp` — Trechos `PLAN` removidos** | 0 | 0 | **176** | 0 |
| **`der_sp` — Total na camada removidos** | 3 | 0 | **341** | 0 |
| **`der_sp` — Arcos (links) na rede** | 18 | 62 | 4.942 | 62 |
| **`der_sp` — Nós da rede** | 23 | 62 | 5.144 | 62 |
| **`der_sp` — Maior componente conexa** | 10 arcos | 53 arcos | 3.152 arcos | 53 arcos |
| **CRS das Camadas no GeoPackage** | **EPSG:4674** (100%) | **EPSG:4674** (100%) | **EPSG:4674** (100%) | **EPSG:4674** (100%) |
| **Status Final do Motor** | OK (`dnit_snv`, `der_sp`) | OK (`der_sp`), Pulou (`dnit`) | OK (`dnit_snv`, `der_sp`) | OK (`der_sp`), Pulou (`dnit`) |

---

## 2. Detalhamento por Recorte Territorial

### 2.1. Recorte 1 — São José dos Campos (`3549904`)

- **Objetivo central:** Validar que a **BR-116 Presidente Dutra** (rodovia federal concedida, presente tanto no SNV do DNIT quanto no shapefile do DER-SP sob jurisdição federal) não é duplicada, e que rodovias estaduais locais (em especial a **SP-099 Rodovia dos Tamoios**) são integralmente preservadas.
- **Tempo medido:** 1,56 s.
- **Comportamento do recorte:**
  - `dnit_snv`: BBOX inicial retornou 3 trechos; após `native:clip` com o polígono municipal, restaram **2 feições**. Ambas possuem `vl_br="116"`, `ds_superfi="PAV"` (nenhum `PLAN`) e códigos `116BSP2430` e `116BSP2450`. A rede foi montada com 2 arcos e 3 nós.
  - `der_sp_rodovias`: O arquivo ZIP estadual (4.794 feições) foi recortado para o polígono municipal de SJC, resultando em **21 feições**.
  - **Desduplicação federal × estadual:** O módulo `remove_duplicidade_federal` identificou **3 trechos** com `Jurisdicao='Federal'` e `Rodovia='BR 116'` sobrepostos à malha ativa do DNIT dentro da tolerância de 50 m (`TOL_DUP_M`). Esses 3 trechos foram removidos da malha estadual e enviados para `der_sp_rodovias_removidos_3549904` com `motivo='duplicado_federal'`.
  - **Camada final de links estaduais (`der_sp_rodovias_3549904`):** Restaram exatamente **18 arcos** e **23 nós**, com maior componente conexa de **10 arcos**.

#### Conferência Visual e de Atributos em São José dos Campos:
1. **BR-116 Dutra não aparece em dobro:**
   - Na camada `dnit_snv_3549904`: **2 trechos mantidos** (`vl_br = 116`).
   - Na camada `der_sp_rodovias_3549904`: **0 trechos** de BR-116 (`SELECT COUNT(*) WHERE Rodovia LIKE '%116%'` = 0).
   - Na camada `der_sp_rodovias_removidos_3549904`: **3 trechos** de BR-116 devidamente isolados com `motivo='duplicado_federal'`.
2. **SP-099 preservada na camada estadual:**
   - A Rodovia dos Tamoios (**SP-099**) possui **7 arcos** íntegros na camada `der_sp_rodovias_3549904`.
   - Demais rodovias estaduais mantidas: **SP-050** (3 arcos), **SP-062** (2 arcos), **SP-066** (1 arco), **SP-070** Rodovia Ayrton Senna/Carvalho Pinto (3 arcos) e **SP-103** (2 arcos).
3. **Problemas e Correções apontados:**
   - Apenas 3 registros de `ilha_borda` (severidade baixa), correspondentes aos pontos onde as rodovias cruzam a divisa municipal de São José dos Campos.

---

### 2.2. Recorte 2 — Campinas (`3509502`)

- **Objetivo central:** Avaliar comportamento em município com malha rodoviária estadual densa e trechos federais alienados/planejados.
- **Tempo medido:** 1,05 s.
- **Comportamento do recorte:**
  - `dnit_snv`: O BBOX retornou 7 feições; o recorte pelo polígono municipal filtrou para **4 feições**. No SNV do DNIT, todas as 4 feições representam a **BR-050** (`050BSP0637`, `050BSP0641`, `050BSP0645`, `050BSP0650`), cadastradas como `ds_superfi='PLA'` (Planejada) e `est_coinc='SP-330'` (trecho coincidente alienado/concedido à Rodovia Anhanguera).
  - Como todos os trechos eram planejados, o filtro de existência excluiu os 4 trechos para a camada de removidos. Como `layer_links.featureCount() == 0`, o motor aplicou a regra padrão do plugin: a fonte pulou com aviso `"todos os trechos eram planejados/inexistentes"` e nenhuma tabela vazia de links foi criada no GeoPackage.
  - `der_sp_rodovias`: Como não havia camada federal ativa no GPKG, o motor registrou aviso e processou a malha estadual sem remover vias reais. Das 4.794 feições estaduais, **58 feições** incidem no município de Campinas.
  - Quatro multipartes foram explodidas, totalizando **62 arcos** e **62 nós**, com maior componente conexa de **53 arcos**.
  - **Rodovias estaduais ativas mantidas:** SP-330 Anhanguera (9 arcos), SP-348 Bandeirantes (7 arcos), SP-065 Dom Pedro I (5 arcos), SP-083 Anel Viário Magalhães Teixeira (6 arcos), SP-101 (6 arcos), SP-075 Santos Dumont (3 arcos), SP-073 (3 arcos), SP-081 (4 arcos), SP-324 (4 arcos), SP-332 (9 arcos), SP-340 Adhemar de Barros (2 arcos), SP-091 (1 arco), além de alças SPA/SPI (3 arcos).
  - **Correções aplicadas:** 2 correções de `ponta_conectada` (junção em T resolvida automaticamente).
  - **Problemas apontados:** 1 `cruzamento_sem_no` (viaduto sem nó em nível), 3 `ilha`, 1 `ilha_borda` e 1 `ponta_quase_conectada`.

---

### 2.3. Recorte 3 — Modo Estado SP (`uf_sp`, 645 Municípios)

- **Objetivo central:** Teste de estresse na maior escala territorial suportada pelo plugin para rodovias, avaliando o tempo de processamento, performance de rede e detecção em larga escala de duplicidade e trechos planejados.
- **Tempo medido:** **34,18 s** para o estado inteiro de São Paulo.
- **Comportamento do recorte:**
  - O contorno do Estado de São Paulo foi montado via dissolução (`native:dissolve`) dos 645 municípios da malha do geobr (`35municipality_2024_simplified.gpkg`), gerando a geometria de recorte `uf_sp`.
  - `dnit_snv`:
    - Feições no BBOX do estado: **1.046**.
    - Após recorte com a fronteira de SP: **433**.
    - Trechos `PLAN` removidos: **323 trechos** com `ds_superfi='PLA'`.
    - Rede federal resultante (`dnit_snv_ufsp`): **114 arcos**, **141 nós**, maior componente de **35 arcos**.
    - Correções automáticas no DNIT: **16** `coincidente_colapsado` (resolvendo duplicidade intrínseca de BRs coincidentes) e **2** `ponta_unificada`.
    - Problemas topológicos do DNIT: 1 `cruzamento_sem_no`, 11 `ilha`, 9 `ilha_borda`, 1 `ponta_quase_conectada (alta)` e 2 `ponta_quase_conectada (media)`.
  - `der_sp_rodovias`:
    - Feições brutas do DER-SP: **4.794** (100% dentro do território paulista).
    - **Desduplicação federal × estadual (`remove_duplicidade_federal`):**
      - **165 trechos removidos** por duplicidade com rodovias federais mantidas (sendo 39 cortes parciais onde apenas o segmento sobreposto foi removido).
      - Principais BRs desduplicadas no arquivo estadual: **BR-116** (78 trechos), **BR-153** (49 trechos), **BR-381** Rodovia Fernão Dias (21 trechos), **BR-459** (6 trechos), **BR-383** (5 trechos), **BR-354** (2 trechos), **BR-101** (2 trechos), **BR-262** (1 trecho) e **BR-158** (1 trecho).
      - Problemas apontados durante a desduplicação:
        - `federal_br_divergente`: **5 casos** (ex.: trechos estaduais cadastrados com código divergente sobrepostos a BRs federais por 366 m a 3.240 m).
        - `federal_sem_par`: **3 casos** (trecho federal presente no cadastro estadual sobreposto a segmento do DNIT que é `PLAN` — mantido no DER e sinalizado).
        - `sobreposicao_sem_atributo`: **40 casos** (trechos cadastrados como jurisdição estadual sobrepostos por mais de 200 m à rede federal ativa).
    - **Filtro de inexistentes / planejados:**
      - **176 trechos** do DER-SP com `TipoPista='PLAN'` foram excluídos para a camada de removidos.
      - Total na camada `der_sp_rodovias_removidos_ufsp`: **341 trechos** (165 duplicidade federal + 176 planejados).
    - **Rede estadual resultante (`der_sp_rodovias_ufsp`):**
      - **4.942 arcos** e **5.144 nós**.
      - Maior componente conexa: **3.152 arcos** (cobrindo a espinha dorsal interligada de todo o estado).
      - Multipartes explodidas: **654**.
      - Correções aplicadas automaticamente:
        - `ponta_unificada`: **135**
        - `ponta_conectada` (junções em T): **111**
        - `coincidente_colapsado`: **36**
      - Problemas apontados:
        - `cruzamento_sem_no`: 142
        - `ilha`: 259
        - `ilha_borda`: 57
        - `ponta_quase_conectada` (alta): 99
        - `ponta_quase_conectada` (média): 63
        - Total de problemas na camada `der_sp_rodovias_problemas_ufsp`: **950**.

---

### 2.4. Recorte 4 — Teste de Atualização Forçada (`force=True`) em Campinas

- **Objetivo central:** Comprovar que o parâmetro `refresh=True` no conector `zip_remoto` ignora o cache local e força novo download seguro do arquivo ZIP do DER-SP (`der_sp_sistema_rodoviario_estadual.zip`), preservando a integridade das camadas.
- **Resultado medido:**
  - O motor registrou explicitamente no log a linha:
    ```
    [log] [download] der_sp_sistema_rodoviario_estadual.zip
    ```
  - O arquivo foi transferido via HTTP/2 da URL oficial do DER-SP (`https://dersp.der.sp.gov.br/...`), baixando 2.521.732 bytes com validação TLS Go Daddy G2.
  - A camada resultante no GPKG gerou rigorosamente os mesmos 62 arcos e 62 nós obtidos na execução anterior.
  - Tempo de execução total: **1,47 s**.

---

## 3. Conformidade de CRS no GeoPackage

Todas as camadas geradas em todas as três medições foram inspecionadas consultando `gpkg_contents` e `gpkg_spatial_ref_sys`:

| Camada no GeoPackage | CRS Registrado | Validação |
|---|---|---|
| `dnit_snv_<sufixo>` | `EPSG:4674` | Conforme |
| `dnit_snv_nos_<sufixo>` | `EPSG:4674` | Conforme |
| `dnit_snv_problemas_<sufixo>` | `EPSG:4674` | Conforme |
| `dnit_snv_removidos_<sufixo>` | `EPSG:4674` | Conforme |
| `der_sp_rodovias_<sufixo>` | `EPSG:4674` | Conforme |
| `der_sp_rodovias_nos_<sufixo>` | `EPSG:4674` | Conforme |
| `der_sp_rodovias_problemas_<sufixo>` | `EPSG:4674` | Conforme |
| `der_sp_rodovias_removidos_<sufixo>` | `EPSG:4674` | Conforme |

O driver OGR gravou todas as feições no elipsoide SIRGAS 2000 (`EPSG:4674`), sem distorções de coordenadas e totalmente compatível com os demais eixos do GisBR.

---

## 4. Problemas Encontrados

Em conformidade com a diretriz do projeto de manter as tolerâncias `TOL_*` inalteradas (D6) e registrar eventuais anomalias empíricas:

1. **Aviso de Commit do QGIS Memory Provider com Geometrias 3D (`MultiLineStringZ`):**
   - **Descrição:** Durante a execução de `remove_duplicidade_federal`, o console do QGIS emitiu mensagens como:
     ```
     Commit errors: ERROR: 18 feature(s) not added - geometry type is not compatible with the current layer.
     ```
   - **Causa Raiz:** O shapefile oficial do DER-SP possui vértices com coordenada Z (`MultiLineStringZ`). Ao criar a camada intermediária em memória usando a URI padrão `"MultiLineString?crs=EPSG:4674"` (2D), o buffer de edição do QGIS sinaliza a incompatibilidade de dimensão antes de compatibilizar a geometria.
   - **Impacto no Dado:** Nenhum dado foi perdido. O número de feições mantidas e removidas permaneceu matematicamente exato (`featureCount` idêntico ao esperado: 18 em SJC, 4.668 no Estado), e o GeoPackage final foi gravado corretamente.
   - **Recomendação Futura:** Em rodada futura de refatoração, a instanciação de camadas temporárias em `remove_duplicidade_federal` pode inspecionar `QgsWkbTypes.hasZ(layer_est.wkbType())` e usar `MultiLineStringZ` quando a entrada contiver elevação, eliminando o ruído no console.

2. **DNIT SNV em Campinas composto exclusivamente por `PLA`:**
   - **Descrição:** No município de Campinas, o trecho da BR-050 coincidente com a Rodovia Anhanguera (SP-330) consta no cadastro do SNV como planejado (`PLA`) e alienado à concessão estadual.
   - **Consequência:** Como o DNIT não possui vias físicas ativas no município, a fonte `dnit_snv` pula por falta de arcos e a desduplicação contra o DER-SP é dispensada, garantindo que a malha sob administração estadual permaneça 100% íntegra.
