# Diagnóstico de Plano Diretor

O painel de diagnóstico é a porta principal do GisBR: você escolhe **um
município**, marca as camadas oficiais que interessam e o plugin baixa cada uma
já **filtrada e recortada por aquele município**, grava tudo num **GeoPackage** e
adiciona as camadas ao projeto. É o atalho para montar a base cartográfica de
elaboração ou revisão de um Plano Diretor sem sair do QGIS.

## Abrir o painel

Clique no botão **GisBR** na barra de ferramentas, ou vá em *Complementos →
GisBR → Diagnóstico Plano Diretor (GisBR)*. O painel abre encaixado à direita da
janela do QGIS.

## Passo a passo

1. **Estado (UF)** — escolha a unidade da federação. Na primeira seleção o plugin
   baixa a malha municipal do geobr para listar os municípios; isso leva alguns
   segundos e o log avisa (*"Carregando municípios de …"*).
2. **Município** — o combo aceita digitação: escreva parte do nome e escolha na
   lista. O campo **Código IBGE** logo abaixo é preenchido sozinho pela seleção
   (você também pode digitar o código de 7 dígitos direto, ex.: `3106200`).
3. **Fontes de Dados** — a árvore *Eixos e Camadas* traz as fontes agrupadas nos
   8 eixos, na ordem 1..8. Marque o checkbox de cada camada desejada. Não há
   limite: pode marcar um eixo inteiro ou fontes soltas de eixos diferentes.
4. **GeoPackage de destino** — o botão `...` abre o seletor de arquivo. Se você
   digitar um caminho sem a extensão, o plugin acrescenta `.gpkg`. Aponte sempre
   para o **mesmo** GeoPackage do município: ele é o acervo do diagnóstico, e é
   o que permite ao plugin pular o que já foi baixado.
5. **Pasta de downloads manuais** — só importa para as fontes que exigem login
   gov.br (hoje, o INCRA/SIGEF). O padrão é a pasta *Downloads* do sistema. Veja
   o [guia do SIGEF](sigef.md).
6. **Adicionar imagem de satélite ao fundo** *(opcional)* — acrescenta o mosaico
   Esri World Imagery **como último item** da árvore de camadas, ou seja, ao
   fundo, sem cobrir o que foi baixado.
7. **Atualizar bases já baixadas (rebaixar)** *(opcional)* — força o rebaixamento
   das fontes que já existem no GeoPackage. Deixe **desmarcado** no uso normal.
8. **Carregar selecionadas** — inicia. O **Log de Execução**, no rodapé do
   painel, mostra o município resolvido e, ao final, três listas: `OK`,
   `FALHOU` e `PULOU`, cada uma com o `id` da fonte e o motivo.

## O que esperar do resultado

- **Uma camada por fonte no GeoPackage.** O nome da tabela é `<id>_<código IBGE>`
  (ex.: `sicar_imoveis_3106200`); no projeto ela aparece com o nome de exibição
  "*&lt;nome da fonte&gt; - &lt;município&gt;*". A camada adicionada ao projeto é
  lida **do GeoPackage**, então fechar e reabrir o projeto continua funcionando.
- **Recorte pelo polígono do município, não pela bbox.** As fontes que o servidor
  não sabe filtrar por código são pedidas pela caixa envolvente (*bounding box*)
  e depois **recortadas pelo polígono real** do município. Sem isso, a consulta
  traria pedaços dos vizinhos — numa região metropolitana, a mancha urbana
  transborda por cima de meia dúzia de cidades.
- **Camada vazia é pulada, não criada.** Se a base não retornou nada para aquele
  município (ex.: nenhum aterro sanitário licenciado), a fonte entra em `PULOU`
  com o aviso correspondente — o plugin não cria uma camada-tabela vazia no
  GeoPackage. O mesmo vale quando sobra zero feição **depois** do recorte.
- **Fonte já baixada é pulada.** Se `<id>_<código>` já existe no GeoPackage, a
  fonte entra em `PULOU` com *"já existe no GeoPackage"*. Rodar de novo para
  acrescentar uma camada nova é barato: só o que falta é baixado. Para
  reprocessar de fato, marque *Atualizar bases já baixadas*.
- **Data de extração gravada na camada.** Cada camada baixada leva a propriedade
  `data_extracao` (o dia do download) e `fonte`. Não confunda com a *vintage* dos
  dados — o ano de referência do conjunto, que é próprio de cada fonte.
- **Aviso de truncamento.** Quando o servidor devolve menos feições do que diz
  existir (limite de `maxRecordCount` no ArcGIS, `numberMatched` no WFS), o
  plugin avisa no log e grava a propriedade `truncado` na camada, em vez de
  deixar o corte passar em silêncio.
- **Fontes que dependem de Parquet.** As três fontes do geobr v2
  (favelas, terras quilombolas, locais de votação) são puladas com aviso se não
  houver o driver GDAL Parquet nem o `pyarrow` —
  veja [Instalação](../instalacao.md#opcional-parquet-algoritmos-v2-e-join_censo).
- **CRS.** Tudo sai em **SIRGAS 2000 / EPSG:4674**. Para medir área ou distância,
  reprojete para o fuso UTM correspondente (em Belo Horizonte, EPSG:31983).

## Os oito eixos

| # | Eixo | O que traz |
|---|---|---|
| 1 | **Transportes** | Rodovias federais (DNIT/SNV) e estaduais, ferrovias, trechos rodoviários e ferroviários da BC250 do IBGE e a malha viária urbana do OpenStreetMap (vias + topologia de nós, via Overpass). |
| 2 | **Drenagem e Saneamento** | Rios, bacias hidrográficas, trechos de drenagem e massas d'água (SGB/CPRM e BC250), poços do SIAGAS, hidrografia da ANA e os empreendimentos de água, esgoto e aterro sanitário do IBAMA. |
| 3 | **Demografia** | Limite municipal, setores censitários, áreas de ponderação e favelas/comunidades do IBGE, pelo espelho geobr — a base do cruzamento com o censo (veja o [guia do geobr](geobr.md)). |
| 4 | **Ambiental** | Imóveis do CAR (SICAR), unidades de conservação e embargos do ICMBio, risco geológico do SGB/CPRM, processos minerários da ANM/SIGMINE, autos de infração do IBAMA, biomas, terras indígenas e quilombolas, áreas de risco de desastre e o meio físico do BDIA/IBGE (pedologia, geologia, geomorfologia, vegetação). |
| 5 | **Educação** | Escolas do IBGE/INEP. |
| 6 | **Saúde** | Estabelecimentos de saúde (CNES/IBGE). |
| 7 | **Urbano** | Áreas urbanizadas (2019) e aglomerados subnormais (2010) do IBGE, área densamente edificada da BC250 e a mancha urbana do geobr. |
| 8 | **Político-administrativo** | Sede municipal, bairros, locais de votação e as parcelas certificadas do INCRA/SIGEF (download manual — veja o [guia do SIGEF](sigef.md)). |

O catálogo completo, fonte a fonte, com `id`, protocolo, tipo de filtro e
licença, está em **[Referência › Fontes](../referencia/fontes.md)** — essa página
é gerada do próprio código do plugin, então não envelhece.

## Quando algo falha

O log distingue **`FALHOU`** (o servidor recusou, caiu, ou a camada não abriu) de
**`PULOU`** (nada a fazer: já existe, veio vazia, falta o arquivo manual, falta o
Parquet). Erro de certificado no Windows — *"unable to find issuer certificate"* —
tem página própria em [Referência › Rede e certificados](../referencia/rede.md).
Servidor fora do ar é comum em geosserviços públicos: marque menos fontes de uma
vez e repita mais tarde; o que já entrou no GeoPackage não é rebaixado.
