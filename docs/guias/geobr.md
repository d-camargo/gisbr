# Espelho geobr / censobr

Além do painel de diagnóstico, o GisBR é um **Processing Provider** chamado
`gisbr`: ele traz para dentro da Caixa de Ferramentas de Processamento os
mesmos conjuntos de dados que os pacotes **[geobr](https://github.com/ipeaGIT/geobr)**
e **[censobr](https://github.com/ipeaGIT/censobr)** (IPEA) oferecem em R e
Python — "uma linha, uma camada". São **55 algoritmos** no total, e como são
algoritmos de Processing, funcionam também em modelos gráficos, em lote e no
Console Python.

## Onde eles ficam

Abra *Processar → Caixa de Ferramentas* e procure o provedor **GisBR**. Os
algoritmos estão em três grupos:

| Grupo | O que tem |
|---|---|
| **Geografias (GPKG / v1.7.0)** | 26 algoritmos `read_*` — o catálogo legado do IPEA em GeoPackage. É o caminho padrão: lê **nativamente**, sem nada instalado além do QGIS. |
| **Geografias (Parquet / v2.0.0)** | 28 algoritmos `read_*_v2` — o catálogo novo, em GeoParquet. Precisa do driver GDAL Parquet **ou** do `pyarrow`. |
| **Censo (censobr)** | `join_censo` — junta as tabelas do censo aos setores censitários. |

A lista completa, algoritmo por algoritmo e com o `id` de cada um, está em
**[Referência › Algoritmos](../referencia/algoritmos.md)**.

## Parâmetros comuns

Todos os `read_*` (v1 e v2) compartilham os mesmos quatro parâmetros:

| Parâmetro | Rótulo no QGIS | Tipo | Observação |
|---|---|---|---|
| `YEAR` | *Ano* | enum | Preenchido a partir do catálogo do IPEA. O padrão é o **ano mais recente** disponível para aquela geografia. |
| `CODE` | *Código / sigla* | texto | `all` (padrão), sigla da UF (`MG`), código de UF (`31`) ou código IBGE de município (`3106200`). |
| `SIMPLIFIED` | *Geometria simplificada* | booleano | Padrão `True` — geometrias mais leves, renderização rápida. Desmarque quando precisar do traçado original. |
| `OUTPUT` | *Saída* | camada | Destino: arquivo, `memory:` ou camada temporária. |

!!! warning "`YEAR` é o índice do enum, não o ano"
    No Console Python, `YEAR` recebe a **posição** do ano na lista de anos
    disponíveis — `0` é o mais antigo. Passar `2020` seria lido como índice
    2020 e falharia. **Omita o parâmetro** para usar o ano mais recente, que é
    o que você quer na maior parte das vezes.

Algumas geografias (país, biomas, Amazônia legal…) são nacionais e **não têm**
`CODE`: nesses casos o parâmetro simplesmente não aparece.

## No Console Python

```python
import processing

# Municípios de Minas Gerais, geometria simplificada, camada em memória
processing.run("gisbr:read_municipality", {
    "CODE": "MG",
    "SIMPLIFIED": True,
    "OUTPUT": "memory:",
})
```

O `id` de cada algoritmo é `gisbr:<nome da função>` — o mesmo nome usado no
geobr em R/Python (`gisbr:read_state`, `gisbr:read_census_tract`,
`gisbr:read_schools`…), com o sufixo `_v2` para os do backend Parquet:

```python
# Setores censitários de Belo Horizonte pelo catálogo v2
processing.run("gisbr:read_census_tract_v2", {
    "CODE": "3106200",
    "SIMPLIFIED": True,
    "OUTPUT": "memory:",
})
```

## v1 (GeoPackage) ou v2 (Parquet)?

| | **v1 — GPKG / 1.7.0** | **v2 — Parquet / 2.0.0** |
|---|---|---|
| Requisito | Nenhum: o QGIS abre GeoPackage nativamente. | Driver GDAL Parquet **ou** `pyarrow` — veja [Instalação](../instalacao.md#opcional-parquet-algoritmos-v2-e-join_censo). |
| Anos cobertos | Dados do IBGE até ~2020. | Até 2022/2025. |
| Download | Geografias fatiadas por UF (municípios, setores, áreas de ponderação, meso e microrregiões) baixam **só o arquivo daquele estado** quando `CODE` é informado. | Os arquivos são **nacionais**; o filtro por `CODE` é aplicado **depois** de carregar. |
| Exclusivas | — | `read_favela_v2`, `read_polling_places_v2`, `read_quilombola_land_v2` — não existem no catálogo legado. |

Na prática: **comece pelo v1**. Vá ao v2 quando precisar de um ano mais
recente ou de uma das três geografias exclusivas. Se o Parquet não estiver
disponível na sua instalação, os algoritmos v2 falham com uma mensagem
dizendo como instalá-lo, em vez de quebrar silenciosamente.

## Juntar dados do censo (`join_censo`)

O geobr entrega **só a geometria** — população, renda e domicílios moram no
censobr. O `join_censo` costura os dois:

1. Rode um `read_census_tract` (ou `read_census_tract_v2`) para o município
   desejado — essa é a camada de entrada, e ela precisa do campo `code_tract`.
2. Abra *Censo (censobr) → Juntar dados do censo (censobr) a setores* e
   preencha:

    | Parâmetro | Observação |
    |---|---|
    | *Setores censitários (geobr)* | a camada do passo 1. |
    | *Ano do censo* | 2000, 2010 ou 2022 (padrão: 2010). |
    | *Dataset do censobr* | ex.: `Basico`, `Domicilio`, `DomicilioRenda` (padrão), `Pessoa`, `PessoaRenda`. |
    | *Campo-chave (setor)* | `code_tract`, já preenchido. |
    | *Prefixo nos campos do censo* | `censo_` — evita colisão de nomes com os campos da geometria. |

3. O resultado é a camada de setores com as colunas do censo anexadas, prontas
   para um mapa coroplético.

!!! note "Chave normalizada e contagem reportada"
    `code_tract` vem como **número** no geobr e como **texto** no censobr — um
    join direto casaria zero registros. O algoritmo normaliza a chave para
    texto nos dois lados antes de juntar, e informa no log quantos setores
    casaram e quantos ficaram sem correspondência. Se esse segundo número for
    alto, é sinal de ano ou dataset trocado, não de erro do plugin.

    O `join_censo` também depende do Parquet (é o formato do censobr), e os
    arquivos de setor do censobr são **nacionais** — o primeiro download é
    pesado. O join mantém apenas os setores da camada de entrada.

## CRS

Tudo sai em **SIRGAS 2000 / EPSG:4674**, geográfico, como no geobr original.
Para medir área ou distância, reprojete antes para o fuso UTM correspondente
(em Belo Horizonte, EPSG:31983) — cálculo métrico em coordenadas geográficas
não vale.

## Vintage dos dados

Não confunda o **ano de referência** dos dados (a *vintage*: o censo de 2010, a
malha municipal de 2020) com a **data em que você baixou**. O parâmetro `YEAR`
escolhe a vintage; a data do download só diz quando o arquivo entrou no seu
cache. As duas coisas andam separadas, e é a vintage que precisa constar do
seu relatório.

## Cache e mirrors

O primeiro uso de cada geografia baixa o arquivo e o guarda em disco
(`~/.cache/geobr-qgis/`, ou o equivalente do seu sistema); as execuções
seguintes leem do cache, sem rede. Apague a pasta para forçar um novo
download. O download tenta o servidor do IPEA e, se ele falhar, o espelho no
GitHub — os detalhes, e o que fazer diante do erro de certificado no Windows,
estão em [Referência › Rede e certificados](../referencia/rede.md).
