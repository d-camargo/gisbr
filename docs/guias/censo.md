# Dados do Censo (censobr)

O geobr entrega **só a geometria** do setor censitário: população, renda e
domicílios moram no pacote irmão **[censobr](https://github.com/ipeaGIT/censobr)**
(IPEA). O painel de diagnóstico costura os dois de uma vez: com a opção do Censo
ligada, a camada `geobr_setores_<código IBGE>` já é gravada no GeoPackage **com
as colunas do Censo dentro**, pronta para um mapa coroplético — sem passo manual
de junção.

Quem prefere o Processing continua com o algoritmo
[`gisbr:join_censo`](geobr.md#juntar-dados-do-censo-join_censo), que faz a mesma
junção sobre uma camada já carregada. As duas portas usam **o mesmo núcleo**;
o painel é o caminho de quem está montando o diagnóstico do município.

## Passo a passo

1. **Escolha UF e município** normalmente, como no
   [guia do painel](diagnostico.md).
2. **Marque `Setores censitarios (IBGE/geobr)`**, no eixo *3. Demografia* da árvore de
   fontes. A opção do Censo age **só** sobre essa fonte; se ela não estiver
   marcada, o painel avisa no log e não anexa nada.
3. **Ligue o grupo "Attach Census tables to census tracts (censobr)"** — o
   checkbox no título do grupo, logo abaixo da árvore de fontes. Ele vem
   desmarcado.
4. **Ano do censo** — o combo lista os anos que o censobr publica: **2000, 2010
   e 2022**.
5. **Tabelas** — a lista traz os conjuntos daquele ano (`Basico`, `Domicilio`,
   `DomicilioRenda`, `Pessoa`/`Pessoas`, `PessoaRenda`, …), cada um com seu
   checkbox. Pode marcar mais de um. O padrão é **`Basico`**, que é a menor
   tabela e a que serve para quase todo diagnóstico.
6. **Carregar selecionadas.** O log mostra o arquivo do censobr, o tamanho, e
   quantos setores casaram e quantos ficaram sem correspondência.

A escolha de ano e tabelas fica salva entre sessões do QGIS. Trocar o ano
repopula a lista de tabelas, mantendo marcado o que ainda existir no ano novo.

!!! note "Rótulos ainda em inglês"
    As traduções PT-BR desse grupo ainda não entraram no `.qm`, então o painel
    mostra os rótulos em inglês: *Attach Census tables to census tracts
    (censobr)*, *Census year*, *Tables / Datasets*.

## As colunas que aparecem

Cada tabela entra com **prefixo próprio**, o nome do conjunto seguido de `_`:
`Basico_V001`, `DomicilioRenda_V002`, e assim por diante. Marcar duas tabelas
anexa as duas, cada uma com seu prefixo — não há colisão de nomes entre elas
nem com os campos da geometria.

!!! warning "Tabela larga é tabela larga"
    `Pessoa`/`Pessoas` tem centenas de colunas. Marcar várias tabelas grandes de
    uma vez pode passar do teto de colunas do SQLite que sustenta o GeoPackage;
    o log avisa quando a camada final passa de 1000 colunas. Marque o que vai
    usar.

## O ano do setor acompanha o ano do censo

Os códigos de setor **mudam de um censo para o outro**. Por isso, com a opção
ligada, o plugin baixa a malha de setores **do mesmo ano** do censo escolhido —
censo 2010 traz setores de 2010, não os de 2022 (que seriam o padrão do painel).

Se o ano escolhido não existir na malha do geobr, o plugin carrega a camada
**só com a geometria**, no ano padrão, e diz no log por que o censo não foi
anexado. Juntar anos diferentes é pior que não juntar: sairia uma camada cheia
de `NULL` com cara de dado bom.

## Exige backend Parquet

O censobr publica em **Parquet**, então esta opção depende do driver GDAL
`Parquet`/`Arrow` **ou** do `pyarrow` — as duas alternativas estão em
[Instalação › Parquet](../instalacao.md#opcional-parquet-algoritmos-v2-e-join_censo)
(no Linux, o caminho mais curto é `pip install --user pyarrow`).

Sem nenhum dos dois, **a fonte não falha**: os setores são baixados e gravados
normalmente, só sem as colunas do Censo, e o log traz o aviso com a orientação
de instalação. O que você pediu — o setor — foi entregue.

## Tamanho do download

Os arquivos do censobr são **nacionais** — não há como pedir só um município ao
servidor. A diferença entre tabelas é de duas ordens de grandeza:

| Tabela (2022) | Tamanho |
|---|---|
| `Basico` | 8,6 MB |
| `Pessoas` | 166,7 MB |

O log imprime o tamanho **antes** de baixar, para você saber no que clicou. Cada
arquivo é baixado **uma vez** e fica no cache em disco (`~/.cache/geobr-qgis/`, ou o equivalente do seu sistema);
da segunda vez em diante, o mesmo ano/tabela sai do cache, inclusive para outro
município.

O **recorte por município acontece antes de montar a camada**: o plugin filtra
as linhas do parquet pelo `code_muni` (ou, quando essa coluna não existe, pelo
prefixo de 7 dígitos do `code_tract`) e só então constrói as feições. É isso que
mantém o painel respondendo mesmo com uma tabela de centenas de milhares de
linhas.

## Trocar a seleção depois

O painel **pula a fonte que já existe** no GeoPackage — inclusive a de setores.
Então, se você já carregou `geobr_setores` e depois quer outro ano ou outra
tabela do Censo, mudar a seleção não basta: marque também **Atualizar bases já
baixadas (rebaixar)** antes de clicar em *Carregar selecionadas*. Sem isso, a
fonte entra em `PULOU` com a mensagem lembrando desse checkbox, e a camada
antiga fica como estava.

## Join que casou zero setor

Se uma tabela não casar **nenhum** setor, o resultado dela é **descartado**: a
camada segue com a geometria (e com as outras tabelas que casaram), e o log traz
o aviso. Uma camada com trezentas colunas todas `NULL` é erro disfarçado de
sucesso; geometria sozinha é um resultado honesto.

Casos típicos de zero correspondência são ano ou tabela trocados. Falha de uma
tabela — catálogo fora do ar, download interrompido, leitura recusada — também
não derruba as outras: vira aviso no log e o laço segue.

!!! note "Por que a chave precisa ser normalizada"
    `code_tract` vem como **número** no geobr e como **texto** no censobr. Um
    join direto casaria zero registros; o plugin converte a chave para texto nos
    dois lados antes de juntar. É a mesma correção que já valia no
    `gisbr:join_censo`.
