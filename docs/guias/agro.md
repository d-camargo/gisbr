# Dados agropecuários do IBGE (PAM e Censo Agropecuário)

O eixo **9. Agropecuária** do painel de diagnóstico traz três fontes
**tabulares** do IBGE, servidas pela API v3 de Agregados
(`servicodados.ibge.gov.br`) — pública, sem token, sem nada para instalar:

| Fonte no painel | `id` | Tabela | Período |
|---|---|---|---|
| IBGE — PAM Lavouras temporárias | `ibge_pam_temporarias` | 1612 | apuração mais recente |
| IBGE — PAM Lavouras permanentes | `ibge_pam_permanentes` | 1613 | apuração mais recente |
| IBGE — Censo Agropecuário 2017 | `ibge_censo_agro` | 6881 | 2017 |

São as únicas fontes do catálogo que **não nascem espaciais**: o IBGE entrega
números por município, e o GISBR os pendura no polígono municipal. O fluxo no
painel é o mesmo das outras — marque a fonte, escolha o município, clique em
**Carregar selecionadas** ([guia do painel](diagnostico.md)).

## O que é PAM e o que é Censo Agropecuário

**PAM — Produção Agrícola Municipal.** Pesquisa **anual**, por município e por
produto. Vem separada em duas tabelas porque o IBGE as separa: *lavouras
temporárias* (soja, milho, cana, feijão — replantadas a cada ciclo) e *lavouras
permanentes* (café, laranja, banana — o pé fica no lugar). As variáveis que o
GISBR pede:

| Variável | Unidade | Sai em qual tabela |
|---|---|---|
| Área plantada / Área destinada à colheita | hectares | temporárias / permanentes |
| Área colhida | hectares | as duas |
| Quantidade produzida | toneladas | as duas |
| Rendimento médio da produção | kg/ha | as duas |
| Valor da produção | mil reais | as duas |

**Censo Agropecuário 2017.** Não é pesquisa anual: é o censo do setor, feito de
década em década (o anterior é 2006). O GISBR pede dele **número de
estabelecimentos agropecuários com área** (unidades) e **área dos
estabelecimentos** (hectares), quebrados por *utilização das terras* — lavouras
permanentes, lavouras temporárias, pastagens naturais, pastagens plantadas,
matas e florestas naturais, e o total.

Em diagnóstico de Plano Diretor os dois respondem perguntas diferentes: a PAM
diz **o que o município produz hoje**, o Censo diz **como a terra está
organizada** (quantos estabelecimentos, de que tamanho, em que uso).

## Qual ano sai

- **PAM:** a **apuração mais recente** que a tabela tiver. O GISBR pede
  `periodos/-1` à API e o IBGE resolve — não há seletor de ano no painel para
  estas fontes, e nem há como pedir uma série histórica: **uma camada = um
  ano**. Na medição de 17/09/2026 as tabelas 1612 e 1613 respondiam com
  **2025**.
- **Censo Agropecuário:** sempre **2017**, porque é o censo que existe. Quando
  o IBGE publicar o próximo, a fonte passa a apontar para ele.

O ano efetivamente usado vem junto do dado: a camada carrega a propriedade
`data_extracao` com a data do download, e o ano da apuração é o que a API
devolveu.

## Como a tabela vira camada

O motor junta o resultado da API ao **polígono do município** — o mesmo que o
resto do plugin usa — e grava no GeoPackage uma camada com **uma feição só**, em
**formato largo**:

- **1 feição** — o município, geometria de polígono, EPSG:4674.
- **`code_muni`** — o código IBGE de 7 dígitos, em texto.
- **1 coluna por (variável × produto)** — o nome sai do nome da variável e do
  produto, sem acento, em minúsculas, com `_` no lugar da pontuação, truncado no
  limite de 63 caracteres do GeoPackage. Por exemplo:
  `area_plantada_soja_em_grao`, `valor_da_producao_cafe_total_em_grao_verde`.

O nome da camada no GeoPackage é `<id da fonte>_<código IBGE>` — ex.:
`ibge_pam_temporarias_3106200`. Como nas outras fontes, uma camada que já existe
é pulada, salvo se você marcar **Atualizar bases já baixadas (rebaixar)**.

!!! note "É agregado municipal, não geometria de lavoura"
    A geometria é o limite do município, repetido em todas essas camadas. O dado
    é o número que o IBGE apura **para o município inteiro** — não há polígono de
    talhão, de propriedade nem de área plantada. Para desenho de uso do solo, o
    que existe no plugin é o raster do
    [MapBiomas](mapbiomas.md).

## Por que uma cultura pode não aparecer

Essa é a dúvida que aparece primeiro, e tem três causas diferentes — vale
distinguir antes de concluir que "falta dado":

**1. O município não produz aquilo.** A PAM só lista produto que foi informado
para aquele município. Café não sai em Contagem porque não há café em Contagem,
e a ausência da coluna é a resposta correta.

**2. O IBGE devolveu um código especial, e o GISBR o converteu em NULL — nunca
em zero.** A estatística oficial brasileira usa marcadores no lugar do número:

| Código | O que significa na tabela do IBGE | Como sai na camada |
|---|---|---|
| `-` | fenômeno não existente | **NULL** |
| `..` | não se aplica / não informado | **NULL** |
| `...` | dado não disponível | **NULL** |
| `X` | valor omitido por **sigilo estatístico** | **NULL** |

O motivo de nenhum deles virar `0`: num diagnóstico, *"não há dado"* e *"a área
plantada é zero"* são conclusões opostas, e um zero fabricado entra no relatório
sem aviso. Se a célula estiver vazia na tabela de atributos, o IBGE não afirmou
um número — e é isso que a camada está dizendo. O `X` merece atenção extra: ele
aparece quando há **poucos produtores** e publicar o número os identificaria; o
dado existe, mas não é publicável.

**3. O produto não tinha valor em nenhuma variável, e a coluna foi
descartada.** Se *todas* as variáveis de um produto vierem em código especial,
ele não entra na camada — seriam cinco colunas inteiramente vazias. Mas o
descarte **nunca é silencioso**: o log conta e nomeia os produtos descartados.

```
AgroPipeline: camada 'ibge_pam_temporarias_3106200' criada com 14 produtos e 71 campos.
Aviso: AgroPipeline: descartados 47 produtos sem valor numérico em nenhuma
variável: Abacaxi, Algodão herbáceo (em caroço), Alho, ...
```

Sem isso, a PAM produziria ~60 culturas × 5 variáveis = 300 colunas quase todas
nulas em qualquer município.

E se **nenhum** produto tiver valor, a fonte não falha: entra na lista
**`PULOU`** do log, com a mesma contagem. É o caso de município cuja lavoura
inteira está sob sigilo ou sem apuração no ano.

## Quando a API não responde

O GISBR conversa **apenas** com `servicodados.ibge.gov.br/api/v3`. O SIDRA
clássico (`apisidra.ibge.gov.br`) foi medido e **descartado**: responde HTTP 403
com o HTML de desafio da Cloudflare, que um conector ingênuo entregaria ao
parser reportando "JSON inválido" em vez da causa.

Por isso o conector **olha o corpo antes de parsear**. Se vier HTML em vez de
JSON, a mensagem no log diz que veio HTML (e o título da página), não uma falha
genérica de leitura:

> `Corpo HTML recebido ('Just a moment...') ao inves de JSON v3 da API de
> Agregados`

A âncora TLS do host já vem embarcada no plugin — ver
[Referência › Rede e certificados](../referencia/rede.md).

## O que o GISBR não faz

- **Não empilha série temporal.** Uma camada = um ano. Comparar 2015 com 2025 é
  carregar duas vezes, em dois GeoPackages (ou renomeando a camada).
- **Não consulta UF nem país inteiro.** A API aceita `N6[in N3[31]]` para todos
  os municípios de um estado, e isso fica registrado como porta aberta — o
  plugin é município-cêntrico e consulta um município por vez.
- **Não calcula indicador derivado** (participação da soja na área plantada,
  produtividade relativa, ranking). O plugin põe o número no mapa; interpretar é
  com você.

O catálogo completo, com a tabela e as variáveis de cada fonte, está em
[Referência › Fontes](../referencia/fontes.md).
