# Rede viária (OSM)

A fonte **OSM — Vias urbanas (Overpass)** — `id` `osm_vias`, no painel de
diagnóstico, eixo **1. Transportes** — baixa, via API Overpass do
OpenStreetMap, a malha viária do município escolhido e monta a topologia
real da rede: não há nada para instalar, nenhuma dependência externa. Ela é o
gêmeo da fonte de POIs `osm_pois` (eixo 7. Urbano): mesma infraestrutura de
rede, mesmo GeoPackage do diagnóstico, mesmo fluxo do [guia do
painel](diagnostico.md). Marque a fonte, escolha o município e clique em
**Carregar selecionadas**.

A resposta do Overpass fica em cache em `osm_overpass_<código IBGE>.json`, na
mesma pasta do GeoPackage; numa reexecução o plugin reaproveita esse arquivo
em vez de consultar a rede de novo — mesmo mecanismo do `osm_pois` (veja
[Cache e volume](pois.md#cache-e-volume) no guia de POIs).

## Topologia: por que o way é quebrado em arcos

No OSM, uma via é um `way`: uma sequência de nós (`node_id`). É comum um
`way` atravessar vários cruzamentos sem ter sido cortado naquele ponto — o
cruzamento existe porque **outro** `way` compartilha um nó no *meio* dele,
não numa ponta. Se a rede fosse montada ligando só as pontas geométricas de
cada `way` ("1 way = 1 link"), todo cruzamento no meio de um way ficaria sem
ligação — o grafo perderia esquinas, trevos, entroncamentos reais.

Por isso o motor quebra cada `way` em **arcos**: todo nó que aparece em pelo
menos dois `ways` diferentes (ou que está numa ponta do próprio `way`) vira
um ponto de quebra. Dois arcos ficam conectados **se e somente se
compartilham um `node_id`** — nunca por proximidade geométrica.

É essa mesma regra que explica por que um **viaduto** ou um **túnel** que
cruza outra via no espaço **não vira conexão**: a topologia é por
`node_id`, e uma via elevada não compartilha nó com a via por baixo dela. A
verificação de conectividade usa esse critério para não confundir as duas
coisas: um cruzamento geométrico entre arcos com `bridge`/`tunnel` ativo em
algum dos dois, ou com `layer` diferente, é tratado como sobreposição de
nível — não como falha de mapeamento (veja `cruzamento_sem_no` adiante).

## As três camadas

O motor grava três tabelas no GeoPackage, com sufixo `_<código IBGE>`
(ex.: `osm_links_3118601`):

### `osm_links_<código IBGE>` — os arcos (LineString)

| Coluna | Conteúdo |
|---|---|
| `arc_id` | identificador sequencial do arco |
| `way_id` | id do `way` original no OSM |
| `seq` | ordem do arco dentro do `way` (0, 1, 2…) |
| `from_node`, `to_node` | `node_id` inicial e final do arco |
| `highway` | valor da tag `highway` |
| `name` | nome da via (vazio quando o OSM não tem `name`) |
| `oneway` | valor bruto da tag `oneway` |
| `bridge`, `tunnel`, `layer` | valores brutos das tags de mesmo nome |
| `veicular`, `pedestre` | 1/0 — o arco pertence à rede veicular / à rede a pé |
| `componente`, `componente_tam` | id e tamanho (em arcos) da componente conexa do arco na rede **veicular**; `-1`/vazio se o arco não é veicular |
| `componente_pe` | id da componente conexa na rede **a pé**; `-1` se o arco não é pedestre |

### `osm_nodes_<código IBGE>` — os nós (Point)

Um ponto por `node_id` referenciado como `from_node`/`to_node` de algum arco
mantido (não é todo nó do OSM, só os que sobraram como extremidade de arco).

| Coluna | Conteúdo |
|---|---|
| `node_id` | id do nó no OSM |
| `x`, `y` | longitude, latitude |
| `grau` | grau não dirigido do nó na rede veicular (nº de arcos incidentes; laço conta 2) |
| `grau_pe` | grau na rede a pé |
| `componente` | id da componente conexa do nó na rede veicular (`-1` se não participa) |
| `componente_pe` | idem, rede a pé |

### `osm_problemas_<código IBGE>` — achados da verificação (Point)

| Coluna | Conteúdo |
|---|---|
| `tipo` | um dos sete tipos da tabela abaixo |
| `severidade` | `alta`, `media` ou `baixa` |
| `detalhe` | texto livre (distância medida, tamanho da componente, arcos envolvidos) |
| `node_id`, `arc_id` | referência ao nó/arco do problema, quando aplicável (vazio quando não) |
| `rede` | `veicular` ou `pedestre` — a verificação roda uma vez por rede |

## Rede veicular × rede a pé

A verificação roda **duas vezes**, uma para cada rede, porque misturar tudo
num único grafo gera ilhas e pontas soltas falsas: uma pista de pedestre que
não tem ligação veicular não é um "erro" da rede de carros, é normal. Todo
`way` é classificado em três grupos pelo valor de `highway`:

| Grupo | `highway` |
|---|---|
| **Descartado** (nunca vira arco, em rede alguma) | `proposed`, `construction`, `abandoned`, `disused`, `dismantled`, `razed`, `planned`, `raceway`, `platform`, `rest_area`, `services`, `bus_stop`, `elevator`, `emergency_bay`, `escape`, `via_ferrata`, `corridor`, `bus_guideway`, `busway` — mais qualquer `way` com `area=yes`, e qualquer `highway` fora dos dois grupos abaixo |
| **Veicular** | `motorway`, `motorway_link`, `trunk`, `trunk_link`, `primary`, `primary_link`, `secondary`, `secondary_link`, `tertiary`, `tertiary_link`, `unclassified`, `residential`, `living_street`, `service`, `road`, `track` |
| **Pedestre** | tudo do grupo veicular **exceto** `motorway`/`motorway_link`/`trunk`/`trunk_link` (pedestre não anda em via de alta velocidade), mais `footway`, `pedestrian`, `path`, `steps`, `cycleway`, `bridleway` |

`busway` (faixa exclusiva de ônibus/BRT) fica **fora da rede veicular de
propósito** — carro nenhum passa ali, e contá-lo como veicular gerava mãos
únicas sem saída espúrias (33 nós, medido em Contagem/RMBH).

Tags que mudam a classificação de um `way` já pertencente a um dos grupos
acima:

| Tag | Efeito |
|---|---|
| `access=no` | tira o `way` dos dois modos, salvo override (linha abaixo) |
| `access=private` | **não tira nada** — `service` privado costuma ligar condomínio/pátio à rede, e descartá-lo apagaria uma conexão real |
| `motor_vehicle` (ou `vehicle`, se `motor_vehicle` ausente) | `no` tira do veicular; `yes`/`designated`/`permissive`/`destination` **restaura** o veicular, mas só se o `highway` já era veicular na base (o override não promove um `highway` que não é via de carro) |
| `foot` | mesma regra do item acima, para o modo pedestre |
| `sidewalk` | não altera nada — é atributo de acostamento, não de modo |

A rede a pé **ignora o sentido (`oneway`)** — sempre bidirecional — e por
isso não gera `mao_unica_sem_saida`; também não gera `ponta_solta` (beco sem
saída de calçada é a norma, não um problema a reportar).

## Tabela dos tipos de problema

| `tipo` | Severidade | O que costuma significar |
|---|---|---|
| `ilha` | alta | componente conexa inteira, dentro do recorte, desconectada da maior componente da rede — provável falha de digitalização (via não emenda onde deveria) ou trecho de fato isolado |
| `ilha_borda` | baixa | mesma situação, mas algum nó da componente cai fora do recorte municipal — pode estar conectado por uma via que segue além da divisa; não dá para afirmar que é erro |
| `ponta_quase_conectada` | alta se ≤ 3 m do arco mais próximo; média acima disso (busca até 10 m) | nó de grau 1 perto de um arco que não o toca — sugere ponta sem *snap* na digitalização do OSM; a cauda de 3–10 m costuma ser via paralela que legitimamente não se liga |
| `ponta_solta` | baixa (só na rede veicular) | nó de grau 1 sem nenhum arco próximo dentro da tolerância — beco sem saída real, não é erro |
| `mao_unica_sem_saida` | alta | nó alcançável ignorando o sentido das mãos (componente fraca), mas não alcançável respeitando `oneway` (fora da maior SCC) — sugere sentido único errado ou faltando o trecho de retorno |
| `mao_unica_borda` | baixa | mesmo caso, mas a componente fortemente conexa toca um nó fora do recorte — a "volta" pode estar fora do bbox consultado, não dá para afirmar que é sem saída de fato |
| `cruzamento_sem_no` | média | duas geometrias de arco se cruzam num ponto que não é nó compartilhado por nenhum dos dois — sinaliza cruzamento sem interseção topológica no OSM (viadutos e túneis reais ficam de fora, ver seção de topologia) |

## Como usar o resultado

Filtre `osm_problemas` pelos campos `severidade` e `rede` (expressão do QGIS,
ex.: `"severidade" = 'alta' AND "rede" = 'veicular'`) para priorizar o que
olhar primeiro. `ponta_solta` e os dois tipos `*_borda` são **informativos**,
não erro — não exigem correção, só contexto sobre o limite do recorte ou o
formato normal da malha.

## Limites conhecidos

- **As tolerâncias de distância (10 m de busca, 3 m para severidade alta) foram
  calibradas numa medição só** — Contagem, região metropolitana de Belo
  Horizonte. Nessa medição, separar a rede a pé da veicular e corrigir a
  medida de distância derrubou a rede veicular de 27 para 15 componentes,
  zerou os `cruzamento_sem_no`, e deixou 141 `ponta_quase_conectada` (7
  delas a menos de 3 m). Outro município pode pedir outro número.
- **O recorte municipal mantém o arco inteiro** que intersecta o polígono do
  município — ele **não** usa `native:clip` (que cortaria o arco e deixaria
  `from_node`/`to_node` apontando para um nó fora da geometria recortada). Por
  isso, conectividade que depende de vias fora do recorte aparece como
  `ilha_borda`/`mao_unica_borda`, não como erro.
- **Bicicleta ainda não tem rede própria**: `cycleway` entra na rede a pé
  (junto com calçada, caminho, escada), sem um grafo cicloviário separado.

Como no guia de POIs, os dados são © colaboradores do OpenStreetMap (ODbL).
