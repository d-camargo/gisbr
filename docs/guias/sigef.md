# SIGEF e bases do INCRA

Algumas bases oficiais **não têm endpoint público**: só existem por download
manual, feito por uma pessoa logada com a própria conta gov.br. É o caso das
**parcelas certificadas do SIGEF/INCRA**. Para essas, o GisBR usa o protocolo
**`arquivo`**: você baixa o arquivo no navegador, aponta a pasta onde ele caiu, e
o plugin trata a base como qualquer outra fonte do painel — recorte pelo
polígono do município, GeoPackage, camada no projeto.

!!! warning "O GisBR não pede, não guarda e não manipula credencial gov.br"
    O plugin nunca abre tela de login, nunca armazena usuário, senha ou token, e
    nunca envia credencial a lugar nenhum. A autenticação acontece **fora do
    QGIS**, no seu navegador, e o plugin só enxerga o arquivo que você já baixou.

## Por que é manual

O serviço de exportação do INCRA —
`https://certificacao.incra.gov.br/csv_shp/export_shp.py` — responde a qualquer
requisição anônima com **HTTP 200 e a página de login do gov.br** no corpo (é
login OIDC de CPF, interativo). Nenhum espelho oficial publica as parcelas de
forma anônima: INDE, `geoservicos.incra.gov.br` e `dados.gov.br` foram testados
e nenhum serve a base (medição de 23/08/2026, registrada em
[`docs/diagnostico-plano-diretor/incra-sigef-acesso.md`](https://github.com/d-camargo/gisbr/blob/main/docs/diagnostico-plano-diretor/incra-sigef-acesso.md)).
Como não existe caminho anônimo, o download manual é o único que existe — e a
URL acima entra no plugin apenas como *origem*, para o aviso saber o que dizer,
nunca como endereço de conector.

## Os três passos

1. **Baixe o arquivo logado no INCRA.** Abra
   [certificacao.incra.gov.br/csv_shp/export_shp.py](https://certificacao.incra.gov.br/csv_shp/export_shp.py)
   no navegador, entre com a sua conta gov.br e exporte as parcelas certificadas
   em Shapefile. Guarde o arquivo como veio (normalmente um `.zip`) — não
   precisa descompactar nem renomear.
2. **Aponte a pasta de downloads manuais.** No painel de diagnóstico, o campo
   **Pasta de downloads manuais** tem um botão `...` para escolher o diretório.
   O padrão é a pasta *Downloads* do sistema; se foi ali que o arquivo caiu, não
   há nada a fazer. A escolha fica salva entre sessões do QGIS.
3. **Marque a fonte e carregue.** Na árvore *Eixos e Camadas*, eixo
   **8. Político-administrativo**, marque *INCRA/SIGEF — Parcelas certificadas
   (download manual)* e clique em **Carregar selecionadas**.

Daí em diante o caminho é o mesmo das outras fontes: o plugin abre o arquivo,
recorta pelo polígono do município, grava a camada no GeoPackage e a adiciona ao
projeto. Veja o [guia do painel](diagnostico.md) para o resto do fluxo.

## Que arquivo o plugin procura

O plugin varre a pasta de downloads manuais (**só ela**, sem entrar em
subpastas) e casa o nome do arquivo, **sem diferenciar maiúsculas de
minúsculas**, com estes padrões:

| Padrão | Exemplo que casa |
|---|---|
| `*sigef*.zip` | `Sigef_Brasil_MG.zip`, `sigef-3106200.zip` |
| `*parcela*certific*.zip` | `parcelas_certificadas_mg.zip` |
| `*sigef*.shp` | `sigef_mg.shp` (com os `.dbf`/`.shx`/`.prj` ao lado) |
| `*sigef*.gpkg` | `sigef_mg.gpkg` |

Se mais de um arquivo casar, **vence o mais recente** (data de modificação) — é
o que faz uma atualização funcionar sem apagar o download antigo. Arquivos `.zip`
são lidos direto, sem descompactar: o GDAL acha o Shapefile dentro.

## Quando falta o arquivo

A fonte não falha o carregamento: ela entra na lista **`PULOU`** do log, com um
aviso que diz **qual pasta foi olhada** e **de onde baixar**, mais ou menos
assim:

> `incra_sigef_parcelas: arquivo não encontrado na pasta de downloads manuais
> (/home/você/Downloads); este conjunto de dados requer login no gov.br,
> portanto baixe-o de https://certificacao.incra.gov.br/csv_shp/export_shp.py e
> salve-o nessa pasta`

As demais fontes marcadas seguem normalmente. Se o arquivo **está** na pasta e
mesmo assim a fonte pula, confira o nome contra a tabela de padrões acima; se a
fonte aparecer em `FALHOU`, o aviso traz o caminho do arquivo e a causa relatada
pelo GDAL (zip corrompido, Shapefile sem os arquivos companheiros, etc.).

## Se o INCRA reabrir o acesso

Nada disso é permanente: se as parcelas voltarem a ser publicadas de forma
anônima (num WFS da INDE, por exemplo), a fonte deixa de exigir download manual e
passa a se comportar como as outras — sem mudança no seu fluxo, além de não
precisar mais do arquivo na pasta. O catálogo atualizado, com o protocolo de cada
fonte, está em [Referência › Fontes](../referencia/fontes.md).
