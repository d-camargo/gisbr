# OSM Municipal — Arquitetura Atual (2026-09-19)

**Status:** implementado e integrado ao diagnóstico (fonte `osm_vias`, eixo
Transportes). A topologia foi reescrita nos commits `fd0fc1b` e `81741a1`
(2026-09-19): o pipeline deixou de ser "1 way = 1 link" e passou a ter
topologia real por `node_id`, com verificação de conectividade separada por
rede (veicular/pedestre). O guia do usuário é
[`docs/guias/vias.md`](docs/guias/vias.md); `docs/osm-municipal-pattern.md`
registra o desenho original (2026-07-03), hoje histórico.

---

## 1. Fluxo

```
Overpass (JSON)
   │
   ▼
constroi_arcos()          ── quebra cada way em arcos pela topologia real
   │  (osm_topologia.py, stdlib pura)
   ▼
diagnostica(rede="veicular")   ── grau, componentes, SCC, achados — 1x por rede
diagnostica(rede="pedestre")
   │  (osm_topologia.py)
   ▼
camadas (osm_links_raw → osm_links → osm_nodes)   ── borda QGIS
   │  (osm_pipeline.py)
   ▼
verificação geométrica (ponta_quase_conectada, cruzamento_sem_no)  ── por rede
   │  (osm_pipeline.py, usa QgsSpatialIndex/QgsDistanceArea)
   ▼
osm_problemas + GeoPackage (osm_links_<code>, osm_nodes_<code>, osm_problemas_<code>)
```

`build_osm_municipal_network()` (`osm_pipeline.py`) é o orquestrador único,
chamado pelo protocolo `osm` em `core/diagnostico.py::carregar_fontes()`.

---

## 2. Módulos

### `gisbr/core/osm_topologia.py` — stdlib pura, sem QGIS

Testável sem QGIS instalado (mesma disciplina de `poi_parser.py`).

| Função | O que faz |
|---|---|
| `classifica_modos(tags)` | classifica um `way` OSM em `{"veicular": bool, "pedestre": bool}` a partir de `highway`/`area`/`access`/`motor_vehicle`/`vehicle`/`foot` |
| `constroi_arcos(ways, nodes_dict)` | quebra cada `way` em arcos nos nós compartilhados (`node_id` que aparece em ≥ 2 ways, ou pontas); devolve `(arcos, n_orfaos, descartados)` |
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
| `build_osm_municipal_network(code_muni, nome_muni, gpkg_path, force, feedback)` | orquestrador: resolve o município, consulta/usa cache do Overpass, chama `constroi_arcos`/`diagnostica`, monta as três camadas, grava no GeoPackage |
| `_parse_osm_ways(payload)`, `_build_nodes_dict(payload)` | extraem `ways`/nós do JSON do Overpass |
| `_cria_links_raw(arcos, diag_veicular, diag_pedestre)` | camada LineString de TODOS os arcos (antes do recorte), com `componente`/`componente_pe` já anotados |
| `_filtra_arcos_por_poligono(links_raw, engine)` | recorte municipal — mantém o **arco inteiro** que intersecta o polígono (ver Decisões) |
| `_cria_nodes_layer(osm_links, diag_veicular, diag_pedestre, nodes_dict)` | um ponto por `node_id` referenciado como `from`/`to` de arco mantido |
| `ponta_quase_conectada(arcos, diag, nodes_dict)` | nós de grau 1 a ≤ `TOL_PONTA_M` (10 m) de um arco não incidente, via `QgsSpatialIndex` + `nearestPoint` + `QgsDistanceArea` |
| `cruzamento_sem_no(arcos)` | pares de arcos cujas geometrias se cruzam num ponto que não é nó compartilhado, ignorando `bridge`/`tunnel` ativo ou `layer` diferente |
| `_monta_problemas(arcos_rede, diag, nodes_dict, engine, rede)` | monta os registros de `osm_problemas` de uma rede, só com o ponto dentro do polígono municipal |
| `_cria_problemas_layer(problemas)` | materializa `osm_problemas` (Point) |

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

---

## 4. Testes

- `tests/test_osm_topologia.py` — cobre `osm_topologia.py`. Roda **sem
  QGIS**: `python3 -m pytest tests/test_osm_topologia.py -q`.
- `tests/test_osm_pipeline_verificacao.py` — cobre `ponta_quase_conectada` e
  `cruzamento_sem_no`. Exige QGIS (`QgsGeometry`, `QgsSpatialIndex`,
  `QgsDistanceArea`); pula se a fixture `qgis_app` de `tests/conftest.py`
  vier `None`.

---

## 5. Referências

- Guia do usuário: [`docs/guias/vias.md`](docs/guias/vias.md).
- Desenho original (histórico, não reflete o pipeline atual):
  [`docs/osm-municipal-pattern.md`](docs/osm-municipal-pattern.md).
- `CLAUDE.md`/`GEMINI.md` §10 — armadilhas gerais de PyQGIS que também valem
  aqui (`QgsGeometryEngine`, enums escopados, Overpass).
