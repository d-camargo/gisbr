# Pontos de interesse (POIs) do OpenStreetMap

A fonte **OSM — POIs (equipamentos e edificações, Overpass)** — `id`
`osm_pois`, no painel de diagnóstico, eixo **7. Urbano** — baixa sozinha, via
API Overpass do OpenStreetMap, os pontos de interesse do município escolhido:
não há nada para instalar, nenhuma dependência externa. Ela é o gêmeo da fonte
de vias `osm_vias` (eixo 1. Transportes): mesma infraestrutura de rede, mesmo
GeoPackage do diagnóstico, mesmo fluxo do [guia do painel](diagnostico.md).
Marque a fonte, escolha o município e clique em **Carregar selecionadas**.

## O que conta como POI

O predicado é o do **osm2gmns** — a ferramenta que gera entradas para o modelo
de transporte grid2demand —, copiado **verbatim** para que a saída do GisBR
seja compatível (*drop-in*) com o que aquela ferramenta produz. É POI todo
elemento com tag `building` **ou** `amenity`, mais os elementos com tag de via
nos conjuntos abaixo:

| Tag | Valores que contam | O que costuma trazer |
|---|---|---|
| `building` | qualquer valor | edificações em geral |
| `amenity` | qualquer valor | escolas, hospitais, postos, bancos, restaurantes |
| `highway` | `bus_stop`, `platform` | pontos de ônibus, plataformas |
| `railway` | `depot`, `station`, `workshop`, `halt`, `interlocking`, `junction`, `spur_junction`, `terminal`, `platform` | estações, pátios e infraestrutura ferroviária |

Nos elementos classificados por `highway`/`railway`, a tag da via que fez a
classificação vai para a coluna `way` (`bus_stop`, `station`, …).

Como no OSM não há curadoria de valor, o que estiver mapeado no município vem
— cobertura e qualidade variam entre cidades, e o dado é **colaborativo, não
oficial**. Trate-o como inventário de partida, não como cadastro municipal.

### Divergência declarada em relação ao osm2gmns

O osm2gmns ignora nós soltos (só processa way/relation). O GisBR **inclui nós
com POI** — um `amenity=school` mapeado como ponto entra como feição, com
`area = 0` e `osm_type = "node"`. Quem quiser reproduzir exatamente o
comportamento do osm2gmns filtra a camada com `"osm_type" != 'node'`.

## As duas camadas

O motor grava **duas tabelas** no GeoPackage, ligadas pelo `poi_id`
compartilhado:

- **`osm_pois_<código IBGE>`** (ex.: `osm_pois_3118601`) — geometria
  **Point**, uma linha por POI. É a camada canônica, o equivalente do
  `poi.csv` do osm2gmns.
- **`osm_pois_area_<código IBGE>`** — geometria **Polygon**, só os POIs de
  way/relation: a *footprint* do prédio, para desenhar no mapa.

As colunas, nesta ordem, são as mesmas nas duas camadas:

| Coluna | Conteúdo |
|---|---|
| `poi_id` | identificador sequencial estável (inteiro) |
| `osm_type` | `node`, `way` ou `relation` |
| `osm_id` | id do elemento no OSM |
| `name` | nome do lugar no OSM; vazio quando não há `name` |
| `building` | valor da tag `building`; vazio quando não existe |
| `amenity` | valor da tag `amenity`; vazio quando não existe |
| `way` | tag de via que classificou o elemento como POI (`bus_stop`, `station`, …); vazio nos demais |
| `poi_type` | campo prático para simbologia: valor de `amenity` quando existe, senão de `building`, senão de `way` |
| `area` | área em **m²**, medida no elipsoide do SIRGAS 2000, sem reprojeção |
| `area_ft2` | a mesma área em pés quadrados (fator 10.7639) — existe só por compatibilidade com o formato do osm2gmns |
| `centroid_lon`, `centroid_lat` | coordenadas do centróide |

`poi_type` é o par que serve para simbologia e filtro (ex.:
`"poi_type" = 'school'`); `building`/`amenity`/`way` preservam as tags
originais, como o osm2gmns espera.

## Recorte por centróide, não por corte

O motor atribui ao município todo POI cujo **centróide** cai dentro do
polígono municipal — e não recorta a geometria pela divisa. O motivo: cortar a
*footprint* na divisa (clip) deformaria o polígono e corromperia a `area`, que
é justamente o atributo que modelos de transporte usam. É o mesmo critério do
IBGE para atribuir uma edificação a um município: nenhuma geometria é
alterada, e nenhum prédio aparece cortado na divisa — um POI de divisa
pertence inteiro à cidade onde cai o seu centro.

## `building=yes` e os descartes — tudo contado no log

- **`building=yes` é contado, não filtrado.** A massa de prédios sem tipo
  especificado é o grosso do OSM urbano; o motor baixa tudo e o log mostra
  quantos POIs são `building=yes`, para você saber o que tem em mãos.
- **Descartes nunca são silenciosos.** Ways abertos (sem anel fechado) entram
  na contagem de `descartadas` como `way_aberto`; relações multipolígono cujos
  membros `outer` não vêm fechados (exigiriam costura) entram como
  `relacao_sem_anel_fechado`. O log imprime as contagens:

```
OSM POI: 12874 POIs no municipio (node: 4210, way: 8563, relation: 101)
OSM POI: 9876 POIs com building=yes
OSM POI: descartadas 212 ways abertos (sem anel fechado)
OSM POI: descartadas 7 relacoes sem anel outer fechado
OSM POI: gravados 12874 pontos e 8664 areas em /.../contagem.gpkg
```

## Cache e volume

A resposta do Overpass fica em `osm_poi_<código IBGE>.json`, **na mesma pasta
do GeoPackage**; numa reexecução o plugin reaproveita esse arquivo em vez de
consultar a rede de novo. Para forçar uma consulta nova, marque **Atualizar
bases já baixadas (rebaixar)** no painel — o mesmo checkbox que refaz as
camadas existentes no GeoPackage.

Aviso: em capital o volume é grande — o download baixa a tag `building`
inteira da caixa envolvente do município — e pode levar minutos.

## Usar com o grid2demand

O algoritmo **`gisbr:export_poi_gmns`** (Caixa de Ferramentas → *GisBR →
Diagnóstico → Export POIs to GMNS / grid2demand poi.csv*) exporta a camada
`osm_pois_*` para um `poi.csv` com o cabeçalho **exato** do osm2gmns:

```
name,poi_id,osm_way_id,osm_relation_id,building,amenity,way,geometry,centroid,area,area_ft2
```

É esse CSV que o `grid2demand` lê via `GRID2DEMAND(input_dir).load_network()`.
O parâmetro de saída chama-se `OUTPUT`:

```python
import processing
processing.run("gisbr:export_poi_gmns", {
    "INPUT": "/dados/contagem.gpkg|layername=osm_pois_3118601",
    "OUTPUT": "/dados/gmns/poi.csv",
})
```

!!! warning "O GisBR entrega o `poi.csv` — o resto do fluxo é com você"
    Com apenas o `poi.csv`, o grid2demand também espera `node.csv`/`link.csv`
    da rede — que a fonte `osm_vias` mais um export de rede **ainda não gera
    automaticamente**. O GisBR entrega o `poi.csv`; o restante do fluxo do
    grid2demand (zonas em grade, taxas de viagem do ITE, produção/atração,
    modelo gravitacional, `agent.csv`) está **fora do plugin**.

## O que o GisBR não faz

Para não haver dúvida sobre o escopo:

- **Não gera zonas em grade** (`net2zone`) nem calcula **matriz de distância**
  entre centróides.
- **Não traz taxas de viagem** do ITE (`poi_trip_rate.csv`),
  **produção/atração**, **modelo gravitacional** nem `agent.csv`.
- **Não lê arquivos `.osm`/`.pbf`**: a única entrada de dados OSM é o
  Overpass, pela rede.

O catálogo completo de fontes e algoritmos está em
[Referência › Fontes](../referencia/fontes.md) e
[Referência › Algoritmos](../referencia/algoritmos.md).
