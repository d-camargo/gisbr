# OSM Municipal — Arquitetura Atual (2026-09-19)

**Status:** implementado e integrado ao diagnóstico (fonte `osm_vias`, eixo
Transportes) e exposto como algoritmo do Processing (`gisbr:osm_network`,
grupo Diagnóstico). A topologia foi reescrita nos commits `fd0fc1b` e
`81741a1` (2026-09-19): o pipeline deixou de ser "1 way = 1 link" e passou a
ter topologia real por `node_id`, com verificação de conectividade separada
por rede (veicular/pedestre). O plano `osm_network` (mesma data) separou
"montar camadas" de "gravar no GeoPackage" e acrescentou os atributos de
custo (`maxspeed`/`velocidade_kmh`/`comprimento_m`), progresso visível e o
algoritmo `gisbr:osm_network` — ver §4. O guia do usuário é
[`docs/guias/vias.md`](docs/guias/vias.md); `docs/osm-municipal-pattern.md`
registra o desenho original (2026-07-03), hoje histórico.

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
diagnostica(rede="veicular")   ── grau, componentes, SCC, achados — 1x por rede
diagnostica(rede="pedestre")
   │  (osm_topologia.py)
   ▼
camadas (osm_links_raw → osm_links → osm_nodes)   ── borda QGIS, com
   │  maxspeed/velocidade_kmh/comprimento_m por arco (osm_pipeline.py)
   ▼
verificação geométrica (ponta_quase_conectada, cruzamento_sem_no)  ── por rede
   │  (osm_pipeline.py, usa QgsSpatialIndex/QgsDistanceArea; reporta
   │   progresso e verifica isCanceled() a cada ~200 itens — §4)
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

| Função | O que faz |
|---|---|
| `build_osm_network_layers(code_muni, nome_muni, cache_dir, force, feedback)` | **núcleo.** Resolve o município, consulta/usa cache do Overpass, chama `constroi_arcos`/`diagnostica`, monta as três camadas EM MEMÓRIA (sem gravar GPKG); reporta progresso e trata cancelamento (§4) |
| `build_osm_municipal_network(code_muni, nome_muni, gpkg_path, force, feedback)` | **casca** sobre a função acima: chama `build_osm_network_layers` com `cache_dir` = pasta do GPKG e grava as três camadas, acrescentando `gpkg_ok` ao metadata |
| `_parse_osm_ways(payload)`, `_build_nodes_dict(payload)` | extraem `ways`/nós do JSON do Overpass |
| `_cria_links_raw(arcos, diag_veicular, diag_pedestre)` | camada LineString de TODOS os arcos (antes do recorte), com `componente`/`componente_pe`, `maxspeed`, `velocidade_kmh` e `comprimento_m` já anotados |
| `_filtra_arcos_por_poligono(links_raw, engine)` | recorte municipal — mantém o **arco inteiro** que intersecta o polígono (ver Decisões) |
| `_cria_nodes_layer(osm_links, diag_veicular, diag_pedestre, nodes_dict)` | um ponto por `node_id` referenciado como `from`/`to` de arco mantido |
| `ponta_quase_conectada(arcos, diag, nodes_dict, feedback, faixa)` | nós de grau 1 a ≤ `TOL_PONTA_M` (10 m) de um arco não incidente, via `QgsSpatialIndex` + `nearestPoint` + `QgsDistanceArea`; reporta progresso/checa cancelamento a cada ~200 nós |
| `cruzamento_sem_no(arcos, feedback, faixa)` | pares de arcos cujas geometrias se cruzam num ponto que não é nó compartilhado, ignorando `bridge`/`tunnel` ativo ou `layer` diferente; reporta progresso/checa cancelamento a cada ~200 arcos |
| `_monta_problemas(arcos_rede, diag, nodes_dict, engine, rede, feedback, faixa)` | monta os registros de `osm_problemas` de uma rede, só com o ponto dentro do polígono municipal; divide `faixa` entre os dois laços acima |
| `_cria_problemas_layer(problemas)` | materializa `osm_problemas` (Point) |

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
  ligação veicular não é erro da rede de carros. `diagnostica()` roda uma vez
  por rede (`rede="veicular"|"pedestre"`), e `osm_problemas` grava a coluna
  `rede` em cada achado.
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

## 4. As duas portas, progresso e cancelamento

**Duas portas sobre o mesmo núcleo (`build_osm_network_layers`):**

1. **Motor do diagnóstico** (`core/diagnostico.py::carregar_fontes`, protocolo
   `osm`) → `build_osm_municipal_network` (casca) → grava no GeoPackage do
   painel.
2. **Algoritmo do Processing** (`gisbr:osm_network`,
   `algorithms/diagnostico/osm_network.py`) → `build_osm_network_layers`
   direto → devolve as três camadas em sinks (LINKS/NODES/PROBLEMAS), sem
   gravar GeoPackage. É a porta para outro plugin (ex.: o **logis**) chamar
   `processing.run("gisbr:osm_network", {...})` em vez de copiar o pipeline —
   ver [`docs/guias/vias.md`](docs/guias/vias.md#usar-de-outro-plugin-ou-do-processing).

O algoritmo declara `flags()` com `FlagNoThreading`: o núcleo chama
`processing.run("gisbr:read_municipality")` e mexe em objetos do QGIS
(`QgsVectorLayer`, `QgsGeometry`) fora do padrão seguro para rodar numa
thread de fundo — sem a flag, o Processing poderia agendar o algoritmo numa
`QgsTask` e quebrar.

**Progresso visível (sintoma histórico: o QGIS travava sem sinal de vida ao
carregar a fonte OSM).** `build_osm_network_layers` recebe `feedback`
(`QgsProcessingFeedback`, sempre opcional) e reporta via
`setProgressText`/`setProgress` em seis faixas fixas — resolver município
(0–5), Overpass/cache (5–25), `constroi_arcos`/`diagnostica` (25–35), montar
camadas de links/nós (35–55), verificação geométrica (55–90, dividida entre
as redes veicular/pedestre e, dentro de cada uma, entre
`ponta_quase_conectada` e `cruzamento_sem_no`) e montar `osm_problemas`
(90–100). Dentro dos dois laços longos da verificação, `feedback.isCanceled()`
é checado a cada ~200 itens; se cancelado, a função aborta **sem exceção**,
devolvendo `metadata["cancelado"] = True` com as camadas já prontas até ali
(`osm_links`/`osm_nodes`; `osm_problemas` fica `None`).

No painel (`gui/diagnostico_dock.py`), o `_LogFeedback` ganhou uma
`QProgressBar` (escondida fora da execução) e passou a chamar
`QCoreApplication.processEvents()` em `pushInfo`/`setProgress`/
`setProgressText` — é isso que tira a sensação de travamento sem mudar de
thread — mais um botão "Cancelar" ao lado da barra que chama
`feedback.cancel()`. `_on_carregar` desabilita o botão "Load selected",
troca o cursor para `Qt.CursorShape.WaitCursor` (`QApplication.
setOverrideCursor`, restaurado em `finally`) e devolve tudo ao normal ao
final, canceladas ou não. `carregar_fontes` (`core/diagnostico.py`) ganhou um
`elif meta.get("cancelado")` no ramo `osm_vias`: a fonte volta como
**pulada** ("cancelado pelo usuário"), não como falha — único ponto do motor
tocado pelo Passo 6c, como previsto no plano.

**Pendência conhecida — `QgsTask` não entrou nesta rodada.** Mover o
carregamento para uma thread de fundo é a solução completa contra o
travamento da interface, mas o pipeline cria `QgsVectorLayer`, chama
`processing.run("gisbr:read_municipality")` e grava GeoPackage — e camadas só
entram no `QgsProject` pela thread principal. Fica para um trabalho próprio.

---

## 5. Testes

- `tests/test_osm_topologia.py` — cobre `osm_topologia.py` (inclui
  `velocidade_kmh`). Roda **sem QGIS**:
  `python3 -m pytest tests/test_osm_topologia.py -q`.
- `tests/test_osm_pipeline_verificacao.py` — cobre `ponta_quase_conectada` e
  `cruzamento_sem_no`. Exige QGIS (`QgsGeometry`, `QgsSpatialIndex`,
  `QgsDistanceArea`); pula se a fixture `qgis_app` de `tests/conftest.py`
  vier `None`.
- `tests/test_osm_network_alg.py` — cobre `build_osm_network_layers`
  (camadas/campos novos, progresso monotônico, cancelamento no meio do
  laço, `feedback=None`), a casca `build_osm_municipal_network` (regressão:
  continua gravando GPKG e devolvendo `gpkg_ok`), o registro do algoritmo em
  `ALGORITHMS` e `processAlgorithm` fim a fim. Exige QGIS.
- `tests/test_diagnostico_dock.py` — cobre a barra/botão do Passo 6b/6c:
  começam escondidos, `_LogFeedback` sem barra segue funcionando como antes,
  `_LogFeedback` com barra atualiza valor/formato, `_on_cancelar` chama
  `feedback.cancel()` (e não quebra sem feedback ativo).
- `tests/test_diagnostico.py::test_carregar_fontes_osm_vias_cancelado_vira_pulou`
  — cobre o `elif meta.get("cancelado")` do Passo 6c em `carregar_fontes`.

---

## 6. Referências

- Guia do usuário: [`docs/guias/vias.md`](docs/guias/vias.md).
- Desenho original (histórico, não reflete o pipeline atual):
  [`docs/osm-municipal-pattern.md`](docs/osm-municipal-pattern.md).
- `CLAUDE.md`/`GEMINI.md` §10 — armadilhas gerais de PyQGIS que também valem
  aqui (`QgsGeometryEngine`, enums escopados, Overpass).
