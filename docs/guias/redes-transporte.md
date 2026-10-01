# Redes rodoviárias e ferroviárias

Seis fontes do eixo **1. Transportes** do painel de diagnóstico não saem
mais como linhas soltas: saem como **rede roteável**, com links, nós e uma
camada de problemas. Mesmo GeoPackage, mesmo fluxo do [guia do
painel](diagnostico.md): marque as fontes, escolha o município e clique em
**Carregar selecionadas**.

| `id` | Nome no painel | Tipo |
|---|---|---|
| `dnit_snv` | DNIT — SNV (rodovias federais) | rodoviária |
| `der_mg_rodovias` | DER-MG — Rodovias estaduais | rodoviária |
| `pr_rodovias_der` | DER-PR — Rodovias estaduais (IAT GeoPR) | rodoviária |
| `go_malha_viaria` | Siga-GO — Malha viária (2024) | rodoviária |
| `minfra_ferrovias` | MInfra — Ferrovias | ferroviária |
| `ibge_bc250_ferrovias` | IBGE — BC250 Trecho ferroviario | ferroviária |

A `ibge_bc250_rodovias` **não** vira rede, porque mistura todas as
jurisdições; ela sai como antes. As demais fontes do painel também ficam como
antes.

A diferença para a [rede viária do OSM](vias.md) é a topologia. No OSM, o
`node_id` compartilhado já é a topologia (ver [por que o way é quebrado em
arcos](vias.md)). Nenhuma destas
bases tem id de nó: a conexão só existe pela coincidência de coordenadas.
Por isso a topologia é **reconstruída**.

## As quatro camadas

O motor grava até quatro tabelas por fonte no GeoPackage (EPSG:4674).
`<sufixo>` é o código do recorte, ex.: `3118601`.

### `<id>_<sufixo>` — links (LineString)

Mesmo nome de antes, então o skip-exists e os GeoPackages antigos continuam
valendo.

| Coluna | Conteúdo |
|---|---|
| atributos originais | todos os campos da fonte |
| `arc_id` | identificador do arco |
| `from_node`, `to_node` | nó inicial e final |
| `comprimento_m` | comprimento em metros (haversine) |
| `componente`, `componente_tam` | componente conexa do arco e seu tamanho, em arcos |
| `coincidentes` | os `fid` dos arcos fundidos neste, separados por `;`; vazio se nenhum |

### `<id>_nos_<sufixo>` — nós (Point)

Mesmo esquema do `osm_nodes`.

| Coluna | Conteúdo |
|---|---|
| `node_id` | identificador do nó |
| `x`, `y` | coordenadas |
| `grau` | número de arcos incidentes |
| `componente` | componente conexa do nó |

### `<id>_problemas_<sufixo>` — problemas (Point)

Junta os problemas apontados **e** as correções aplicadas (estas com
`severidade=corrigido`). Só é gravada se tiver alguma linha.

| Coluna | Conteúdo |
|---|---|
| `tipo` | tipo do problema ou da correção |
| `severidade` | `alta`, `media`, `baixa` ou `corrigido` |
| `detalhe` | texto livre com as medidas |
| `node_id`, `arc_id` | referência ao nó/arco, quando aplicável |
| `rede` | `rodoviaria` ou `ferroviaria` |

### `<id>_removidos_<sufixo>` — removidos (LineString)

Atributos originais mais `motivo` (`planejado` ou `duplicado_federal`). Só
existe se algo foi removido.

No projeto os nomes aparecem como "<nome da fonte> - <recorte> (links)",
"(nos)", "(problemas)" e "(removidos)". O log traz uma linha "Relatório de
rede: ..." com as contagens por fonte.

## O que é corrigido automaticamente

Cada correção vira um ponto na camada de problemas, com `severidade=corrigido`.
Multipartes são explodidas em linhas que herdam os atributos.

| `tipo` | O que fez |
|---|---|
| `geometria_degenerada` | parte sem 2 pontos distintos, ou de comprimento zero, foi descartada (vértices repetidos seguidos são limpos sem contar) |
| `ponta_unificada` | pontas a até 1 m (`TOL_NO_M`) viraram o mesmo nó, quando não eram idênticas |
| `ponta_conectada` | junção em T: ponta a até 10 m (`TOL_SNAP_M`) do meio de outra linha; a linha alvo é quebrada no pé da perpendicular e a ponta liga ali |
| `coincidente_colapsado` | arcos com o mesmo par de nós e o mesmo comprimento (tolerância de 1 m ou 1 %) viram um só; os `fid` vão para `coincidentes` |

O `coincidente_colapsado` resolve a duplicidade interna do DNIT: BRs
coincidentes vêm com a geometria repetida, uma vez por BR. Em Contagem,
040×135 por 23,5 km, 040×356 por 18,7 km e 262×381 por 13,3 km.

## O que só é apontado

Estes casos ficam na camada de problemas e nada é alterado. Seguem os mesmos
tipos e regras do [guia do OSM](vias.md#tabela-dos-tipos-de-problema).

| `tipo` | Severidade | O que significa |
|---|---|---|
| `cruzamento_sem_no` | média | duas linhas se cruzam em X sem vértice comum. Não é quebrado, porque pode ser viaduto e a base não diz |
| `ponta_quase_conectada` | alta se ≤ 3 m; média acima | ponta a até 10 m de um arco que não a toca e que a correção em T não ligou |
| `ilha` | alta | componente desconectada da maior |
| `ilha_borda` | baixa | o mesmo, mas a componente toca fora do recorte |

`ponta_solta` não é listado (beco sem saída ou fim de trecho, como no OSM).
Não há `mao_unica_*`: as bases não trazem sentido de tráfego, então a rede é
bidirecional. O sentido das pistas D/E do DER-MG ficou fora, porque a base
não garante o sentido do traçado.

## O que não existe é removido

Arco que não existe numa rede de roteamento dá rota falsa. Cada fonte tem um
filtro de existência por atributo próprio, com comparação exata do valor:

| Fonte | Campo | Sai |
|---|---|---|
| `dnit_snv` | `ds_superfi` | `PLA` |
| `der_mg_rodovias` | `superficie` | `PLA` |
| `pr_rodovias_der` | `situacao` | `PLA` |
| `go_malha_viaria` | `situacao` | `PLA` |
| `minfra_ferrovias` | `tip_situac` | `Planejada`, `Estudo`, `Em Obra` |
| `ibge_bc250_ferrovias` | `situacaofisica` | `Em construção`, `Destruída` |

O que sai vai para a camada de removidos com `motivo=planejado`. Ficam de
propósito:

- "Desativada" (MInfra) e "Abandonada" (BC250), que existem fisicamente; o
  atributo vai junto para quem quiser filtrar.
- Obras de pavimentação e duplicação (`EOP`/`EOD`): a estrada já existe.

Números medidos: em MG inteiro, 414 de 945 trechos do DNIT são `PLA`; no
bbox de Contagem/BH, 18 de 30. No MInfra nacional são 2.489 trechos, dos
quais 479 Planejada, 220 Estudo e 105 Em Obra. Na BC250 ferrovias, 500
trechos, 7 Em construção e 3 Destruída.

Se depois do filtro não sobrar nada, a fonte aparece como pulada com "todos
os trechos eram planejados/inexistentes".

## Duplicidade federal × estadual

Os DERs (MG, PR) e o Siga-GO também trazem as rodovias federais
(`jurisdicao=Federal`; no bbox de Contagem, 22 dos 44 trechos do DER-MG).
Sem tratamento o mapa fica com a BR em dobro.

**É preciso marcar o DNIT junto** com o DER, ou já tê-lo no GeoPackage. A
referência é a camada `dnit_snv_<sufixo>` já gravada. O DNIT vem antes dos
DERs no catálogo, então marcar os dois na mesma carga basta. Sem essa camada
nada é removido e o log avisa: "camada federal dnit_snv_<sufixo> não
encontrada no GeoPackage; duplicidade ignorada". O filtro de `PLA` do DNIT é
reaplicado sobre essa camada, então um GeoPackage antigo com `PLA` não serve
de prova.

Para cada trecho estadual mede-se quanto dele cai dentro de um buffer de
**50 m** (`TOL_DUP_M`) em torno dos trechos federais mantidos. O trecho é
removido quando as três condições valem:

1. a jurisdição é Federal;
2. há 100 m ou mais sobrepostos;
3. o número da BR bate.

O número da BR vem do campo `codigo_rod` no DER-MG e `rod_num` no DER-PR,
completado com zeros à esquerda até 3 dígitos e comparado com `vl_br` e com as BRs coincidentes
`ds_coinc` do DNIT; assim "040" casa com um trecho 040×135, e "135" também.
O Siga-GO não tem número de BR confiável: lá decidem só a jurisdição e a
sobreposição.

Sai só a parte sobreposta. Se o que sobra tem menos de 50 m, ou a
sobreposição cobre 95 % ou mais do trecho, sai o trecho inteiro. O que sai
vai para a camada de removidos com `motivo=duplicado_federal`. Toque só em
entroncamento (menos de 100 m) não remove nada.

### O que cada problema quer dizer

Todos ficam na camada de problemas da fonte estadual; nada é removido.

| `tipo` | Severidade | O que significa |
|---|---|---|
| `federal_sem_par` | média | trecho Federal no DER sobre um trecho do DNIT que é planejado (`PLA`) |
| `federal_br_divergente` | média | trecho Federal sobreposto a um federal mantido, mas com número de BR diferente; pode ser coincidência de traçado ou erro de cadastro, confira |
| `sobreposicao_sem_atributo` | média | trecho de jurisdição não federal sobreposto por mais de 200 m à rede federal; provável federal cadastrado como estadual (ou o inverso), fica para conferência |

O `federal_sem_par` é o caso do federal "planejado" sobre estadual
existente. Em Contagem, 13 dos 18 `PLA` do DNIT têm `est_coinc=Alienado` e
`sup_est_co=DUP`: a BR é "planejada" no SNV, mas a estrada existe sob
jurisdição estadual. O DNIT tira o `PLA` e o DER fica com o trecho, então a
estrada não some do mapa (ex.: 262BMG0550/0570/0610, sobreposição 0,00 com o
DNIT mantido). Por isso a duplicidade só remove contra federal **mantido**.

Medido no bbox de Contagem, a sobreposição do DER-MG com o DNIT mantido é
1,00 em 040BMG0360, 040BMG0400 e 262BMG0640/0645, e vai de 0,72 a 1,00 em
381BMG9060 (que casa com 381CMG3015: mesma BR 381, código diferente). As
estaduais (808, 806, 010, 040EMG…) dão no máximo 0,02, só nos entroncamentos.

## GeoPackage antigo

Um GeoPackage baixado antes desta versão tem a camada `<id>_<sufixo>` com o
mesmo nome, então o skip-exists pula a fonte e a rede não é montada. Para
refazer, marque **"Atualizar bases já baixadas"** no painel (ver [guia do
painel](diagnostico.md)) e carregue de novo, marcando o DNIT junto com o DER
para a duplicidade valer.

## Limites conhecidos

- As tolerâncias (1 m, 10 m, 50 m) foram calibradas no recorte de
  Contagem/RMBH; outra região pode pedir outro número.
- O cruzamento em X nunca é quebrado: a base não distingue viaduto de
  interseção.
- Não há rede unificada (federal + estadual + OSM num só grafo); cada fonte é
  uma rede.
- Não há algoritmo de Processing próprio para essas redes; elas saem pelo
  painel.
