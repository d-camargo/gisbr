# Processos minerários do SIGMINE (ANM)

O SIGMINE é o sistema de informações geográficas da mineração da **ANM** —
Agência Nacional de Mineração. Ele publica os **processos minerários**: os
polígonos de área requerida ou autorizada para pesquisa e lavra, com o titular,
a substância e a fase em que o processo está. Num diagnóstico de Plano Diretor é
a base que mostra quanto do território municipal está comprometido com mineração
— e em que estágio.

No painel, eixo **4. Ambiental**, há **duas coisas diferentes** com o mesmo
nome — e a diferença importa:

| Fonte no painel | `id` | O que é |
|---|---|---|
| ANM/SIGMINE — Processos minerarios | `anm_sigmine` | **serviço ao vivo** (ArcGIS REST em `geo.anm.gov.br`), todas as fases |
| ANM/SIGMINE — Requerimento de pesquisa | `anm_sigmine_req_pesquisa` | **produto mensal publicado**, só essa fase |
| ANM/SIGMINE — Licenciamento | `anm_sigmine_licenciamento` | idem |
| ANM/SIGMINE — Concessao de lavra | `anm_sigmine_concessao_lavra` | idem |
| ANM/SIGMINE — Lavra garimpeira | `anm_sigmine_lavra_garimpeira` | idem |

!!! warning "As quatro fontes por fase estão indisponíveis hoje"
    O host que publica o produto mensal (`app.anm.gov.br`) **não responde** —
    medição de 17/09/2026. Elas continuam no catálogo, marcadas como
    indisponíveis, e o painel diz isso quando você as marca (ver
    [O que o painel mostra](#o-que-o-painel-mostra-com-o-host-fora)). A fonte ao
    vivo `anm_sigmine` funciona normalmente.

## Ao vivo ou retrato mensal — qual usar

As duas origens respondem perguntas diferentes, e é por isso que convivem no
catálogo em vez de uma substituir a outra:

- **`anm_sigmine` (ao vivo)** responde *"o que está valendo agora"*. É consulta
  ao servidor da ANM no momento em que você clica: filtra pela caixa envolvente
  do município e o motor recorta pelo polígono municipal, como em qualquer fonte
  de bbox. Rápida (0,11 s no teste de resposta do serviço) e sempre atual.
- **As quatro por fase (produto mensal)** respondem *"qual era o retrato
  oficial na data do estudo"*. É o arquivo que a ANM publica mensalmente —
  citável num parecer técnico como "SIGMINE, extração de `<mês>/<ano>`", e
  reproduzível: quem refizer o diagnóstico com o mesmo arquivo chega ao mesmo
  número.

Para desenhar o mapa do diagnóstico, use a fonte ao vivo. Para fechar o número
que vai no texto do parecer, o produto mensal é o que se cita — quando estiver
disponível.

## As quatro fases

O produto mensal do SIGMINE vem num arquivo único, com todas as fases juntas na
coluna **`FASE`**. As quatro fontes do painel apontam para **o mesmo download** e
se distinguem por um filtro de atributo — o arquivo baixa uma vez e as quatro
fontes o reaproveitam do cache:

| Fonte | Filtro aplicado | O que significa a fase |
|---|---|---|
| Requerimento de pesquisa | `FASE = 'REQUERIMENTO DE PESQUISA'` | pedido protocolado, ainda sem autorização |
| Licenciamento | `FASE = 'LICENCIAMENTO'` | regime de licenciamento (areia, argila, brita para construção civil) |
| Concessao de lavra | `FASE = 'CONCESSÃO DE LAVRA'` | lavra autorizada — mina em operação ou apta a operar |
| Lavra garimpeira | `FASE = 'LAVRA GARIMPEIRA'` | permissão de lavra garimpeira (PLG) |

Em termos de diagnóstico, a leitura é de pressão futura para uso consolidado:
*requerimento* é intenção, *licenciamento* e *lavra garimpeira* são atividade em
regimes específicos, e *concessão de lavra* é o compromisso mais forte que o
território tem com mineração.

!!! note "`FASE` é caixa alta e acentuada"
    Os literais são exatamente como a ANM os devolve — `CONCESSÃO DE LAVRA`, com
    cedilha e til, em maiúsculas. Se você for filtrar a fonte ao vivo à mão no
    QGIS, copie o valor daqui; uma expressão com `Concessão de Lavra` não casa
    nada e o silêncio parece "não há mineração no município".

### Filtrando a fonte ao vivo por fase

Enquanto o produto mensal não volta, dá para chegar perto usando a camada
`anm_sigmine_<código IBGE>` do GeoPackage e um filtro de atributos. As fases
apuradas em Minas Gerais (48.827 processos, medição de 17/09/2026), com a
contagem estadual:

| `FASE` | Processos em MG |
|---|---|
| `APTO PARA DISPONIBILIDADE` | 552 |
| `AUTORIZAÇÃO DE PESQUISA` | 24.533 |
| `CONCESSÃO DE LAVRA` | 3.126 |
| `DIREITO DE REQUERER A LAVRA` | 1.028 |
| `DISPONIBILIDADE` | 1.766 |
| `LAVRA GARIMPEIRA` | 276 |
| `LICENCIAMENTO` | 3.388 |
| `RECONHECIMENTO GEOLÓGICO` | 2 |
| `REGISTRO DE EXTRAÇÃO` | 225 |
| `REQUERIMENTO DE LAVRA` | 5.940 |
| `REQUERIMENTO DE LAVRA GARIMPEIRA` | 1.400 |
| `REQUERIMENTO DE LICENCIAMENTO` | 2.208 |
| `REQUERIMENTO DE PESQUISA` | 4.074 |
| `REQUERIMENTO DE REGISTRO DE EXTRAÇÃO` | 309 |

Fora de MG ocorrem também `DADO NÃO CADASTRADO` e, em lotes residuais, valor em
branco — trate-os como fase desconhecida, não como ausência de processo.

## As colunas

Tanto o serviço ao vivo quanto o produto mensal trazem os mesmos campos:

| Coluna | Conteúdo |
|---|---|
| `PROCESSO` | número do processo minerário (formato `NNNNNN/AAAA`) |
| `NUMERO`, `ANO` | as duas partes do número, separadas |
| `FASE` | fase do processo (tabela acima) |
| `NOME` | titular do processo |
| `SUBS` | substância requerida ou autorizada (ex.: `MINÉRIO DE FERRO`, `AREIA`) |
| `USO` | uso pretendido (ex.: `Construção civil`, `Industrial`) |
| `AREA_HA` | área do polígono do processo, em hectares |
| `UF` | unidade federativa |
| `ULT_EVENTO` | último evento registrado no processo |

O CRS declarado pelo serviço é **EPSG:4674** (SIRGAS 2000), o mesmo do resto do
plugin. Se você abrir um arquivo do SIGMINE baixado à mão e ele vier sem `.prj`
ou com datum legado (SAD69, WGS 84), atribua EPSG:4674 antes de cruzar com as
outras camadas.

## O que o painel mostra com o host fora

A medição de 17/09/2026 em `app.anm.gov.br`: o IP resolve
(`200.198.193.243`), mas a conexão **estoura o tempo limite** tanto em 443 como
em 80, e nenhum certificado é apresentado. Não é bloqueio, não é certificado
vencido — é servidor inacessível.

Diante disso, as quatro fontes por fase entram **desabilitadas com aviso**.
Marcá-las e clicar em **Carregar selecionadas** não gera erro nem camada vazia:
elas caem na lista **`PULOU`** do log — nunca em `FALHOU`, porque não é falha de
quem está usando o plugin — com o motivo medido e o link do portal oficial, mais
ou menos assim:

> `anm_sigmine_concessao_lavra: fonte indisponível (Host app.anm.gov.br
> indisponível (connection timed out)); consulte o portal oficial em
> https://app.anm.gov.br/`

As demais fontes marcadas carregam normalmente na mesma execução.

!!! danger "Nunca há troca de origem por baixo do pano"
    Com o produto mensal fora do ar, o GISBR **não** cai silenciosamente para o
    serviço ao vivo. São bases diferentes, com datas de referência diferentes, e
    uma fonte que troca de origem sem o usuário saber é o pior tipo de dado num
    parecer técnico. Se você quer o ao vivo, marque `anm_sigmine` — explicitamente.

## Se o host voltar

Nada disso é permanente. Quando `app.anm.gov.br` voltar a responder, o caminho é
medir a URL exata do arquivo (nacional e/ou por UF), o tamanho e a data de
referência, conferir a âncora TLS do host e tirar a marca de indisponível — o
mecanismo de download e o filtro por fase já estão escritos e testados, porque o
que falta é **a URL, que é um dado**, não o desenho. Do seu lado, as quatro
fontes simplesmente param de aparecer em `PULOU` e passam a gravar camada.

O catálogo atualizado, com o protocolo e o estado de cada fonte, está em
[Referência › Fontes](../referencia/fontes.md); a medição completa dos endpoints
da ANM está em
[`docs/diagnostico-plano-diretor/anm-sigmine-acesso.md`](https://github.com/d-camargo/gisbr/blob/main/docs/diagnostico-plano-diretor/anm-sigmine-acesso.md).
