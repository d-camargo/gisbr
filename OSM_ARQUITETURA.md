# OSM Municipal — Arquitetura Atual (2026-09-20)

**Status:** implementado e integrado ao diagnóstico (fonte `osm_vias`, eixo
Transportes) e exposto como algoritmo do Processing (`gisbr:osm_network`,
grupo Diagnóstico). A topologia foi reescrita nos commits `fd0fc1b` e
`81741a1` (2026-09-19): o pipeline deixou de ser "1 way = 1 link" e passou a
ter topologia real por `node_id`, com verificação de conectividade separada
por rede (veicular/pedestre). O plano `osm_network` (mesma data) separou
"montar camadas" de "gravar no GeoPackage" e acrescentou os atributos de
custo (`maxspeed`/`velocidade_kmh`/`comprimento_m`), progresso visível e o
algoritmo `gisbr:osm_network`. O plano `osm_qgstask` (2026-09-20) resolveu a
pendência de `QgsTask` **para o painel**: a fonte `osm_vias` agora baixa e
calcula a rede em segundo plano, sem travar a interface — ver §4. O plano
`so_veicular` (2026-09-20, mesmo dia, versão 0.12.0) voltou atrás na decisão
de rodar as duas redes sempre: passou a rodar **uma rede por execução**
(veicular por padrão), tirou `ponta_solta` da listagem por padrão e agrupou
`mao_unica_sem_saida`/`mao_unica_borda` por armadilha — ver §3. O guia do
usuário é [`docs/guias/vias.md`](docs/guias/vias.md);
`docs/osm-municipal-pattern.md` registra o desenho original (2026-07-03),
hoje histórico.

---

## 1. Fluxo

```
Overpass (JSON)
   │
   ▼
constroi_arcos()          ── quebra cada way em arcos pela topologia real
   │  (osm_topologia.py, stdlib pura; guarda maxspeed cru e expõe
   │   velocidade_kmh(tags) — tabela copiada verbatim do logis)
   ▼
diagnostica(rede=REDE)   ── grau, componentes, SCC, achados — UMA rede por
   │  (osm_topologia.py)      execução (plano `so_veicular`; REDE="veicular"
   │                          por padrão — pedestre só via parâmetro REDE)
   ▼
camadas (osm_links_raw → osm_links → osm_nodes)   ── borda QGIS, com
   │  maxspeed/velocidade_kmh/comprimento_m por arco (osm_pipeline.py)
   ▼
verificação geométrica (ponta_quase_conectada, cruzamento_sem_no)  ── só na
   │  rede executada (metade do custo de antes, que rodava as duas sempre);
   │  ponta_solta fica de fora por padrão (INCLUIR_PONTAS_SOLTAS), contada
   │  à parte; mao_unica_sem_saida/borda saem agrupadas por armadilha (SCC),
   │  não por nó (osm_pipeline.py, usa QgsSpatialIndex/QgsDistanceArea;
   │  reporta progresso e verifica isCanceled() a cada ~200 itens — §4)
   ▼
osm_problemas  ── build_osm_network_layers() para AQUI (tudo em memória)
   │
   ▼
GeoPackage (osm_links_<code>, osm_nodes_<code>, osm_problemas_<code>)
   ── só na casca build_osm_municipal_network()
```

`build_osm_network_layers()` (`osm_pipeline.py`) é o núcleo único: monta as
três camadas em memória (com progresso/cancelamento, §4) e NÃO grava
GeoPackage. Duas portas chamam esse mesmo núcleo — ver §4.

---

## 2. Módulos

### `gisbr/core/osm_topologia.py` — stdlib pura, sem QGIS

Testável sem QGIS instalado (mesma disciplina de `poi_parser.py`).

| Função | O que faz |
|---|---|
| `classifica_modos(tags)` | classifica um `way` OSM em `{"veicular": bool, "pedestre": bool}` a partir de `highway`/`area`/`access`/`motor_vehicle`/`vehicle`/`foot` |
| `constroi_arcos(ways, nodes_dict)` | quebra cada `way` em arcos nos nós compartilhados (`node_id` que aparece em ≥ 2 ways, ou pontas); devolve `(arcos, n_orfaos, descartados)`. Cada arco guarda `maxspeed` cru |
| `velocidade_kmh(tags)` | velocidade em km/h: `maxspeed` (convertendo mph), ou, sem um valor utilizável, a tabela `_DEFAULT_SPEEDS` por `highway` (default 40,0) — copiada **verbatim** de `~/projects/logis/logis/core/network/osm_pipeline.py` para os dois plugins baterem o mesmo número |
| `sentido(arco)` | `"ambos"` / `"direto"` / `"inverso"` a partir de `oneway`/`junction`/`highway` |
| `grau(arcos)` | grau não dirigido por `node_id` (laço soma 2) |
| `componentes(arcos)` | componentes conexas não dirigidas (union-find), renumeradas por tamanho (0 = maior) |
| `componentes_fortes(arcos)` | SCC por Tarjan **iterativo** (sem recursão — redes municipais estouram o limite do Python), sobre o grafo dirigido por `sentido(arco)` |
| `diagnostica(arcos, rede)` | consolida grau/componentes/SCC de UMA rede (`"veicular"` ou `"pedestre"`) em `pontas_soltas`, `mao_unica_sem_saida`, `ilhas` |

### `gisbr/core/osm_pipeline.py` — borda QGIS

Converte o resultado de `osm_topologia.py` em camadas (`QgsVectorLayer`) e
roda a verificação geométrica que depende de `QgsGeometry`/`QgsSpatialIndex`.
O plano `osm_qgstask` (2026-09-20) partiu o núcleo em três, para permitir
rodar o meio (Overpass + topologia + verificação) fora da thread principal
via `QgsTask` (`core/osm_task.py`, §4) — a regra: **a tarefa calcula dados
puros, a thread principal monta as camadas.**

| Função | O que faz |
|---|---|
| `resolve_municipio(code_muni, nome_muni)` | **thread principal.** Resolve o polígono do município (`processing.run("gisbr:read_municipality")`) e a geometria unida; devolve `(municipio_layer, bbox, mun_geom)` — `mun_geom` pode vir `None` se a geometria for inválida (quem decide o que fazer com isso é o chamador) |
| `compute_osm_network(code_muni, nome_muni, bbox, mun_geom, cache_dir, force, feedback, rede, incluir_pontas_soltas)` | **dados puros, seguro em `QgsTask`.** Recebe `bbox`/`mun_geom` já resolvidos; consulta/usa cache do Overpass, chama `constroi_arcos`/`diagnostica` **de UMA rede** (`rede`, plano `so_veicular`; default `"veicular"`, `ValueError` fora de `{"veicular","pedestre"}`), filtra os arcos pelo polígono (`_filtra_arcos`, lista) e roda a verificação geométrica (`incluir_pontas_soltas`, default `False`, repassado a `_monta_problemas`); devolve um dict sem nenhuma `QgsVectorLayer` (`arcos_todos`, `arcos`, `diag`, `nodes_dict`, `problemas`, `metadata` — `metadata["rede"]` registra qual rodou) |
| `montar_camadas(dados)` | **thread principal.** Materializa as quatro `QgsVectorLayer` (`osm_links_raw`/`osm_links`/`osm_nodes`/`osm_problemas`) a partir do dict de `compute_osm_network`; lê `rede` de `dados["metadata"]` (default `"veicular"`) |
| `build_osm_network_layers(code_muni, nome_muni, cache_dir, force, feedback, rede, incluir_pontas_soltas)` | **composição síncrona** de `resolve_municipio` + `compute_osm_network` + `montar_camadas`, na thread principal — mesma assinatura/retorno de sempre, com `rede`/`incluir_pontas_soltas` (plano `so_veicular`) só repassados adiante; é o que o algoritmo do Processing (`FlagNoThreading`, §4) e `build_osm_municipal_network` continuam chamando |
| `build_osm_municipal_network(code_muni, nome_muni, gpkg_path, force, feedback, rede)` | **casca** sobre `build_osm_network_layers`: grava as três camadas no GPKG, acrescentando `gpkg_ok` ao metadata |
| `osm_vias_ja_existe(existentes, code_muni)` | `True` se `osm_links_<code>`/`osm_nodes_<code>` já estão no conjunto de `diagnostico._layers_existentes(gpkg_path)` — extraída para o motor (`carregar_fontes`) e o painel (`OsmNetworkTask`) não duplicarem a regra de "já existe no GeoPackage" |
| `_parse_osm_ways(payload)`, `_build_nodes_dict(payload)` | extraem `ways`/nós do JSON do Overpass |
| `_cria_links_raw(arcos, diag, rede)` | camada LineString de uma LISTA de arcos, com `componente`/`componente_tam` **genéricos** (da rede executada), `maxspeed`, `velocidade_kmh` e `comprimento_m` já anotados — usada tanto para `osm_links_raw` (todos os arcos) quanto para `osm_links` (arcos mantidos) |
| `_filtra_arcos(arcos, engine)` | recorte municipal sobre uma LISTA de arcos (dados puros, roda dentro de `compute_osm_network`) — mantém o **arco inteiro** que intersecta o polígono (ver Decisões) |
| `_cria_nodes_layer(arcos, diag, nodes_dict)` | um ponto por `node_id` referenciado como `from`/`to` da LISTA de arcos mantidos, com `grau`/`componente` genéricos (da rede executada) |
| `ponta_quase_conectada(arcos, diag, nodes_dict, feedback, faixa)` | nós de grau 1 a ≤ `TOL_PONTA_M` (10 m) de um arco não incidente, via `QgsSpatialIndex` + `nearestPoint` + `QgsDistanceArea`; reporta progresso/checa cancelamento a cada ~200 nós |
| `cruzamento_sem_no(arcos, feedback, faixa)` | pares de arcos cujas geometrias se cruzam num ponto que não é nó compartilhado, ignorando `bridge`/`tunnel` ativo ou `layer` diferente; reporta progresso/checa cancelamento a cada ~200 arcos |
| `_monta_problemas(arcos_rede, diag, nodes_dict, engine, rede, incluir_pontas_soltas, feedback, faixa)` | monta os registros de `osm_problemas` de uma rede, só com o ponto dentro do polígono municipal; divide `faixa` entre os dois laços acima. Plano `so_veicular`: `ponta_solta` só sai se `incluir_pontas_soltas=True` (senão só conta, no 2º item da tupla devolvida); `mao_unica_sem_saida`/`mao_unica_borda` saem agrupados por SCC, um ponto por grupo. Devolve `(problemas, ponta_solta_nao_listadas)` |
| `_cria_problemas_layer(problemas)` | materializa `osm_problemas` (Point) |

### `gisbr/core/osm_task.py` — `OsmNetworkTask` (QgsTask)

`OsmNetworkTask` roda `compute_osm_network` fora da thread principal — ver
§4. `_TaskFeedback` (mesmo arquivo) adapta a task para a interface de
`QgsProcessingFeedback` que `compute_osm_network` espera, sem tocar GUI:
`pushInfo`/`pushWarning` emitem o sinal `mensagem` (Qt, thread-safe) e
`isCanceled()` repassa para `task.isCanceled()`.

### `gisbr/algorithms/diagnostico/osm_network.py` — algoritmo do Processing

`OsmNetwork` (`gisbr:osm_network`) chama `build_osm_network_layers` e copia
as feições de cada camada de memória para os sinks (`LINKS`/`NODES`/
`PROBLEMAS`). Ver §4.

---

## 3. Decisões, com o porquê

- **Topologia por `node_id`, não geométrica.** Um cruzamento geométrico entre
  duas linhas não é necessariamente uma conexão real — um viaduto ou túnel
  cruza outra via no espaço sem se ligar a ela. Ligar arcos só quando
  compartilham `node_id` evita esse erro; a verificação (`cruzamento_sem_no`)
  usa o mesmo critério ao contrário, ignorando pares com `bridge`/`tunnel`
  ativo ou `layer` diferente (presume sobreposição de nível, não falha de
  mapeamento).
- **Arco inteiro no recorte, sem `native:clip`.** `native:clip` cortaria o
  arco na borda do polígono e deixaria `from_node`/`to_node` apontando para
  um nó fora da geometria resultante — quebrando a topologia que acabou de
  ser construída. `_filtra_arcos_por_poligono` mantém o arco inteiro sempre
  que ele intersecta o polígono municipal, mesmo que parte dele fique fora.
- **`nearestPoint` em vez de `closestSegmentWithContext`.** Medido:
  `closestSegmentWithContext` devolvia `(0.0, pt, ...)` — o próprio ponto de
  busca como "ponto mais próximo" — quando o ponto cai dentro do bbox de
  busca do arco mas fora da geometria dele, inflando toda ponta cujo bbox de
  tolerância tocasse outro arco em falso positivo a 0,0 m.
- **`busway` fora da rede veicular.** Faixa exclusiva de ônibus/BRT, não rede
  de carro — contá-la como veicular gerava 33 nós de `mao_unica_sem_saida`
  espúrios em Contagem/RMBH.
- **Separação entre rede veicular e rede a pé.** Misturar os dois modos num
  único grafo produzia ilhas e pontas soltas falsas — uma via de pedestre sem
  ligação veicular não é erro da rede de carros. `diagnostica()` roda por
  rede (`rede="veicular"|"pedestre"`), e `osm_problemas` grava a coluna
  `rede` em cada achado.
- **Uma rede por execução, veicular por padrão (plano `so_veicular`,
  2026-09-20, v0.12.0).** O desenho anterior rodava `diagnostica` e a
  verificação geométrica DUAS vezes por carregamento — veicular e pedestre —
  e gravava campos `_pe` (`componente_pe`, `grau_pe`) nas camadas, mesmo o
  uso declarado do Diego sendo roteirização (só veicular). Medido em
  Contagem: dos ~3,9 mil pontos de `osm_problemas`, 2.593 eram `ponta_solta`
  da rede veicular (beco sem saída, entrada de garagem, acesso de
  condomínio — não é erro) e outros ~736 vinham da rede a pé, que não serve
  para roteirização de veículos. `compute_osm_network`/
  `build_osm_network_layers`/`build_osm_municipal_network` ganharam o
  parâmetro `rede` (default `"veicular"`, `ValueError` fora de
  `{"veicular","pedestre"}`); os campos das camadas viraram genéricos
  (`componente`/`grau`, sem o par `_pe` — a rede a pé volta pelo mesmo campo
  quando `REDE=pedestre`). Ganho colateral: a verificação geométrica (a
  etapa mais cara) roda metade das vezes. A porta para a rede a pé continua
  aberta — algoritmo `gisbr:osm_network`, parâmetro `REDE` — só que fora do
  caminho padrão do painel, que sempre usa veicular.
- **`ponta_solta` fora da listagem por padrão, com a contagem preservada.**
  2.593 dos ~3,9 mil pontos medidos em Contagem eram becos sem saída
  legítimos — não erro, mas ruído que afoga o que pede atenção de verdade.
  `_monta_problemas` ganhou `incluir_pontas_soltas` (default `False`): sem
  ele, `ponta_solta` não entra em `osm_problemas`, mas a contagem nunca é
  descartada muda — sai em `metadata["verificacao"]["ponta_solta_nao_listadas"]`
  e no log. O algoritmo expõe isso como `PONTAS_SOLTAS`; o painel não expõe,
  usa o default.
- **`mao_unica_sem_saida`/`mao_unica_borda` por armadilha, não por nó.** O
  desenho anterior emitia um ponto por nó da SCC presa (399 em Contagem) —
  ruído redundante, já que a armadilha é uma unidade só. Agora sai **um
  ponto por grupo** (SCC de `diag["scc"]`), representado pelo menor
  `node_id` do grupo que esteja dentro do polígono (grupo sem nenhum nó
  dentro não gera ponto), com `detalhe` trazendo o tamanho do grupo
  ("N nós"). A regra de borda (`mao_unica_borda`, severidade baixa, quando
  algum nó do grupo cai fora do polígono) continua valendo, agora aplicada
  ao grupo inteiro.
- **`build_osm_network_layers` é o núcleo; `build_osm_municipal_network` é
  casca.** O motor do diagnóstico (`core/diagnostico.py::carregar_fontes`)
  continua chamando a função Python (a casca), não o algoritmo do Processing
  — as duas portas (§4) compartilham o mesmo núcleo; fazer o motor passar
  por `processing.run()` só acrescentaria indireção e risco.
- **Tabela de velocidades copiada verbatim do logis.** `velocidade_kmh`
  reproduz `_DEFAULT_SPEEDS`/`_parse_speed` de
  `logis/core/network/osm_pipeline.py` byte a byte (mesmos valores por
  `highway`, mesma conversão mph→km/h) para as duas bases produzirem o mesmo
  número quando o logis apagar sua cópia e passar a chamar
  `gisbr:osm_network`.

---

## 4. As portas, o `QgsTask` do painel, progresso e cancelamento

**Três portas sobre o mesmo núcleo, cada uma com o regime de thread que faz
sentido para o seu chamador:**

1. **Painel** (`gui/diagnostico_dock.py`, fonte `osm_vias`) → **plano
   `osm_qgstask` (2026-09-20):** `resolve_municipio` na thread principal +
   `OsmNetworkTask` (QgsTask, `core/osm_task.py`) rodando
   `compute_osm_network` em segundo plano + `montar_camadas`/gravação no
   GPKG/`QgsProject.addMapLayer` de volta na thread principal
   (`_on_osm_concluida`, chamado pelo sinal `concluida` que `finished()`
   emite). É a ÚNICA porta que roda fora da thread principal — ver detalhe
   abaixo.
2. **Motor do diagnóstico** (`core/diagnostico.py::carregar_fontes`, quem
   chama o motor por fora do painel) → `build_osm_municipal_network`
   (casca sobre `build_osm_network_layers`, síncrona) → grava no GeoPackage.
3. **Algoritmo do Processing** (`gisbr:osm_network`,
   `algorithms/diagnostico/osm_network.py`) → `build_osm_network_layers`
   direto (síncrona) → devolve as três camadas em sinks
   (LINKS/NODES/PROBLEMAS), sem gravar GeoPackage. É a porta para outro
   plugin (ex.: o **logis**) chamar `processing.run("gisbr:osm_network",
   {...})` em vez de copiar o pipeline — ver
   [`docs/guias/vias.md`](docs/guias/vias.md#usar-de-outro-plugin-ou-do-processing).

O algoritmo continua declarando `flags()` com `FlagNoThreading`: ele chama
`build_osm_network_layers` direto, que por sua vez chama
`processing.run("gisbr:read_municipality")` e monta `QgsVectorLayer` — nada
disso é seguro fora da thread principal, e o Processing não tem como separar
"resolver município" de "rodar o algoritmo" para essa chamada específica.
**A divisão em `QgsTask` é exclusiva do painel** (porta 1); as demais fontes
do painel (protocolos `wfs`/`arcgis`/`geobr`/`arquivo`/etc.) continuam
síncronas, como sempre.

**A regra que governa o desenho do `QgsTask` (porta 1):** `QgsVectorLayer`
(mesmo memory) e `QgsProject` são objetos de thread principal;
`QgsGeometry`, `QgsSpatialIndex`, `QgsDistanceArea` e
`QgsBlockingNetworkRequest` (usada por baixo do `fetch_overpass_json`) podem
rodar numa tarefa de fundo. Logo: **a tarefa calcula e devolve dados puros
(`compute_osm_network`); a thread principal resolve o município antes
(`resolve_municipio`) e monta as camadas depois (`montar_camadas`)**. O
painel resolve o município ANTES de despachar a task — `OsmNetworkTask`
recebe `bbox`/`mun_geom` já prontos e nunca chama `processing.run` nem toca
`QgsVectorLayer` dentro de `run()`.

**Progresso visível (sintoma histórico: o QGIS travava sem sinal de vida ao
carregar a fonte OSM).** `compute_osm_network`/`build_osm_network_layers`
recebem `feedback` (`QgsProcessingFeedback`, sempre opcional) e reportam via
`setProgressText`/`setProgress` em faixas fixas — resolver município (0–5),
Overpass/cache (5–25), `constroi_arcos`/`diagnostica` da rede escolhida
(25–35), filtro dos arcos pelo polígono (35–55), verificação geométrica
(55–90, dividida entre `ponta_quase_conectada` e `cruzamento_sem_no` — só da
rede escolhida desde o plano `so_veicular`; antes dividida ao meio entre
veicular e pedestre) e montar as camadas (90–100).
Dentro dos dois laços longos da verificação, `feedback.isCanceled()` é
checado a cada ~200 itens; se cancelado, `compute_osm_network` aborta **sem
exceção**, devolvendo `metadata["cancelado"] = True` com `arcos_todos`/
`arcos`/diagnósticos já prontos e `problemas = None` — `montar_camadas`
então monta `osm_links_raw`/`osm_links`/`osm_nodes`, mas não `osm_problemas`.

No caminho síncrono (motor/algoritmo), `_LogFeedback` (painel) ganhou uma
`QProgressBar` (escondida fora da execução) e passou a chamar
`QCoreApplication.processEvents()` em `pushInfo`/`setProgress`/
`setProgressText` — é isso que tira a sensação de travamento sem mudar de
thread, para as fontes que continuam síncronas. No caminho da `QgsTask`
(porta 1), quem faz esse papel é o sinal `progressChanged` nativo do
`QgsTask` (emitido por `self.setProgress`, chamado por `_TaskFeedback` em
`core/osm_task.py`), conectado à mesma barra — a interface não trava porque
o cálculo roda de verdade em outra thread, não porque alguém chama
`processEvents()`.

**Cancelamento:** o botão "Cancelar" do painel chama
`self._feedback_atual.cancel()` (fontes síncronas) e, se houver uma
`OsmNetworkTask` viva, também `self._task_osm.cancel()` — `QgsTask.cancel()`
faz `isCanceled()` responder `True` na próxima checagem, tanto no `run()` da
task quanto (via `_TaskFeedback`) dentro de `compute_osm_network`. Barra e
botão "Cancelar" só somem quando a task efetivamente termina
(`_on_osm_concluida`), não no `finally` do carregamento síncrono — senão a
barra sumiria com o OSM ainda rodando em segundo plano. `carregar_fontes`
(`core/diagnostico.py`, caminho síncrono do motor) mantém o
`elif meta.get("cancelado")` no ramo `osm_vias`: a fonte volta como
**pulada** ("cancelado pelo usuário"), não como falha.

---

## 5. Testes

- `tests/test_osm_topologia.py` — cobre `osm_topologia.py` (inclui
  `velocidade_kmh`). Roda **sem QGIS**:
  `python3 -m pytest tests/test_osm_topologia.py -q`.
- `tests/test_osm_pipeline_verificacao.py` — cobre `ponta_quase_conectada` e
  `cruzamento_sem_no`. Exige QGIS (`QgsGeometry`, `QgsSpatialIndex`,
  `QgsDistanceArea`); pula se a fixture `qgis_app` de `tests/conftest.py`
  vier `None`. Plano `so_veicular`: `_monta_problemas` devolve
  `(problemas, ponta_solta_nao_listadas)` — cobre `ponta_solta` fora por
  padrão (e contada), presente com `incluir_pontas_soltas=True`, ausente/não
  contada na rede pedestre, e `mao_unica_sem_saida` agrupado por SCC (um
  ponto por grupo, `detalhe` com o tamanho, inclusive um grupo de 3 nós).
- `tests/test_osm_network_alg.py` — cobre `resolve_municipio` (os três
  formatos de retorno), `compute_osm_network` (dados puros, sem nenhuma
  `QgsVectorLayer` no dict; a trava de ordem `sem_vias` antes de "município
  sem geometria válida", mesmo com `mun_geom=None`; cancelamento deixa
  `problemas=None`), `montar_camadas` (as quatro camadas com os campos de
  `_LINK_FIELDS`/`_NODE_FIELDS`/`_PROBLEMA_FIELDS`; `arcos_todos` vazio
  devolve tudo `None`), `osm_vias_ja_existe`, `build_osm_network_layers`
  (camadas/campos novos, progresso monotônico, cancelamento no meio do
  laço, `feedback=None` — testes de antes do plano `osm_qgstask`, intactos),
  a casca `build_osm_municipal_network` (regressão: continua gravando GPKG e
  devolvendo `gpkg_ok`), o registro do algoritmo em `ALGORITHMS` e
  `processAlgorithm` fim a fim. Exige QGIS. Plano `so_veicular`: `rede`
  default/`"pedestre"`/inválida (`ValueError`), `metadata["rede"]`
  preenchido, `ponta_solta_nao_listadas` batendo com o nº de nós de grau 1
  dentro do polígono, e `REDE`/`PONTAS_SOLTAS` do algoritmo chegando a
  `build_osm_network_layers` como `rede`/`incluir_pontas_soltas`
  (monkeypatch conferindo os kwargs).
- `tests/test_osm_task.py` — cobre `OsmNetworkTask.run()` chamado direto
  (sem `QgsApplication.taskManager()`), com `compute_osm_network`
  monkeypatchado: caminho feliz (`True`, `self.dados` preenchido), erro
  (`False`, `self.erro` preenchido), sinal `mensagem` emitido, `cancel()`
  antes de `run()` (`False`, compute nunca chamado) e `finished()` emitindo
  `concluida` com os dados ou `None`. Exige QGIS (só por `QgsTask`/sinais).
- `tests/test_diagnostico_dock.py` — cobre a barra/botão do Passo 6b/6c:
  começam escondidos, `_LogFeedback` sem barra segue funcionando como antes,
  `_LogFeedback` com barra atualiza valor/formato, `_on_cancelar` chama
  `feedback.cancel()` (e não quebra sem feedback ativo). Passo 3/4 do plano
  `osm_qgstask`: `_on_cancelar` também chama `cancel()` da `OsmNetworkTask`
  viva; `_on_osm_concluida(None)` loga cancelamento ou erro sem quebrar
  (barra/botão somem); `_on_osm_concluida(dados)` com dados sintéticos de
  `compute_osm_network` grava no GPKG e adiciona `osm_links`/`osm_nodes` ao
  `QgsProject` (removidas ao final do teste).
- `tests/test_diagnostico.py::test_carregar_fontes_osm_vias_cancelado_vira_pulou`
  — cobre o `elif meta.get("cancelado")` do Passo 6c em `carregar_fontes`
  (caminho síncrono do motor, que não usa `QgsTask`).

---

## 6. Referências

- Guia do usuário: [`docs/guias/vias.md`](docs/guias/vias.md).
- Desenho original (histórico, não reflete o pipeline atual):
  [`docs/osm-municipal-pattern.md`](docs/osm-municipal-pattern.md).
- `CLAUDE.md`/`GEMINI.md` §10 — armadilhas gerais de PyQGIS que também valem
  aqui (`QgsGeometryEngine`, enums escopados, Overpass).
