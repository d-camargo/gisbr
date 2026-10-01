# Recortes regionais e escala estadual

Além do município e da região metropolitana, o painel de diagnóstico trabalha
com recortes maiores: **microrregião**, **mesorregião**, **estado** e
**macrorregião de saúde**. O fluxo é o mesmo do
[guia do painel](diagnostico.md): escolher o recorte na aba *Localização*, marcar
as fontes e clicar em **Carregar selecionadas**. O que muda é o tamanho do
pedido — e, por isso, algumas fontes ficam indisponíveis nas escalas maiores.

## Os seis recortes

Na aba *Localização* há seis radio buttons, em grade de 3 linhas por 2 colunas
(o painel é estreito):

| Recorte | O que você escolhe | O que aparece na lista |
|---|---|---|
| **Município** | UF e município (ou código IBGE) | — |
| **Microrregião** | UF e a microrregião da UF | Municípios da microrregião |
| **Mesorregião** | UF e a mesorregião da UF | Municípios da mesorregião |
| **Região metropolitana** | UF e a RM da UF | Municípios da RM (ver [Regiões metropolitanas](regioes-metropolitanas.md)) |
| **Estado** | Só a UF (o combo de região fica desabilitado) | Todos os municípios da UF, com a contagem |
| **Macrorregião de saúde** | UF e a macrorregião de saúde da UF | Municípios da macrorregião |

Exemplos: *Microrregião de Belo Horizonte* (MG), *Mesorregião Metropolitana de
Belo Horizonte*, *Minas Gerais (MG)* e *Macrorregião de Saúde Centro* (MG).

A **Grande Região do IBGE** (Norte, Nordeste, Sudeste, Sul e Centro-Oeste), que ocupava esse lugar até a versão anterior, **saiu do painel**: o sexto recorte agora é a macrorregião de saúde.

## O que é Macrorregião de saúde

A **macrorregião de saúde** é um agrupamento de **regiões de saúde** definido pelo Ministério da Saúde para o **Planejamento Regional Integrado (PRI)** do SUS. A composição município → região de saúde → macrorregião vem da **base territorial do DataSUS de junho de 2026**. São **121 macrorregiões** no país, **16 em Minas Gerais**, e cada uma fica **sempre dentro de uma única UF** — por isso o combo de UF fica habilitado e lista só as macros daquela UF. Não confundir com a Grande Região do IBGE nem com macrorregião hidrográfica.

!!! note "Meso e microrregião são divisões antigas"
    Em 2017 o IBGE substituiu oficialmente a mesorregião e a microrregião pelas
    **regiões geográficas intermediárias** e **imediatas**. O IBGE ainda publica
    as divisões antigas, e o plugin oferece **meso** e **micro**. Imediata e
    intermediária **ainda não estão no painel**, embora a composição delas já
    venha no arquivo embarcado.

## Nomes de camada

O nome da tabela no GeoPackage é `<fonte>_<sufixo>`. O sufixo depende do
recorte:

| Recorte | Sufixo | Exemplo |
|---|---|---|
| Município | código IBGE de 7 dígitos | `sicar_imoveis_3106200` |
| Microrregião | `micro<id>` | `sicar_imoveis_micro31030` |
| Mesorregião | `meso<id>` | `sicar_imoveis_meso3107` |
| Região metropolitana | `rm<id>` | `sicar_imoveis_rm04501` |
| Estado | `uf<sigla>` | `sicar_imoveis_ufmg` |
| Macrorregião de saúde | `macsaud<id>` | `sicar_imoveis_macsaud3103` |

A **camada de limite** segue o padrão `<tipo>_<id>`: `micro_31030`, `meso_3107`,
`rm_04501`, `uf_mg` e `macsaud_3103`.

No **Estado**, a camada de limite é a **malha municipal** do recorte: um polígono por município, com a coluna `code_muni`. Assim você tem os municípios da UF no projeto. Para recortar as fontes, o plugin usa o **contorno dissolvido** dessa malha (uma só feição), não os 853 polígonos separados.

## Por que algumas fontes ficam desabilitadas

Quanto maior o recorte, maior o pedido. Uma UF inteira pode trazer centenas de
megabytes, milhões de feições, ou bater no limite de resposta do servidor — que
corta o resultado sem avisar. Para não travar o QGIS nem entregar dado truncado,
cada fonte do catálogo declara até que escala ela aguenta.

Na prática, quando o recorte está grande demais para uma fonte:

- a fonte aparece **desmarcada e em cinza** na árvore;
- o **tooltip** mostra o motivo;
- o **log** traz uma linha com as fontes desabilitadas;
- ao voltar para um recorte menor, a fonte **volta a ficar habilitada**.

O motor também confere isso por conta própria: se o carregamento for chamado
fora do painel (por script, por exemplo), a fonte grande demais é **pulada com o
motivo** e nunca é baixada.

### Critério (medido em Minas Gerais, o pior caso)

| Fica até | Fica desabilitada quando... |
|---|---|
| **Regional** (micro, RM, meso, macro de saúde) | passa de ~90 MB ou ~100 mil feições em MG; o servidor corta a resposta abaixo do total; ou é raster/tabular sem caminho medido na UF |
| **Estado** | passa de ~20 MB em MG, ou é ArcGIS com limite baixo de registros por resposta |

### Até onde cada fonte vai

| Nível | Fontes |
|---|---|
| **Só município** | OSM — Vias urbanas (Overpass); OSM — POIs (equipamentos e edificações, Overpass). Milhões de ways numa UF estouram o timeout de 60 s do Overpass. |
| **Até regional** (micro, RM, meso, macro de saúde; desabilitadas no Estado) | SICAR — Imóveis (CAR), que em MG tem cerca de 1,18 milhão de imóveis e o servidor trunca em 10 mil (seriam 118 páginas); SGB/CPRM — Rios (BC250), ~187 mil feições; IBGE — BC250 Trechos de drenagem, ~182 mil feições; IBGE/BDIA — Pedologia (~231 MB), Geologia (~125 MB) e Geomorfologia (~91 MB); ANM/SIGMINE — Processos minerários, ~95 mil feições com limite de 5.000 por resposta, e os quatro pacotes (Requerimento de pesquisa, Licenciamento, Concessão de lavra, Lavra garimpeira); IBAMA — Autos de infração/embargos, ~38 mil feições com limite de 2.000; MapBiomas — Cobertura e uso da terra (Coleção 9), cerca de 650 milhões de pixels em MG a 30 m; IBGE — PAM Lavouras temporárias e permanentes e Censo Agropecuário 2017 (tabelas por município, sem caminho medido para centenas de municípios de uma vez); Sisema-MG — Outorgas de uso de recursos hídricos (58.741 pontos, ~145 MB) |
| **Até Estado** | DNIT — SNV (rodovias federais), ~47 MB em MG; DER-MG — Rodovias estaduais, ~69 MB; IBGE — BC250 Trecho rodoviário, ~46 MB; IBGE/BDIA — Vegetação, ~53 MB; IBGE — Áreas urbanizadas (2019), ~28 MB; SGB/CPRM — Poços (SIAGAS), 61 mil pontos; SGB/CPRM — Bacias hidrográficas, ~26 MB; SGB/CPRM — Risco geológico, ~13 MB; ANA — Hidrografia (limite de 1.000 registros por resposta); Setores censitários, Bairros, Favelas/comunidades e Locais de votação (geobr; os setores de MG têm 79 MB); INCRA/SIGEF — Parcelas certificadas (download manual; o SIGEF exporta por UF); e as fontes estaduais Sisema-MG (ETE, UCs estaduais, UCs municipais, Áreas urbanizadas 2022, Risco de erosão), Siga-GO (Malha viária, Aterros, Captações, UCs estaduais, Suscetibilidade a deslizamentos) e DataGeo-SP (Áreas de risco de inundação) |
| **Todos os recortes** | MInfra — Ferrovias; ICMBio — Embargos e UCs federais; IBGE — BC250 Trecho ferroviário, Massa d'água e Área densamente edificada; IBGE — Aglomerados subnormais (2010); IBAMA — Esgotamento sanitário, Abastecimento de água e Aterro sanitário; geobr — Limite municipal, Áreas de ponderação, Escolas, Estabelecimentos de saúde, Biomas, Unidades de conservação, Terras indígenas, Áreas de risco de desastre, Mancha urbana, Sede municipal e Terras quilombolas; Imagem de satélite (Esri) |

As fontes de escolas e de saúde do geobr são baixadas em nível nacional e
recortadas localmente, o que já vale para qualquer recorte.

## Fontes estaduais

As **fontes estaduais** vêm de infraestruturas de dados espaciais (IDEs) dos
estados e só aparecem habilitadas quando o recorte está **inteiro dentro da UF
da fonte**. Fora disso ficam desabilitadas, com tooltip. É o caso de pedir, por
exemplo, o DER-MG numa microrregião de Sergipe: sem essa regra, a fonte voltaria
vazia.

Entraram **13** fontes estaduais:

| UF | Fonte | Escala máxima |
|---|---|---|
| MG | DER-MG — Rodovias estaduais | Estado |
| MG | Sisema-MG — Áreas urbanizadas (2022) | Estado |
| MG | Sisema-MG — UCs estaduais | Estado |
| MG | Sisema-MG — UCs municipais | Estado |
| MG | Sisema-MG — Estações de tratamento de esgoto (ETE) | Estado |
| MG | Sisema-MG — Outorgas de uso de recursos hídricos | Regional (58.741 pontos, ~145 MB) |
| MG | Sisema-MG — Risco de erosão e movimento de massa | Estado |
| GO | Siga-GO — Malha viária (2024) | Estado |
| GO | Siga-GO — Aterros sanitários e lixões | Estado |
| GO | Siga-GO — Pontos de captação (Saneago) | Estado |
| GO | Siga-GO — UCs estaduais | Estado |
| GO | Siga-GO — Suscetibilidade a deslizamentos | Estado |
| SP | DataGeo-SP — Áreas de risco de inundação (IG 2014) | Estado |
| DF | IDE-DF — Zoneamento e macrozoneamento do PDOT | Estado |
| DF | IDE-DF — Regiões administrativas | Estado |
| DF | IDE-DF — Escolas públicas | Estado |
| RS | SEDUR-RS — Áreas urbanizadas e suscetibilidade à inundação / a movimentos de massa (PDVT Vale do Taquari) | Estado |
| PR | IAT GeoPR — UCs estaduais | Estado |
| PR | DER-PR — Rodovias estaduais | Regional (2.328 feições na UF, acima do limite por resposta do serviço) |

### IDEs avaliadas que ficaram de fora

| IDE | Motivo |
|---|---|
| PR — APP hídrica FBDS (`pr_app_fbds`) | A consulta espacial por município falha por timeout no servidor (29–83 s); fora até houver paginação e serviço estável |
| BA — SEI | Só a cartografia sistemática, que duplica o IBGE |
| BA — INEMA e GeoBahia | Inviáveis: falham no handshake TLS |
| SC — SIGSC | Só limites e hidrografia, que duplicam ANA e IBGE |
| SP — IDE-SP | Só WMS (raster de visualização), sem vetor |
| SP — Emplasa | Só HTTP, sem HTTPS |
| GO — SIEG (portal legado) | Certificado SSL expirado, sem resposta |
| RS — zoneamento de Plano Diretor | Um serviço por município, fora do modelo do catálogo |

## Origem e data da composição regional

A composição município → microrregião → mesorregião → UF → Grande Região vem de
um arquivo **embarcado no plugin**, `gisbr/core/data/divisao_regional.csv`,
gerado a partir da API de localidades do IBGE
(`https://servicodados.ibge.gov.br/api/v1/localidades/municipios`). A extração é
de **2026-09-30**.

Não há acesso à rede em tempo de execução para montar a composição: o arquivo é
lido direto do disco. Para atualizá-lo, rode `tools/gera_divisao_regional.py`.

A composição das macrorregiões de saúde vem de outro arquivo embarcado, `gisbr/core/data/macro_saude.csv`, extraído da base territorial do DataSUS de junho de 2026 (`ftp://ftp.datasus.gov.br/territorio/tabelas/2026/06-base_territorial_jun26.zip`) em **2026-10-01**. Para atualizá-lo, rode `tools/gera_macro_saude.py`.
