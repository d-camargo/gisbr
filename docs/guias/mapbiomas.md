# Cobertura e uso da terra (MapBiomas Coleção 9)

A fonte **MapBiomas — Cobertura e uso da terra (Coleção 9)** — `id`
`mapbiomas_cobertura`, no painel de diagnóstico, eixo **4. Ambiental** — traz o
mapeamento anual de cobertura e uso do solo do Brasil, recortado no município
escolhido. É a **única fonte raster** do catálogo, e por isso se comporta de um
jeito um pouco diferente das outras: o resultado sai num **GeoTIFF ao lado do
GeoPackage**, não dentro dele.

O fluxo no painel é o de sempre — marque a fonte, escolha o município e clique em
**Carregar selecionadas** ([guia do painel](diagnostico.md)). Nada para
instalar: a leitura usa a pilha GDAL que já vem no QGIS.

## Ano e resolução

A Coleção 9 cobre **1985 a 2023** — 39 anos. Ao marcar a fonte, o combo **Ano do
MapBiomas** no painel habilita; o padrão é **2023** (o mais recente) e a escolha
fica salva entre sessões do QGIS.

| | |
|---|---|
| Série | 1985–2023, um arquivo por ano |
| Resolução | ~30 m (pixel de 0,000269494585236°, Landsat) |
| Tipo de dado | banda única, `Byte` — o valor do pixel **é o código da classe** |
| CRS do raster | **EPSG:4326** (WGS 84) |
| Licença | CC-BY-SA (MapBiomas) |

**Uma camada = um ano.** Não há empilhamento de série temporal nem raster
multibanda com 1985–2023. Para comparar dois anos, carregue duas vezes, mudando o
ano no combo — os arquivos têm o ano no nome e não se sobrescrevem.

## Sai em `.tif` ao lado do GeoPackage, não dentro dele

Esta é a diferença que mais surpreende quem já usou as outras fontes. O recorte
é gravado como GeoTIFF **na mesma pasta do GeoPackage**:

```
/dados/contagem.gpkg                              ← as fontes vetoriais
/dados/mapbiomas_cobertura_2023_3118601.tif       ← o recorte do MapBiomas
```

O nome é `mapbiomas_cobertura_<ano>_<código IBGE>.tif`. A camada é adicionada ao
projeto apontando para esse `.tif`.

**Por que não dentro do GeoPackage:** o GPKG até guarda raster, mas o driver o
reescreve como *tiles* PNG/JPEG — e um raster **categórico** `Byte` com paleta
não sobrevive bem a isso: a compressão com perda inventa valores de pixel
intermediários, e valor de pixel intermediário, aqui, significa **classe
errada**. GeoTIFF é o formato nativo do dado, e é nele que ele fica.

Uma consequência prática: o *skip-exists* dessa fonte olha a **existência do
`.tif`**, não as camadas do GeoPackage. Se o arquivo já está lá, a fonte entra em
`PULOU`; para refazer o recorte, marque **Atualizar bases já baixadas
(rebaixar)**, como nas outras. E se você mover o `.gpkg` de pasta, leve o `.tif`
junto.

## Não baixa 1 GB — lê só o município

O arquivo nacional de um ano tem **~1 GB** (1,05 GB em 2023). O GISBR **não** o
baixa: o MapBiomas publica COG de verdade (*Cloud-Optimized GeoTIFF*, blocos de
512×512, LZW, 9 níveis de *overview*) e o servidor aceita requisições por faixa
de bytes, então o recorte via `/vsicurl/` lê **apenas os blocos que cobrem o
município**.

Medido em Contagem/MG (~195 km²), coleção 9, ano 2023:

| | |
|---|---|
| Tempo total (download + recorte) | **16,9 s** |
| Tamanho do `.tif` gerado | **~33,5 KB** |
| Raster resultante | 580 × 685 pixels |

Capital ou município muito grande demora mais, na proporção da área — mas em
nenhum caso o arquivo nacional é transferido.

## CRS 4326, e o cuidado ao calcular área

O raster fica em **EPSG:4326**, que é o CRS do arquivo de origem, e isso é
deliberado: reprojetar raster **categórico** exige vizinho-mais-próximo e desloca
classe de pixel na borda, sem ganho nenhum (SIRGAS 2000 e WGS 84 diferem em
centímetros na escala municipal, e o QGIS reprojeta na tela sozinho). A regra
"vetor em 4674" do plugin continua valendo — ela fala de vetor. O que **é**
reprojetado é a **máscara**: o polígono do município vai de 4674 para 4326 antes
do corte, senão o recorte cairia no lugar errado.

!!! warning "Pixel em graus não tem área constante"
    Em EPSG:4326 a largura do pixel em metros diminui conforme a latitude se
    afasta do equador. Na altura de Belo Horizonte/Contagem (~19,9° S), um pixel
    de "30 m" equivale a **~840 m²**, não 900 m² — um erro de ~7% se você
    multiplicar contagem de pixels por 900. Para somar hectares de pastagem ou de
    área urbanizada, calcule no elipsoide (`QgsDistanceArea`) ou reprojete o
    recorte para a UTM local (**EPSG:31983** em MG) antes de medir.

## A paleta e as classes

O GISBR aplica automaticamente a legenda oficial da Coleção 9: renderizador
paletado, cor exata de cada classe, rótulo em **português ou inglês** conforme o
idioma do plugin, e **só as classes presentes no recorte** aparecem na legenda —
um município urbano não carrega 42 entradas de mangue e restinga no painel de
camadas. A tabela vive em `gisbr/core/data/mapbiomas_col9_classes.csv`.

As classes que costumam decidir a leitura de um diagnóstico de Plano Diretor:

| Código | Classe | Cor | Por que olhar |
|---|---|---|---|
| **15** | Pastagem | `#edde8e` | costuma ser o grande estoque de terra disponível para expansão urbana |
| **30** | Mineração | `#9c0027` | cruza com o [SIGMINE](anm.md): o que está mapeado como lavrado, não só requerido |
| **24** | Área Urbanizada | `#d4271e` | mancha urbana medida por sensor, comparável entre anos |
| **19** | Lavoura Temporária (geral) | `#d5a6bd` | agricultura de ciclo curto |
| **39** | Soja | `#f5b3c8` | destacada da temporária |
| **20** | Cana | `#db7093` | idem |
| **40** | Arroz | `#c71585` | idem |
| **62** | Algodão (beta) | `#ff69b4` | idem |
| **41** | Outras Lavouras Temporárias | `#f54ca9` | idem |
| **36** | Lavoura Perene (geral) | `#d390e6` | agricultura permanente |
| **46** | Café | `#d68fe2` | destacado da perene |
| **47** | Citrus | `#9932cc` | idem |
| **35** | Dendê | `#9065d0` | idem |
| **48** | Outras Lavouras Perenes | `#e6ccff` | idem |
| **3** | Formação Florestal | `#1f8d49` | remanescente nativo |
| **21** | Mosaico de Usos | `#ffefc3` | onde o sensor não separa agricultura de pastagem |
| **33** | Rio, Lago e Oceano | `#2532e4` | corpos d'água |
| **27** | Não Observado | `#ffffff` | sem dado — **não** é "sem cobertura" |

A legenda completa (42 classes) é a da Coleção 9 do MapBiomas Brasil, publicada
em <https://brasil.mapbiomas.org/downloads/codigos-de-legenda/>.

!!! note "As classes se aninham"
    `19` (lavoura temporária) e `39` (soja) não se somam: a hierarquia do
    MapBiomas tem níveis, e num mesmo ano/município o mapeamento usa o nível mais
    detalhado que conseguiu resolver. Somar "19 + 39 + 20" como se fossem
    disjuntas superestima. Confira quais códigos de fato aparecem no seu recorte
    antes de agregar.

## Atribuição

A Coleção 9 é CC-BY-SA: o uso em parecer ou relatório exige citar a fonte, com a
coleção e o ano usados. Formato sugerido:

> Projeto MapBiomas — Coleção 9 da Série Anual de Mapas de Cobertura e Uso da
> Terra do Brasil, ano `<ano>`, acessado em `<data>`.

A camada carrega a propriedade `data_extracao` com a data do download, justamente
para você não precisar lembrar.

## O que o GISBR não faz

- **Não calcula área nem percentual por classe.** A camada é o raster; a
  tabulação (quantos hectares de pastagem, quanto da área urbanizada cresceu) é
  análise, e está fora desta entrega.
- **Não cruza com outras camadas** — nem com o [SIGMINE](anm.md), nem com o
  [dado agropecuário do IBGE](agro.md). O cruzamento é seu, no QGIS.
- **Não traz série temporal nem taxa de conversão** entre dois anos.
- **Não baixa o mosaico nacional** para análise fora do município.

O catálogo completo de fontes está em
[Referência › Fontes](../referencia/fontes.md); o detalhe da medição do COG, em
[`docs/diagnostico-plano-diretor/mapbiomas-col9-acesso.md`](https://github.com/d-camargo/gisbr/blob/main/docs/diagnostico-plano-diretor/mapbiomas-col9-acesso.md).
