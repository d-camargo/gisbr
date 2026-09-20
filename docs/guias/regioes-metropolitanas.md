# Regiões metropolitanas

O painel de diagnóstico pode operar em dois modos de recorte: **Município** e
**Região metropolitana**. No modo RM, o plugin baixa cada fonte filtrada pelo
**conjunto de municípios** da região — não apenas por um — e recorta pelo
polígono unificado, da mesma forma que faz para um município isolado. Marque o
radio **Região metropolitana** na aba *Localização*, escolha a UF e a RM, e
clique em **Carregar selecionadas** — o resto do fluxo é o mesmo do
[guia do painel](diagnostico.md).

## Escolher o recorte

Na aba *Localização* há dois radio buttons: **Município** (padrão) e **Região
metropolitana**. Ao marcar *Região metropolitana*:

- Os campos *Município* e *Código IBGE* ficam desabilitados.
- Um combo **Região metropolitana** aparece, populado pelas RMs da UF
  selecionada.
- Uma lista exibe os **municípios integrantes** da RM escolhida (nome e código
  IBGE de 7 dígitos), com a contagem total no rótulo acima.

O plugin traz no combo apenas as RMs da UF escolhida; troque de UF para ver as
de outro estado.

## O que muda no GeoPackage

### Nome das camadas

No modo Município, o nome da tabela no GeoPackage é `<fonte>_<código IBGE>`
(ex.: `sicar_imoveis_3106200`). No modo RM, o sufixo muda para **`rm<id>`**,
onde `<id>` é o código IBGE da RM (5 dígitos, com zero à esquerda):

| Modo | Tabela no GeoPackage | Exemplo |
|---|---|---|
| Município | `<fonte>_<code_muni>` | `sicar_imoveis_3106200` |
| Região metropolitana | `<fonte>_rm<id>` | `sicar_imoveis_rm04501` |

O nome de exibição no painel de camadas do QGIS segue o mesmo padrão das demais
fontes: "*&lt;nome da fonte&gt; - &lt;rótulo do recorte&gt;*" (ex.: *SICAR —
Imóveis rurais (CAR) - RM de Belo Horizonte*).

### Camada de limite

Na primeira execução, o plugin grava no GeoPackage a camada **`rm_<id>`** (ex.:
`rm_04501`) com o **polígono unificado** dos municípios integrantes — o contorno
da RM. Ela é adicionada ao projeto com o rótulo "RM de …" e serve como
referência visual e como polígono de recorte para as fontes filtradas por
bounding box. Na reexecução, o plugin reaproveita o polígono que já está no
GeoPackage (salvo se *Atualizar bases já baixadas* estiver marcado).

## De onde vem a composição municipal

A lista de municípios de cada RM vem de um **CSV embarcado no plugin**
(`gisbr/core/data/regioes_metropolitanas.csv`), extraído da
[**API de Localidades do IBGE v1**](https://servicodados.ibge.gov.br/api/v1/localidades/regioes-metropolitanas)
pelo script `tools/gera_regioes_metropolitanas.py`. O CSV contém 84 regiões
metropolitanas (e aglomerações urbanas) com a composição municipal completa.

A composição é **atualizada por versão do plugin**: a cada release, o CSV é
regenerado a partir do endpoint do IBGE e embarcado junto. A data de extração
aparece no comentário da primeira linha do arquivo.

!!! note "Sem dependência de rede para a composição"
    O CSV é lido da stdlib (`csv`), sem precisar de rede nem de PyQGIS. A
    composição inteira é carregada em memória na primeira consulta e memoizada
    para o resto da sessão.

## OSM — indisponível no modo RM

As fontes **`osm_vias`** (rede viária) e **`osm_pois`** (pontos de interesse)
são **desabilitadas automaticamente** no modo Região metropolitana: os
checkboxes ficam cinza, desmarcados, e o log avisa:

> *OSM road network and POIs are available for single municipality mode only
> (disabled in RM mode).*

O motivo é técnico: a consulta Overpass para a bounding box de uma RM inteira
(que pode conter dezenas de municípios) geraria volumes massivos de dados,
timeouts na API pública e travamento do QGIS durante o parse.

!!! tip "O que fazer: carregar OSM por município"
    Para ter as vias e os POIs do OSM na região metropolitana, volte ao modo
    **Município** e carregue cada cidade de interesse individualmente, sempre
    apontando para o **mesmo GeoPackage**. As camadas OSM de cada município
    (`osm_links_<code>`, `osm_nodes_<code>`, `osm_pois_<code>`) convivem no
    mesmo arquivo com as camadas da RM (`<fonte>_rm<id>`) — o GeoPackage aceita
    ambos os sufixos.

## RIDEs não estão no catálogo

As **Regiões Integradas de Desenvolvimento Econômico** — RIDE DF e Entorno, RIDE
Petrolina–Juazeiro e RIDE Teresina–Timon — são criadas por lei complementar
**federal** e envolvem municípios de **mais de uma UF**. O endpoint de RMs do
IBGE
(`api/v1/localidades/regioes-metropolitanas`) lista apenas as 84 entidades
instituídas por leis complementares **estaduais** (todas mono-UF), portanto as
RIDEs **não aparecem no combo**.

!!! note "Arquitetura pronta para multi-UF"
    O código já foi desenhado para suportar recortes multi-UF: a classe
    `Recorte` agrupa os códigos por UF, baixa a malha municipal de cada uma,
    mescla os vetores e aplica o filtro consolidado. O que falta é uma fonte
    oficial que publique as RIDEs em formato consumível — quando existir, entram
    no mesmo CSV sem mudança de motor.

## Aviso de truncamento na camada de limite

Ao montar o polígono da RM, o plugin baixa a malha municipal do geobr e extrai
apenas os municípios cujo `code_muni` está na composição. Se o geobr retornar
**menos polígonos** do que a composição espera — o que pode acontecer quando o
IBGE cria municípios novos que a malha ainda não inclui, ou vice-versa —, o log
exibe um aviso:

> *Aviso: camada extraída para RM de Belo Horizonte tem 33 feições, mas o
> recorte tem 34 códigos.*

Isso **não** é um erro do plugin: significa que a malha do geobr está
desatualizada em relação à composição do IBGE. O polígono resultante é gravado
assim mesmo (com os municípios disponíveis) e serve para o recorte — mas pode
faltar um fragmento na borda. Se a diferença for significativa, verifique a
versão da malha (parâmetro `YEAR` do `read_municipality`) e a data de extração
do CSV.

## Fonte que veio truncada

No modo RM, cada pedido cobre **dezenas de municípios de uma vez** — e serviços
WFS (GeoServer) e ArcGIS REST podem **limitar o tamanho da resposta**
(`maxRecordCount` e afins) sem avisar que cortaram o resultado. Quanto maior o
recorte, maior a chance de a resposta bater no teto do servidor.

Quando isso acontece, o plugin detecta o truncamento e age de propósito:

- A camada **entra no GeoPackage mesmo assim** — meio dado com aviso vale mais
  que nenhum.
- O **log** mostra a contagem no formato "**X de Y**" (o que veio vs. o que o
  serviço diz que existe).
- A camada recebe a custom property **`truncado`**, que fica gravada junto com
  ela para consulta posterior.

!!! note "Por que carregar mesmo assim"
    Metade do dado com aviso é útil; nenhum dado sem aviso é armadilha. Sem a
    detecção, a camada pareceria completa — e o diagnóstico mente silenciosamente.

Para completar a fonte que veio truncada, você tem dois caminhos:

1. **Rodar a fonte faltante em modo Município** — volte à aba *Localização*,
   selecione os municípios que ficaram de fora um a um (ou os mais importantes
   para o seu diagnóstico), sempre apontando para o **mesmo GeoPackage**.
2. **Marcar "Atualizar bases já baixadas" e repetir** o carregamento da RM —
   o plugin refaz o download da fonte e pode conseguir o conjunto completo
   (por exemplo, quando o limite era temporário).

O mecanismo de detecção é o **mesmo do modo Município**; em modo RM ele apenas
fica muito mais provável de disparar, porque o volume pedido é maior.

O catálogo completo de fontes e algoritmos está em
[Referência › Fontes](../referencia/fontes.md) e
[Referência › Algoritmos](../referencia/algoritmos.md).
