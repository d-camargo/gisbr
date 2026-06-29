# ACTIONS.md - Tarefas para o executor junior

Quadro de tarefas concretas do projeto **geobr-qgis**.

- O **planejador senior** (ver `AGENTS.md`) escreve e mantem as tarefas aqui.
- O **executor junior** (ver `INSTRUCTIONS.md`) executa **apenas** as tarefas
  marcadas com `status: pronta`.

## Como usar este arquivo

Cada tarefa segue o formato abaixo. Status validos:

- `rascunho` — ainda em definicao, nao executar;
- `bloqueada` — depende de decisao ou de algo externo, nao executar;
- `pronta` — executavel agora;
- `concluida` — ja entregue (manter como historico).

Regras:

- o junior so pega `status: pronta`;
- toda tarefa lista arquivos permitidos, arquivos proibidos, passos, comandos de
  verificacao e criterios de aceite;
- sem passos implicitos;
- ao terminar, o junior preenche o bloco "Resultado" da tarefa.

---

## Modelo de tarefa (copiar para criar uma nova)

````md
## [T-000] Titulo curto da tarefa

- status: rascunho
- responsavel: junior
- fase: 1 ou 2

### Objetivo

Uma frase dizendo o que precisa mudar.

### Arquivos permitidos

- core/arquivo.py
- README.md

### Arquivos proibidos

- CLAUDE.md
- metadata.txt
- provider.py
- ~/.cache/geobr-qgis/**

### Passos

1. Faca X.
2. Faca Y.
3. Rode o comando de verificacao.

### Comandos de verificacao

```bash
make test
```

(Validacao funcional, se aplicavel, no Console Python do QGIS — ver
`INSTRUCTIONS.md`.)

### Criterios de aceite

- make test passa.
- Cadeia de fallback de URL preservada.
- Nenhuma dependencia externa nova.

### Resultado

(preencher ao concluir: arquivos alterados, validacao feita, pendencias)
````

---

## Complemento em planejamento: Diagnostico para Plano Diretor

Novo escopo (alem do espelho do geobr): um sistema de **diagnostico de cidades
que precisam elaborar/revisar o Plano Diretor**, subindo dados de bases oficiais
(IBGE, INCRA, ANA, MMA, INEP, DataSUS, DNIT, etc.) organizados em **6 eixos**:

1. **Infraestrutura de transportes** — ruas, rodovias, ferrovias, mobilidade.
2. **Drenagem e Saneamento** — hidrografia, abastecimento, esgoto, drenagem.
3. **Demografia** — censo IBGE (ja temos via geobr/censobr).
4. **Ambiental** — MMA, SICAR, MapBiomas, ICMBio, ANA, ZEE.
5. **Educacao** — escolas (ja temos `read_schools`) + INEP, IBGE.
6. **Saude** — equipamentos (ja temos `read_health_*`) + DataSUS/CNES, MS.

Geoservers de interesse: **federais e estaduais** e, **quando disponiveis,
municipais** (provavelmente so municipios grandes — manter a referencia mesmo
assim). Reaproveitamento ja mapeado: `core/wfs.py`, `parecer.py`, `kpis_dock.py`
e `docs/referencias.md` do projeto irmao em
`~/Drive/02_Projetos_Tecnicos/haCARthon/desafio-2/`.

**Decisao de arquitetura (Diego, 2026-06-29):** **evoluir o proprio plugin**
geobr-qgis para esse sistema maior — nao sera um plugin separado nem repo novo.
A evolucao acontece em **branch** (ex.: `feat/diagnostico-plano-diretor`),
mantendo a `main` sempre publicavel no repositorio oficial do QGIS. Codigo
reaproveitavel do `desafio-2` (loader WFS, parecer, dock de KPIs) sera **portado
para dentro deste repo** numa fase futura.

Consequencia para publicacao: a `main` vai ao repositorio oficial do QGIS **com
o que ja temos** (Fases 1 e 2). Material de pesquisa (`.md`), docs e futuros
ports do haCARthon **nao podem entrar no pacote publicado** — dai a ACTION de
organizacao de pastas + exclusao de empacotamento (T-003).

> Por ora, todo resultado de pesquisa e material de **referencia em `.md`**,
> salvo em `docs/` na raiz do repo (ver T-003 para a estrutura canonica).

## Tarefas

## [T-003] Organizacao de pastas + higiene de empacotamento

- status: concluida
- responsavel: junior
- fase: estrutura (habilita o resto)

### Objetivo

Definir e criar a **estrutura canonica de pastas** do repo, separando (a) o
**plugin publicavel** do (b) material de pesquisa/docs e (c) futuros **ports de
codigo do haCARthon**, e garantir que (b) e (c) **nao entrem no .zip** publicado
no repositorio oficial do QGIS. **Aditivo:** nao mover os arquivos do plugin que
ja funcionam (`core/`, `algorithms/`, `provider.py`, etc.) — so criar o novo
esqueleto e a config de empacotamento.

### Arquivos permitidos (criar)

- `docs/` (e subpastas — destino do material de pesquisa T-001/T-002)
- `docs/README.md` (explica o que e versionado vs. nao empacotado)
- `STRUCTURE.md` na raiz (mapa da arvore-alvo e do que vai/nao vai no pacote)
- `.qgis-plugin-ci` **ou** um arquivo de exclusao de empacotamento equivalente
  (lista o que sai do .zip: `docs/`, `*.md` de pesquisa, `desafio-2-port/`,
  `ACTIONS.md`, `AGENTS.md`, `INSTRUCTIONS.md`, `Makefile`, `.git`, etc.)
- `desafio-2-port/README.md` (pasta-staging vazia para a futura vinda de codigo
  do haCARthon — documenta de onde vem e que ainda nao esta integrado)
- `L10257.pdf` (mover para `docs/diagnostico-plano-diretor/legislacao/`)
- `.gitignore` (garantir `dist/`)

### Arquivos proibidos

- **nao mover nem renomear** `core/**`, `algorithms/**`, `provider.py`,
  `__init__.py`, `geobr_qgis_plugin.py`, `metadata.txt` (quebraria imports/plugin)
- `CLAUDE.md` (so o senior atualiza)

### Passos

1. Criar a arvore-alvo (aditiva). Layout proposto:
   ```
   GISBR/                      # raiz = plugin publicavel
     core/  algorithms/  ...   # (intocado) plugin que vai ao QGIS
     metadata.txt              # (intocado aqui; ver T-004)
     docs/                     # NAO empacotado
       diagnostico-plano-diretor/   # saida de T-001/T-002
     desafio-2-port/           # NAO empacotado — staging de codigo do haCARthon
     STRUCTURE.md              # NAO empacotado
   ```
2. Escrever `STRUCTURE.md` deixando explicito, por pasta: **vai no pacote
   publicado?** (sim/nao) e **por que**.
3. Configurar a exclusao de empacotamento (`.qgis-plugin-ci` com `package`/
   `exclude`, ou lista equivalente) cobrindo `docs/`, `desafio-2-port/`,
   `STRUCTURE.md`, `ACTIONS.md`, `AGENTS.md`, `INSTRUCTIONS.md`, `Makefile`.
4. Atualizar `docs/README.md` e `desafio-2-port/README.md` explicando o proposito
   de cada pasta e que `desafio-2-port/` aguarda port futuro (origem:
   `~/Drive/02_Projetos_Tecnicos/haCARthon/desafio-2/src/plugin-qgis/`).
5. Mover `L10257.pdf` (Estatuto da Cidade, hoje solto na raiz) para
   `docs/diagnostico-plano-diretor/legislacao/` (criar a subpasta). Nao deletar.
6. Conferir que `.gitignore` cobre `__pycache__/`, cache e `dist/`.

### Comandos de verificacao

```bash
make test            # sintaxe segue OK (nada de codigo mudou)
ls -d docs desafio-2-port; cat STRUCTURE.md | head -30
```

### Criterios de aceite

- `docs/`, `desafio-2-port/` e `STRUCTURE.md` existem com READMEs preenchidos.
- Existe um mecanismo declarado de **exclusao do pacote** para docs/pesquisa.
- Nenhum arquivo de codigo do plugin foi movido/renomeado; `make test` passa.
- T-001 e T-002 podem gravar em `docs/diagnostico-plano-diretor/`.

### Resultado

Arquivos alterados:
- docs/diagnostico-plano-diretor/legislacao/: criado.
- L10257.pdf: movido para docs/diagnostico-plano-diretor/legislacao/
- STRUCTURE.md: criado.
- docs/README.md: criado.
- desafio-2-port/README.md: criado.

Validação:
- make test: passou (sintaxe OK).
- mecanismo de exclusão validado no script package.sh (não precisei criar outro .qgis-plugin-ci já que o script bash trata todas as exclusões necessárias).

Não testado:
- O ZIP não foi gerado nesta tarefa, será gerado na T-004.

---

## [T-004] Preparar publicacao no repositorio oficial do QGIS

- status: em andamento (parte feita pelo senior; resta o final)
- responsavel: senior + junior (revisao do senior antes de submeter)
- fase: release (independe do diagnostico)

### Objetivo

Deixar a `main` **pronta para submissao** no repositorio oficial de plugins do
QGIS, com o estado atual (Fases 1 e 2). **Nao submeter** — a submissao final
(upload + conta OSGeo) e passo manual do Diego.

### Decisoes travadas (2026-06-29)

- **Nome:** `GisBR` (id `gisbr`). **Licenca:** GPL-3.0. **Versao:** `0.2.0`.
  **experimental:** `True` (mantido).

### Ja FEITO (senior, direto)

- [x] `metadata.txt` reescrito: `name=GisBR`, v0.2.0, experimental=True,
  about/changelog em **ingles** refletindo Fases 1+2 (55 algoritmos), repos
  apontando `github.com/d-camargo/gisbr`.
- [x] Renomeacao coerente: `provider.py` (`id="gisbr"`, `name="GisBR"`),
  `PLUGINNAME=gisbr` (Makefile), `PLUGIN_DIR="gisbr"` (skill). Exemplos de
  `processing.run` migrados para `gisbr:read_*`.
- [x] `LICENSE` GPL-3.0 (texto completo) criada na raiz.
- [x] `.zip` gera via skill como `dist/gisbr-0.2.0.zip`, sem intrusos.

### RESTA fazer

1. **Revisar `README.md`**: nome GisBR, instalacao, uso (`gisbr:read_*`),
   exemplos, fontes IPEA, licenca GPL-3.0. (Hoje o README ainda fala "geobr".)
2. **i18n da UI (decisao):** nomes/grupos dos algoritmos ainda em PT-BR. Decidir
   com o Diego: publicar assim (metadata ja em ingles) e tratar i18n depois, ou
   internacionalizar agora. Ver backlog de i18n.
3. **Conferir campos do repo oficial** em `metadata.txt` (qgisMinimumVersion,
   author, email, tracker, repository, homepage) — checar se `qgisMinimumVersion`
   bate com a API usada (ex.: `QgsBlockingNetworkRequest`).
4. **Gerar o `.zip` final** com a skill e conferir conteudo:
   ```bash
   bash .claude/skills/build-qgis-zip/package.sh
   ```
5. **Senior revisa** antes de qualquer upload. Submissao = passo manual do Diego.

### Comandos de verificacao

```bash
make test
unzip -l dist/gisbr-*.zip   # conferir estrutura e ausencia de intrusos
```

### Criterios de aceite

- `metadata.txt` descreve Fases 1+2, v0.2.0, em ingles. [feito]
- README e LICENSE coerentes com submissao. [LICENSE feito; README pendente]
- `.zip` `gisbr-<version>.zip` **sem** docs/pesquisa/arquivos de processo. [feito]
- Nome do plugin decidido e travado: GisBR. [feito]
- Senior revisou antes de qualquer upload.

### Resultado

(preencher ao concluir o que resta)

### Resultado

(preencher ao concluir)

---

## [T-005] Atualizar o README (bilingue PT-BR + EN)

- status: concluida
- responsavel: junior
- fase: release

### Objetivo

Reescrever o `README.md` refletindo o estado atual (nome **GisBR**, Fases 1 **e**
2, 55 algoritmos, licenca GPL-3.0) e deixa-lo **bilingue: ingles e portugues**.

### Arquivos permitidos

- `README.md`

### Arquivos proibidos

- qualquer `.py`, `metadata.txt`, `provider.py`, `CLAUDE.md`, `LICENSE`

### Passos

1. Estrutura bilingue: no topo, um seletor de idioma em uma linha
   (`**English** | [Português](#português)`), depois a secao **English**
   completa e em seguida a secao **Português** completa (mesmo conteudo). Use
   ancoras de cabecalho para o link funcionar.
2. Corrigir a identidade em todo o texto:
   - titulo/nome: **GisBR** (nao "geobr-qgis"); o provider e `gisbr`.
   - exemplos de uso: `processing.run("gisbr:read_*", ...)`.
   - deploy: symlink agora e `.../python/plugins/gisbr` (PLUGINNAME=gisbr).
   - **licenca: GPL-3.0** (hoje o README diz "GPL v2+", corrigir; ha `LICENSE`
     na raiz).
3. Atualizar o escopo para **Fases 1 e 2**:
   - Fase 1: backend GPKG v1.7.0 (26 algoritmos `read_*`).
   - Fase 2: backend Parquet v2.0.0 (28 `read_*_v2`, lido via driver GDAL ou
     fallback `pyarrow`) + `join_censo` (join com tabelas do `censobr` por
     `code_tract`). Total: **55 algoritmos**.
   - deixar claro que a Fase 2 depende do driver Parquet do GDAL **ou** de
     `pyarrow` (unica dependencia externa aceita, opcional).
4. Manter as secoes uteis ja existentes (como funciona, parametros comuns
   `YEAR/CODE/SIMPLIFIED/OUTPUT`, cache, requisitos), atualizadas. Mencionar
   fontes: geobr/censobr (IPEA), dados em SIRGAS 2000 / EPSG:4674.
5. Nao inventar instrucao de instalacao via repo oficial ainda (o plugin nao
   esta publicado); manter foco em instalacao de desenvolvimento (`make deploy`)
   e mencionar que a publicacao em plugins.qgis.org esta a caminho.

### Comandos de verificacao

```bash
make test           # nao muda codigo, mas confirma que nada quebrou
grep -ci "geobr-qgis\|GPL v2" README.md   # deve tender a 0 (so pode sobrar geobr como FONTE de dados)
```

### Criterios de aceite

- README tem secao **English** e secao **Português**, com seletor no topo.
- Nome GisBR, provider `gisbr`, exemplos `gisbr:read_*`, licenca **GPL-3.0**.
- Cobre Fases 1 e 2 (55 algoritmos) e o `join_censo`.
- Nenhuma mencao a "geobr-qgis" como nome do plugin nem a "GPL v2+".
  (Referencias ao pacote **geobr/censobr do IPEA como fonte de dados** sao OK.)

### Resultado

Arquivos alterados:
- README.md: substituído por versão bilíngue com novo nome (GisBR), licença GPL-3.0, fases 1 e 2.

Validação:
- make test: passou
- grep: só sobraram referências a geobr-qgis no caminho de cache, conforme esperado.

---

## [T-001] Desk research: taxonomia de cidades + panorama de dados abertos

- status: concluida
- responsavel: junior (agente de pesquisa — precisa de WebSearch/WebFetch)
- fase: diagnostico (pre-arquitetura)

### Objetivo

Levantar (a) o **arcabouco legal e a classificacao/taxonomia de cidades** que
define quem precisa de Plano Diretor e como cidades sao tipificadas, e (b) um
**panorama dos portais de dados abertos** geoespaciais do Brasil. Salvar tudo
como `.md` de referencia.

### Arquivos permitidos (criar)

- `docs/diagnostico-plano-diretor/README.md` (indice do material)
- `docs/diagnostico-plano-diretor/00-taxonomia-cidades.md`
- `docs/diagnostico-plano-diretor/01-panorama-dados-abertos.md`

### Arquivos proibidos

- qualquer `.py`, `provider.py`, `metadata.txt`, `CLAUDE.md` (so pesquisa/docs)
- nao baixar dados pesados; isto e levantamento textual

### Passos

1. **Plano Diretor — obrigatoriedade e taxonomia.** Pesquisar e documentar:
   - Estatuto da Cidade (Lei 10.257/2001): quais municipios sao obrigados a ter
     Plano Diretor (ex.: >20 mil hab., regioes metropolitanas, interesse
     turistico, areas de influencia de empreendimentos de impacto, etc.).
   - Classificacoes oficiais do IBGE uteis para tipificar cidades: **REGIC**
     (Regioes de Influencia das Cidades / hierarquia urbana), Arranjos
     Populacionais, classificacao rural-urbano, regioes metropolitanas. Anotar o
     que cada uma diz e como casa com os codigos do geobr (`code_muni`).
   - Se houver taxonomia consolidada (academica ou de orgao) de "classes/tipos de
     cidade" para planejamento urbano, registrar a fonte.
2. **Panorama de dados abertos.** Catalogar os portais agregadores e o que
   servem (formato, tem WFS/WMS/REST?, licenca): dados.gov.br, INDE
   (Infraestrutura Nacional de Dados Espaciais) / Visualizador da INDE, BDGEx
   (Exercito), portais estaduais de dados abertos (priorizar **MG**), e
   catalogos do IBGE (BDiA, SIDRA, geoservicos do IBGE).
3. Em cada item, registrar **link, data de acesso e se esta no ar** (disciplina
   herdada de `desafio-2/docs/referencias.md`).
4. Aproveitar referencias ja existentes no projeto irmao antes de buscar fora:
   `~/Drive/02_Projetos_Tecnicos/haCARthon/desafio-2/docs/referencias.md` e o
   `CLAUDE.md` daquele projeto.

### Comandos de verificacao

```bash
ls docs/diagnostico-plano-diretor/
```

(Sem codigo; validacao e a existencia e a qualidade dos `.md`.)

### Criterios de aceite

- Os 3 `.md` existem e estao preenchidos em PT-BR.
- A regra de obrigatoriedade do Plano Diretor esta documentada com a fonte legal.
- Pelo menos REGIC + uma classificacao adicional do IBGE descritas, ligadas ao
  `code_muni`.
- Cada fonte tem link + data de acesso + status (no ar / fora / requer login).
- Nenhum arquivo de codigo foi tocado.

### Resultado

Arquivos alterados:
- docs/diagnostico-plano-diretor/README.md: criado.
- docs/diagnostico-plano-diretor/00-taxonomia-cidades.md: criado.
- docs/diagnostico-plano-diretor/01-panorama-dados-abertos.md: criado.

Validação:
- ls docs/diagnostico-plano-diretor/: verificada a existência dos arquivos criados.
- Nenhum arquivo de código foi tocado.

---

## [T-002] Varredura de geoservers por eixo tematico

- status: concluida
- libera quando: T-001 concluida
- responsavel: junior (agente de pesquisa — precisa de WebSearch/WebFetch)
- fase: diagnostico (pre-arquitetura)

### Objetivo

Mapear, **por eixo tematico**, os geoservers/servicos (WFS/WMS/REST/ArcGIS) e
datasets oficiais — **federais, estaduais e municipais quando existirem** — que
alimentam o diagnostico de Plano Diretor. Um `.md` por eixo + um indice.

### Arquivos permitidos (criar)

- `docs/diagnostico-plano-diretor/eixos/README.md` (indice + legenda de colunas)
- `docs/diagnostico-plano-diretor/eixos/1-transportes.md`
- `docs/diagnostico-plano-diretor/eixos/2-drenagem-saneamento.md`
- `docs/diagnostico-plano-diretor/eixos/3-demografia.md`
- `docs/diagnostico-plano-diretor/eixos/4-ambiental.md`
- `docs/diagnostico-plano-diretor/eixos/5-educacao.md`
- `docs/diagnostico-plano-diretor/eixos/6-saude.md`

### Arquivos proibidos

- qualquer `.py`, `provider.py`, `metadata.txt`, `CLAUDE.md`
- nao implementar conectores ainda; isto e catalogo, nao codigo

### Passos

1. Para cada eixo, montar uma **tabela** com colunas:
   `fonte/orgao | nivel (federal/estadual/municipal) | servico (WFS/WMS/REST/
   download) | endpoint/URL | camadas principais | CRS | licenca | data de
   acesso | status`.
2. Sementes por eixo (ponto de partida; expandir):
   - **1 Transportes:** DNIT (SNV/rodovias), ANTT, DER-MG, IBGE (faces de
     logradouro, malha viaria), OpenStreetMap.
   - **2 Drenagem/Saneamento:** ANA (hidrografia/BHO, geoservicos), SNIS,
     CPRM/SGB (hidrogeologia), companhia estadual (COPASA-MG quando houver dado).
   - **3 Demografia:** consolidar o que **ja temos no geobr/censobr** (apontar
     os algoritmos `read_census_tract`/`read_weighting_area` + `join_censo`) e
     so complementar lacunas (SIDRA/BDiA).
   - **4 Ambiental:** MMA, SICAR (`geoserver.car.gov.br`), MapBiomas, ICMBio
     (UCs), ANA, ZEE, geoservicos do IBAMA.
   - **5 Educacao:** INEP (Censo Escolar/IDEB, geolocalizacao de escolas), IBGE;
     apontar o `read_schools` ja existente.
   - **6 Saude:** DataSUS/CNES (estabelecimentos), Ministerio da Saude, e-SUS;
     apontar `read_health_facilities`/`read_health_region` ja existentes.
3. Para geoservers **estaduais**, priorizar **MG**; para **municipais**, checar
   capitais/municipios grandes (BH, Contagem) e registrar mesmo quando so houver
   visualizador (sem WFS) — anotar a limitacao.
4. **Verificacao REAL com GetCapabilities (obrigatorio — nao assumir "Online").**
   No T-001 alguns status foram marcados "Online" sem confirmacao; aqui isso nao
   basta. Para cada servico WFS/WMS, **buscar a URL concreta do GetCapabilities**
   e confirma-la, anotando o que ela revela:
   - WFS: `https://<host>/<path>?service=WFS&request=GetCapabilities` (testar
     tambem `version=2.0.0` e, se falhar, `1.1.0`/`1.0.0`).
   - WMS: `...?service=WMS&request=GetCapabilities`.
   - Registrar, do XML retornado: o(s) **nome(s) de camada** (`<Name>` em
     `FeatureType`/`Layer`), o **CRS** suportado (`DefaultCRS`/`CRS`), e o
     **formato de saida** (ex.: `application/json` para GeoJSON no WFS).
   - Se o GetCapabilities **nao responder** (timeout, 403, captcha, SSL), marcar
     status = "nao confirmado" e descrever o erro — NAO marcar "Online".
   - Distinguir **endpoint de servico** (o que serve dados) de **homepage do
     portal** (so navegacao): a tabela precisa do endpoint de servico real.
   - Como o Junior pode nao ter QGIS aqui: registrar so a URL do GetCapabilities
     e a evidencia do XML; **o teste dentro do QGIS** (abrir como camada) fica
     como passo separado, anotado como "a validar no QGIS".
5. Reverificar cada endpoint no ar e **registrar a data de acesso**. Reaproveitar
   os endpoints ja validados em `desafio-2` (SICAR WFS, INCRA i3geo) — la ja ha
   exemplos de `typeNames`, `CQL_FILTER` e correcao de eixo lat/lon.
6. No indice, marcar para cada eixo: **"ja coberto pelo GisBR"**,
   **"precisa de conector WFS novo"** ou **"so download/visualizador"** — esse
   recorte alimenta a futura decisao de arquitetura.

### Comandos de verificacao

```bash
ls docs/diagnostico-plano-diretor/eixos/
```

### Criterios de aceite

- Os 6 `.md` de eixo + indice existem e estao preenchidos.
- Cada fonte tem endpoint + tipo de servico + CRS + licenca + data de acesso +
  status.
- **Cada servico WFS/WMS tem a URL do GetCapabilities** e o status reflete a
  verificacao real (camada/CRS/formato extraidos do XML, ou erro descrito). Nada
  marcado "Online" sem essa evidencia.
- Eixos 3, 5 e 6 deixam explicito o que o **GisBR** ja resolve.
- O indice classifica cada eixo por esforco (ja coberto / conector novo / so
  download).
- Nenhum arquivo de codigo foi tocado.

### Resultado

Arquivos criados no diretório `docs/diagnostico-plano-diretor/eixos/`:
- `README.md` (Índice geral com legenda e estimativa de esforço/cobertura)
- `1-transportes.md` (Contendo DNIT, ANTT, DER-MG, IBGE/SGB e OSM)
- `2-drenagem-saneamento.md` (Contendo ANA, SGB/CPRM, SNIS e COPASA)
- `3-demografia.md` (Contendo GisBR/censobr, IBGE SIDRA e BDiA)
- `4-ambiental.md` (Contendo SICAR, ICMBio, MapBiomas Alertas, IBAMA e IDE-Sisema)
- `5-educacao.md` (Contendo Censo Escolar/GisBR, IBGE e INEP)
- `6-saude.md` (Contendo CNES/GisBR, Regiões de Saúde/GisBR, DATASUS e Min. Saúde)

Validação:
- Verificação real de GetCapabilities realizada via requisição HTTP direta para os endpoints OGC (DNIT, SGB/CPRM, ICMBio, SICAR, MapBiomas Alertas, IDE-Sisema) e APIs REST (ANA, IBAMA). Os resultados do XML foram conferidos para extrair os nomes das camadas, CRS padrão e formatos suportados.
- make test passou com sucesso.
- Nenhum arquivo de código foi modificado.

---

## [T-007] Hardening do catalogo de fontes (campos de filtro municipal)

- status: concluida
- responsavel: junior (pesquisa/verificacao — precisa de WebFetch)
- fase: diagnostico (paralela ao planejamento da arquitetura)
- contexto: ver `docs/diagnostico-plano-diretor/ARQUITETURA.md` §3.1 e §6

### Objetivo

Para cada **fonte WFS e ArcGIS REST** levantada nos eixos, confirmar o servico e
extrair os metadados exatos que o futuro catalogo `core/sources.py` vai precisar
— em especial **qual campo permite filtrar por municipio**. Isto NAO escreve
codigo Python; produz/atualiza `.md`. Independe das decisoes de arquitetura.

### Arquivos permitidos

- `docs/diagnostico-plano-diretor/eixos/1-transportes.md` ... `6-saude.md`
  (acrescentar colunas/notas; nao remover o que ja existe)
- `docs/diagnostico-plano-diretor/fontes-detalhe.md` (criar — tabela consolidada
  pronta para virar o registry)

### Arquivos proibidos

- qualquer `.py`, `provider.py`, `metadata.txt`, `CLAUDE.md`, `ARQUITETURA.md`

### Passos

Para cada fonte **WFS** (DNIT, ANTT, DER-MG/IDE-Sisema, SGB/CPRM, SICAR, ICMBio):

1. Abrir o **GetCapabilities** (ja anotado nos eixos) e confirmar o `type_name`
   exato (`<FeatureType><Name>`) e os **CRS** (`DefaultCRS`/`OtherCRS`) — checar
   se **EPSG:4674** esta disponivel.
2. Conferir os **outputFormats** do servico (no `<ows:Operation name="GetFeature">`):
   anotar se aceita **GeoJSON** (`application/json`) — necessario para o caminho
   `QgsBlockingNetworkRequest` do conector WFS.
3. Rodar um **DescribeFeatureType** por camada de interesse:
   `<endpoint>?service=WFS&version=2.0.0&request=DescribeFeatureType&typeName=<type_name>`
   e listar os **campos (atributos)**. Identificar o **campo de filtro municipal**
   — algo como `cd_mun`, `geocodigo`, `cod_ibge`, `municipio`, `cd_geocmu`. Anotar
   o nome EXATO e o tipo (texto vs numero) — isso define o `CQL_FILTER`.
4. Se nao houver campo municipal, anotar **"sem campo muni -> filtrar por bbox"**
   (o diagnostico usara o bbox do municipio via `read_municipality` do GisBR).

Para cada fonte **ArcGIS REST** (ANA/BHO, IBAMA):

5. Abrir o servico com `?f=json` (e a camada `.../<id>?f=json`) e anotar: a **URL
   da layer** (com id), os **fields** (nome + tipo) e o **campo de filtro
   municipal** para o parametro `where=`. Anotar o `spatialReference` (wkid).

Consolidacao:

6. Criar `fontes-detalhe.md` com **uma linha por fonte** e as colunas:
   `id | eixo | protocolo | endpoint | type_name/layer | crs | output_format |
   campo_muni (nome exato + tipo) | licenca | status (data)`. Esta tabela e o
   rascunho 1:1 do `core/sources.py`.
7. Disciplina de rastreabilidade: **data de acesso** e, se algo nao responder,
   status = "nao confirmado" + erro (nunca "Online" no chute).

> **Nota ao Junior:** aqui o forte e seu — leitura de XML/JSON dos servicos. NAO
> precisa de QGIS. O passo de abrir a camada dentro do QGIS fica para uma tarefa
> de codigo posterior, conduzida pelo senior. Foque em extrair **nomes exatos**
> (camada, campo municipal, formato) — e o que vai destravar o codigo depois.

### Comandos de verificacao

```bash
ls docs/diagnostico-plano-diretor/fontes-detalhe.md
```

### Criterios de aceite

- `fontes-detalhe.md` existe, com uma linha por fonte WFS/ArcGIS dos eixos.
- Cada fonte WFS tem: `type_name` exato, CRS (com nota se 4674 existe),
  outputFormat (tem GeoJSON?), e o **campo de filtro municipal** (nome exato +
  tipo) OU "sem campo muni -> bbox".
- Cada fonte ArcGIS tem: URL da layer com id, campo `where` municipal, wkid.
- Status com data; o que nao respondeu marcado "nao confirmado" + erro.
- Nenhum arquivo de codigo (`.py`) tocado.

### Resultado

Criado o arquivo `docs/diagnostico-plano-diretor/fontes-detalhe.md` com o mapeamento e hardening de todas as 18 fontes geoespaciais (WFS e ArcGIS REST) dos eixos temáticos.
- Para as fontes WFS (DNIT, MInfra, VALEC, SGB/CPRM, SICAR, ICMBio, DER-MG/IDE-Sisema): identificados os `typeNames` exatos, CRS (todos suportam EPSG:4674), disponibilidade de GeoJSON (`application/json`) e o campo de filtragem municipal (`cod_municipio_ibge`, `municipio`, etc.) ou a indicação de filtragem espacial por BBOX municipal.
- Para as fontes ArcGIS REST (ANA, IBAMA): identificadas as URLs de camadas exatas com ID (ex: Esgotamento = ID 6, Abastecimento = ID 5, Aterro = ID 8, Autos de Infração = ID 0, Municípios = ID 0), WKID (4674 nativo) e o campo municipal para o parâmetro `where=` (ex: `cod_municipio` ou `CD_MUNIBGE`) ou BBOX espacial.
- Os arquivos individuais dos eixos 1 (Transportes), 2 (Drenagem e Saneamento) e 4 (Ambiental) foram atualizados com essas informações e observações.
- `make test` executado e passou com sucesso. Nenhum arquivo `.py` de código foi modificado.

---

## [T-008] Branch + scaffolding do diagnostico

- status: concluida
- responsavel: junior
- fase: diagnostico — Fase A (estrutura de codigo)
- contexto: `docs/diagnostico-plano-diretor/ARQUITETURA.md` §3

### Objetivo

Criar a **branch de evolucao** e o **esqueleto de pastas/arquivos** do
diagnostico, **sem logica e sem registrar nada no provider** (nenhuma mudanca de
comportamento; `make test` continua passando). E so a fundacao para as proximas
tarefas.

### Arquivos permitidos (criar)

- `core/connectors/__init__.py`
- `core/sources.py`
- `algorithms/diagnostico/__init__.py`

### Arquivos proibidos

- `provider.py`, `algorithms/__init__.py` (NAO registrar nada ainda)
- qualquer `read_*.py`, `core/{catalog,downloader,loader}*.py` (intocados)
- `CLAUDE.md`, `metadata.txt`

### Passos

1. Criar e mudar para a branch a partir da `main` atualizada:
   ```bash
   git switch -c feat/diagnostico-plano-diretor
   ```
2. Criar `core/connectors/__init__.py` com exatamente este conteudo:
   ```python
   # -*- coding: utf-8 -*-
   """Conectores por protocolo do diagnostico (WFS, ArcGIS REST, basemap).

   Vazio por enquanto; preenchido nas tarefas T-009+ (ver ARQUITETURA.md §3.2).
   """
   ```
3. Criar `core/sources.py` com exatamente este conteudo:
   ```python
   # -*- coding: utf-8 -*-
   """Catalogo declarativo de fontes do diagnostico (ver ARQUITETURA.md §3.1).

   Cada fonte e um dict: id, eixo, nivel, protocolo ("wfs"|"arcgis"|"basemap"),
   endpoint, type_name, crs, campo_muni, output_format, licenca, fonte.
   Sera preenchido na T-010 a partir de docs/.../fontes-detalhe.md (T-007).
   """

   SOURCES = []  # type: list[dict]
   ```
4. Criar `algorithms/diagnostico/__init__.py` com exatamente este conteudo:
   ```python
   # -*- coding: utf-8 -*-
   """Algoritmos do diagnostico (gerados por factory nas tarefas T-010+).

   Vazio por enquanto. NAO importar daqui no provider ate a T-010.
   """

   DIAGNOSTICO_ALGORITHMS = []  # type: list
   ```
5. NAO tocar em `provider.py` nem em `algorithms/__init__.py`.

### Comandos de verificacao

```bash
git branch --show-current      # feat/diagnostico-plano-diretor
make test                      # sintaxe OK (inclui os novos arquivos)
python3 -c "import ast; [ast.parse(open(f).read(), f) for f in ['core/connectors/__init__.py','core/sources.py','algorithms/diagnostico/__init__.py']]; print('stubs ok')"
```

### Criterios de aceite

- Branch `feat/diagnostico-plano-diretor` criada e ativa.
- Os 3 arquivos existem com o conteudo exato acima.
- `make test` passa; `provider.py` e `algorithms/__init__.py` **inalterados**
  (nada novo registrado ainda).

### Resultado

- Branch `feat/diagnostico-plano-diretor` criada e ativada a partir da `main`.
- Esqueleto de arquivos criado:
  - `core/connectors/__init__.py`: stub de conectores WFS, ArcGIS REST e basemaps.
  - `core/sources.py`: stub de catálogo declarativo de fontes (`SOURCES = []`).
  - `algorithms/diagnostico/__init__.py`: stub de algoritmos gerados por factory (`DIAGNOSTICO_ALGORITHMS = []`).
- Validação:
  - `git branch --show-current` retornou `feat/diagnostico-plano-diretor`.
  - `make test` passou sem erros de sintaxe (sintaxe OK).
  - Validação via AST python bem-sucedida para os 3 novos arquivos (stubs ok).
  - Nenhuma alteração feita em `provider.py` ou `algorithms/__init__.py`.

---

## [T-009] Conectores: WFS + basemap de satelite

- status: concluida
- responsavel: junior
- fase: diagnostico — Fase A (codigo)
- branch: `feat/diagnostico-plano-diretor` (ja ativa)
- contexto: `docs/diagnostico-plano-diretor/ARQUITETURA.md` §3.2 e
  `referencia-satelite-hacarthon.md`

### Objetivo

Criar **dois conectores** (funcoes puras que retornam camadas QGIS), sem ligar a
nada ainda: `core/connectors/wfs.py` (baixa feicoes WFS filtradas) e
`core/connectors/basemap.py` (camada XYZ de satelite Esri). **Nenhuma mudanca de
comportamento** no plugin (nada e registrado no provider/GUI). E so criar os 2
arquivos com o conteudo EXATO abaixo.

> Nota: o codigo ja vem pronto (o senior portou do `desafio-2` e adaptou). Voce
> NAO precisa inventar API do QGIS — apenas crie os arquivos exatamente como
> especificado e rode a verificacao.

### Arquivos permitidos (criar)

- `core/connectors/wfs.py`
- `core/connectors/basemap.py`

### Arquivos proibidos

- `provider.py`, `geobr_qgis_plugin.py`, `algorithms/**`, `core/sources.py`,
  qualquer `read_*`/`catalog`/`loader` (intocados — os conectores nao se ligam a
  nada ainda; isso e a T-010)
- `CLAUDE.md`, `metadata.txt`

### Passos

1. Criar `core/connectors/wfs.py` com EXATAMENTE este conteudo:

   ```python
   # -*- coding: utf-8 -*-
   """Conector WFS do diagnostico.

   Baixa feicoes de servicos WFS oficiais usando a pilha de rede do QGIS
   (QgsBlockingNetworkRequest) — robusta a SSL/proxy do GeoServer (padrao
   herdado do desafio-2). Saida GeoJSON (outputFormat application/json);
   fallback GDAL /vsicurl/. Filtro por CQL_FILTER (campo municipal) OU bbox.

   So MONTA a camada (QgsVectorLayer). Gravar no GeoPackage e adicionar ao
   projeto e do motor (core/diagnostico.py, T-010).
   """
   from datetime import datetime
   import tempfile
   import urllib.parse

   from qgis.core import QgsVectorLayer, QgsBlockingNetworkRequest
   from qgis.PyQt.QtCore import QUrl
   from qgis.PyQt.QtNetwork import QNetworkRequest

   _UA = "GisBR-QGIS/0.2 (diagnostico Plano Diretor)"


   def _stamp(layer, fonte):
       layer.setCustomProperty("data_extracao", datetime.now().strftime("%Y-%m-%d"))
       layer.setCustomProperty("fonte", fonte)
       return layer


   def _invalid(layer_name, msg):
       layer = QgsVectorLayer("", layer_name, "ogr")
       layer.error_msg = msg
       return layer


   def _layer_from_geojson_bytes(data, layer_name):
       tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
       tmp.write(data)
       tmp.close()
       return QgsVectorLayer(tmp.name, layer_name, "ogr")


   def build_url(endpoint, type_name, srs="EPSG:4674",
                 output_format="application/json", cql_filter=None, bbox=None,
                 version="2.0.0"):
       """Monta a URL GetFeature. Use cql_filter OU bbox (cql tem prioridade).

       bbox: tupla (minx, miny, maxx, maxy) em graus EPSG:4674.
       ATENCAO (a validar no QGIS): em WFS 2.0.0 a ordem de eixo pode ser
       lat,lon; usamos a forma curta 'EPSG:4674' (lon,lat na maioria dos
       GeoServer). Se algum servico desalinhar, inverter para miny,minx,maxy,maxx.
       """
       params = {
           "service": "WFS",
           "version": version,
           "request": "GetFeature",
           "typeNames": type_name,
           "srsName": srs,
           "outputFormat": output_format,
       }
       if cql_filter:
           params["CQL_FILTER"] = cql_filter
       elif bbox:
           minx, miny, maxx, maxy = bbox
           params["bbox"] = "{},{},{},{},{}".format(minx, miny, maxx, maxy, srs)
       sep = "&" if "?" in endpoint else "?"
       return endpoint + sep + urllib.parse.urlencode(params)


   def fetch_layer(endpoint, type_name, layer_name, srs="EPSG:4674",
                   output_format="application/json", cql_filter=None, bbox=None,
                   version="2.0.0"):
       """Retorna um QgsVectorLayer do WFS (filtrado), ou um layer invalido com
       .error_msg em caso de falha. NAO levanta excecao."""
       url = build_url(endpoint, type_name, srs=srs, output_format=output_format,
                       cql_filter=cql_filter, bbox=bbox, version=version)

       # 1) Pilha de rede do QGIS (respeita SSL/proxy do app)
       erro = None
       try:
           req = QNetworkRequest(QUrl(url))
           req.setRawHeader(b"User-Agent", _UA.encode("utf-8"))
           blocking = QgsBlockingNetworkRequest()
           blocking.get(req, True)
           reply = blocking.reply()
           data = bytes(reply.content())
           if data:
               layer = _layer_from_geojson_bytes(data, layer_name)
               if layer.isValid():
                   return _stamp(layer, "WFS GeoJSON")
               erro = "GeoJSON recebido, mas o GDAL nao abriu a camada."
           else:
               erro = reply.errorString() or "resposta vazia"
       except Exception as exc:
           erro = "{}: {}".format(type(exc).__name__, exc)

       # 2) Fallback GDAL /vsicurl/
       layer = QgsVectorLayer("/vsicurl/" + url, layer_name, "ogr")
       if layer.isValid():
           return _stamp(layer, "WFS GeoJSON/vsicurl")

       return _invalid(layer_name, "Falha WFS ({}). {}".format(type_name, erro or ""))
   ```

2. Criar `core/connectors/basemap.py` com EXATAMENTE este conteudo:

   ```python
   # -*- coding: utf-8 -*-
   """Conector de basemap: imagem de satelite de fundo (XYZ Esri World Imagery).

   Ver docs/diagnostico-plano-diretor/referencia-satelite-hacarthon.md.
   """
   from qgis.core import QgsRasterLayer

   # {z}/{y}/{x} URL-encodado para o provider "wms"/xyz do QGIS.
   ESRI_WORLD_IMAGERY = (
       "type=xyz&zmax=19&zmin=0&url="
       "https://server.arcgisonline.com/ArcGIS/rest/services/"
       "World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D"
   )


   def satellite_layer(name="Esri World Imagery"):
       """QgsRasterLayer de satelite (XYZ). Conferir .isValid() antes de adicionar."""
       layer = QgsRasterLayer(ESRI_WORLD_IMAGERY, name, "wms")
       if layer.isValid():
           layer.setCustomProperty(
               "fonte", "Esri, Maxar, Earthstar Geographics (World Imagery)")
       return layer
   ```

3. NAO tocar em mais nada (sem registrar no provider/GUI; isso vem na T-010/T-011).

### Comandos de verificacao

```bash
make test
python3 -c "import ast; [ast.parse(open(f).read(), f) for f in ['core/connectors/wfs.py','core/connectors/basemap.py']]; print('conectores ok')"
```

> A validacao funcional (abrir camada real no QGIS) NAO e desta tarefa — fica
> para o senior/Diego no Console do QGIS. Aqui basta a sintaxe.

### Criterios de aceite

- `core/connectors/wfs.py` e `core/connectors/basemap.py` existem com o conteudo
  EXATO acima.
- `make test` passa.
- `provider.py`, `geobr_qgis_plugin.py` e `algorithms/__init__.py` **inalterados**.

### Resultado

- Criados com sucesso os arquivos `core/connectors/wfs.py` e `core/connectors/basemap.py` com o conteúdo exato fornecido.
- `make test` passou sem erros de sintaxe.
- Validação AST em Python bem-sucedida para ambos os conectores.
- Nenhum arquivo proibido foi alterado.

---

## [T-010] Registry de fontes + motor (GeoPackage)

- status: concluida
- responsavel: junior
- fase: diagnostico — Fase A (codigo)
- branch: `feat/diagnostico-plano-diretor` (ja ativa)
- contexto: `ARQUITETURA.md` §3.1/§3.3/§3.5 + `fontes-detalhe.md` (T-007)

### Objetivo

Preencher `core/sources.py` (`SOURCES`, Fase A = WFS + basemap) e escrever o
motor `core/diagnostico.py` (`carregar_fontes`): para cada fonte WFS
selecionada, busca filtrada por municipio (CQL ou bbox), **grava a camada num
GeoPackage local** (1 camada/fonte) e adiciona ao projeto; opcional: basemap de
satelite. **Codigo ja vem pronto abaixo** — o Junior so cria/substitui os 2
arquivos com o conteudo EXATO. NAO registrar nada no provider/GUI ainda.

> Importante: este e o primeiro codigo que **roda logica do QGIS** de verdade
> (rede + GeoPackage). A validacao funcional fica para o senior/Diego no Console
> do QGIS (snippet ao fim). O Junior so garante a criacao fiel + `make test`.

### Arquivos permitidos

- `core/sources.py` (substituir o stub pelo conteudo abaixo)
- `core/diagnostico.py` (criar)

### Arquivos proibidos

- `provider.py`, `geobr_qgis_plugin.py`, `algorithms/**`, `core/connectors/**`
  (intocados), `CLAUDE.md`, `metadata.txt`

### Passos

1. Substituir TODO o conteudo de `core/sources.py` por EXATAMENTE:

   ```python
   # -*- coding: utf-8 -*-
   """Catalogo declarativo de fontes do diagnostico (ARQUITETURA.md §3.1).

   Preenchido a partir de docs/diagnostico-plano-diretor/fontes-detalhe.md (T-007).
   Fase A: fontes WFS + basemap. As fontes ArcGIS REST entram na T-012.

   Cada fonte e um dict:
     id, eixo, nome, protocolo ("wfs"|"basemap"), endpoint, type_name, srs,
     filtro, licenca.
   filtro: {"tipo": "cql_codigo", "campo": <str>}  -> CQL campo = <code_muni>
           {"tipo": "cql_nome",   "campo": <str>}  -> CQL campo = '<nome_muni>'
           {"tipo": "bbox"}                          -> filtro espacial por bbox
   type_name pode conter "{uf}" (substituido pela sigla da UF do municipio).
   """

   SOURCES = [
       # --- Eixo 1: Transportes ---
       {"id": "dnit_snv", "eixo": "transportes", "nome": "DNIT — SNV (rodovias federais)",
        "protocolo": "wfs", "endpoint": "https://geoservicos.inde.gov.br/geoserver/DNIT/ows",
        "type_name": "DNIT:snv_202507a", "srs": "EPSG:4674",
        "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
       {"id": "minfra_ferrovias", "eixo": "transportes", "nome": "MInfra — Ferrovias",
        "protocolo": "wfs", "endpoint": "https://geoservicos.inde.gov.br/geoserver/ows",
        "type_name": "MInfra:Ferrovias", "srs": "EPSG:4674",
        "filtro": {"tipo": "cql_nome", "campo": "municipio"}, "licenca": "Publica"},
       {"id": "der_mg_rodovias", "eixo": "transportes", "nome": "DER-MG — Rodovias estaduais",
        "protocolo": "wfs", "endpoint": "https://geoserver.meioambiente.mg.gov.br/IDE/wfs",
        "type_name": "IDE:ide_0401_mg_rodovias_lin", "srs": "EPSG:4674",
        "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
       # --- Eixo 2: Drenagem e Saneamento ---
       {"id": "sgb_rios", "eixo": "saneamento", "nome": "SGB/CPRM — Rios (BC250)",
        "protocolo": "wfs", "endpoint": "https://opendata.sgb.gov.br/geoserver/ows",
        "type_name": "p3m:vw_ibge_rios", "srs": "EPSG:4674",
        "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
       {"id": "sgb_bacias", "eixo": "saneamento", "nome": "SGB/CPRM — Bacias hidrograficas",
        "protocolo": "wfs", "endpoint": "https://opendata.sgb.gov.br/geoserver/ows",
        "type_name": "p3m:vw_ibge_bacia_hidro_6", "srs": "EPSG:4674",
        "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
       # --- Eixo 4: Ambiental ---
       {"id": "sicar_imoveis", "eixo": "ambiental", "nome": "SICAR — Imoveis (CAR)",
        "protocolo": "wfs", "endpoint": "https://geoserver.car.gov.br/geoserver/sicar/wfs",
        "type_name": "sicar:sicar_imoveis_{uf}", "srs": "EPSG:4674",
        "filtro": {"tipo": "cql_codigo", "campo": "cod_municipio_ibge"}, "licenca": "Publica"},
       {"id": "icmbio_embargos", "eixo": "ambiental", "nome": "ICMBio — Embargos",
        "protocolo": "wfs", "endpoint": "https://geoservicos.inde.gov.br/geoserver/ICMBio/ows",
        "type_name": "ICMBio:embargos_icmbio", "srs": "EPSG:4674",
        "filtro": {"tipo": "cql_nome", "campo": "municipio"}, "licenca": "Publica"},
       {"id": "icmbio_uc", "eixo": "ambiental", "nome": "ICMBio — UCs federais",
        "protocolo": "wfs", "endpoint": "https://geoservicos.inde.gov.br/geoserver/ICMBio/ows",
        "type_name": "ICMBio:limiteucsfederais_a", "srs": "EPSG:4674",
        "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
       # --- Contexto ---
       {"id": "basemap_satelite", "eixo": "contexto", "nome": "Imagem de satelite (Esri)",
        "protocolo": "basemap"},
   ]
   ```

2. Criar `core/diagnostico.py` com EXATAMENTE:

   ```python
   # -*- coding: utf-8 -*-
   """Motor do diagnostico (ARQUITETURA.md §3.3/§3.5).

   carregar_fontes(): para cada fonte WFS selecionada, busca filtrada por
   municipio, grava no GeoPackage (1 camada/fonte) e adiciona ao projeto.
   Opcional: basemap. NAO resolve nome/bbox do municipio (isso e do painel/caller,
   T-011); recebe code_muni, nome_muni e bbox explicitos.
   """
   from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

   from .connectors import wfs, basemap
   from .sources import SOURCES

   # Prefixo de 2 digitos do code_muni -> sigla da UF.
   _UF_POR_CODIGO = {
       "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
       "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
       "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
       "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
       "51": "MT", "52": "GO", "53": "DF",
   }


   def _por_id(ids):
       return [s for s in SOURCES if s["id"] in ids]


   def _filtro_para(s, code_muni, nome_muni):
       """Retorna (cql_filter, usa_bbox)."""
       f = s.get("filtro") or {"tipo": "bbox"}
       t = f.get("tipo")
       if t == "cql_codigo":
           return "{} = {}".format(f["campo"], int(code_muni)), False
       if t == "cql_nome":
           nome = (nome_muni or "").replace("'", "''")
           return "{} = '{}'".format(f["campo"], nome), False
       return None, True


   def _grava_gpkg(layer, gpkg_path, layer_name, primeiro):
       opts = QgsVectorFileWriter.SaveVectorOptions()
       opts.driverName = "GPKG"
       opts.layerName = layer_name
       opts.actionOnExistingFile = (
           QgsVectorFileWriter.CreateOrOverwriteFile if primeiro
           else QgsVectorFileWriter.CreateOrOverwriteLayer
       )
       ctx = QgsProject.instance().transformContext()
       res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, gpkg_path, ctx, opts)
       return res[0] == QgsVectorFileWriter.NoError, res[1]


   def carregar_fontes(source_ids, code_muni, nome_muni, bbox, gpkg_path,
                       add_basemap=False, feedback=None):
       def log(m):
           if feedback is not None:
               feedback.pushInfo(m)

       uf = _UF_POR_CODIGO.get(str(code_muni)[:2], "").lower()
       res = {"ok": [], "falhou": [], "pulou": []}
       primeiro = True

       for s in _por_id(source_ids):
           proto = s.get("protocolo")
           if proto == "basemap":
               continue
           if proto != "wfs":
               res["pulou"].append((s["id"], "conector {} ainda nao implementado".format(proto)))
               continue

           type_name = s["type_name"].replace("{uf}", uf)
           cql, usa_bbox = _filtro_para(s, code_muni, nome_muni)
           layer = wfs.fetch_layer(
               s["endpoint"], type_name, s["id"], srs=s.get("srs", "EPSG:4674"),
               cql_filter=cql, bbox=(bbox if usa_bbox else None),
           )
           if not layer.isValid():
               res["falhou"].append((s["id"], getattr(layer, "error_msg", "camada invalida")))
               continue

           ok, msg = _grava_gpkg(layer, gpkg_path, s["id"], primeiro)
           if not ok:
               res["falhou"].append((s["id"], "gravar GeoPackage: {}".format(msg)))
               continue
           primeiro = False

           gl = QgsVectorLayer("{}|layername={}".format(gpkg_path, s["id"]), s["id"], "ogr")
           if gl.isValid():
               QgsProject.instance().addMapLayer(gl)
               res["ok"].append(s["id"])
               log("OK: {}".format(s["id"]))
           else:
               res["falhou"].append((s["id"], "camada do GeoPackage invalida"))

       if add_basemap:
           bl = basemap.satellite_layer()
           if bl.isValid():
               QgsProject.instance().addMapLayer(bl)
               log("basemap de satelite adicionado")

       return res
   ```

3. NAO registrar nada no provider/GUI (isso e a T-011).

### Comandos de verificacao

```bash
make test
python3 -c "import ast; [ast.parse(open(f).read(), f) for f in ['core/sources.py','core/diagnostico.py']]; print('registry+motor ok')"
```

### Validacao funcional (senior/Diego, no Console do QGIS — NAO e do Junior)

```python
from gisbr.core import diagnostico
r = diagnostico.carregar_fontes(
    ["sicar_imoveis"], code_muni="3106200", nome_muni="Belo Horizonte",
    bbox=(-44.07, -20.06, -43.86, -19.78), gpkg_path="/tmp/diag_bh.gpkg",
    add_basemap=True)
print(r)  # esperado: sicar em r["ok"], camada no projeto + .gpkg em /tmp
```

### Criterios de aceite

- `core/sources.py` e `core/diagnostico.py` com o conteudo EXATO acima.
- `make test` passa.
- `provider.py`/`geobr_qgis_plugin.py`/`algorithms/__init__.py` **inalterados**.

### Resultado

- Substituído `core/sources.py` com o catálogo de fontes da Fase A (WFS de DNIT, MInfra, CPRM, SICAR, ICMBio, e basemap Esri World Imagery).
- Criado `core/diagnostico.py` contendo a lógica para baixar as camadas, gravá-las no formato GeoPackage local usando `QgsVectorFileWriter` (uma camada por tabela) e adicioná-las ao projeto ativo do QGIS.
- Executado `make test` com sucesso (*sintaxe OK*).
- Validação AST em Python bem-sucedida para ambos os arquivos.
- Os arquivos `provider.py`, `geobr_qgis_plugin.py` e `algorithms/__init__.py` não foram tocados.

---

## [T-011] Painel (dock) do diagnostico

- status: concluida
- responsavel: junior (IMPLEMENTA o codigo; senior verifica depois)
- fase: diagnostico — Fase B (GUI)
- branch: `feat/diagnostico-plano-diretor` (ja ativa)
- contexto: `ARQUITETURA.md` §3.4 ; motor pronto em `core/diagnostico.py` (T-010)

> **Metodo desta tarefa (NOVO):** o codigo do dock VOCE implementa, seguindo a
> estrutura e as regras duras abaixo. Os 2 trechos QGIS mais arriscados
> (resolucao do municipio e fiacao no `initGui`) ja vem **prontos** — use-os como
> estao. Ao terminar, o senior revisa e valida no Console do QGIS.

### Objetivo

Criar o **painel (dock)** que e a UX principal: campo de municipio + **arvore de
fontes com checkbox por eixo** + caminho do GeoPackage + opcao satelite + botao
"Carregar", chamando `core.diagnostico.carregar_fontes(...)`. Ligar o dock no
`initGui` do plugin (hoje so registra o provider).

### Arquivos permitidos

- `gui/diagnostico_dock.py` (criar — VOCE implementa)
- `geobr_qgis_plugin.py` (editar SO o `initGui`/`unload`, conforme o bloco exato
  abaixo — copie verbatim)

### Arquivos proibidos / NAO FACA

- NAO tocar em `provider.py`, `core/**`, `algorithms/**`, `metadata.txt`,
  `CLAUDE.md`.
- NAO mudar `initProcessing` nem a ordem em que ele e chamado (o provider PRECISA
  continuar registrando — nao quebre as Fases 1/2).
- NAO inventar API do QGIS: use SOMENTE as classes/metodos nomeados abaixo.
- NAO chamar rede/`carregar_fontes` na construcao do dock — so no clique do botao.
- NAO adicionar dependencia externa (so PyQGIS/Qt).

### REGRAS DURAS (guardrails)

1. O dock e uma classe `DiagnosticoDock(QgsDockWidget)` em `gui/diagnostico_dock.py`.
2. Imports permitidos:
   ```python
   from qgis.gui import QgsDockWidget
   from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
       QTreeWidget, QTreeWidgetItem, QCheckBox, QPushButton, QFileDialog,
       QLabel, QPlainTextEdit)
   from qgis.PyQt.QtCore import Qt
   from qgis.core import QgsProject
   from ..core.sources import SOURCES
   from ..core import diagnostico
   ```
3. Ler as fontes SEMPRE de `SOURCES` (nao hardcodar lista de fontes no dock).
4. Agrupar na arvore por `s["eixo"]` (item-pai por eixo, filhos = fontes com
   checkbox). Pular `protocolo == "basemap"` na arvore (o satelite tem checkbox
   proprio). Guardar o `s["id"]` em cada item filho via
   `item.setData(0, Qt.UserRole, s["id"])`.
5. So coletar como selecionadas as fontes com `checkState(0) == Qt.Checked`.
6. O botao "Carregar" chama UM metodo `self._on_carregar()`; nada de logica de
   rede fora dele.

### Estrutura a implementar (VOCE preenche o layout)

`DiagnosticoDock.__init__(self, iface, parent=None)`: chama
`super().__init__("GisBR — Diagnostico", parent)`, guarda `self.iface = iface`,
chama `self._build_ui()`.

`_build_ui(self)`: um `QWidget` central com `QVBoxLayout` contendo, nesta ordem:
- `QLineEdit` para o **codigo do municipio** (IBGE 7 digitos) — guardar em
  `self.ed_muni`.
- `QTreeWidget` com as fontes agrupadas por eixo (checkbox por fonte) —
  `self.tree`. Use `QTreeWidgetItem`, `item.setFlags(... | Qt.ItemIsUserCheckable)`
  e `item.setCheckState(0, Qt.Unchecked)`.
- linha com `QLineEdit` (caminho do `.gpkg`, `self.ed_gpkg`) + `QPushButton`
  "..." que abre `QFileDialog.getSaveFileName(self, "GeoPackage", "", "GeoPackage (*.gpkg)")`.
- `QCheckBox` "Adicionar imagem de satelite ao fundo" — `self.chk_satelite`.
- `QPushButton` "Carregar selecionadas" — conectar `clicked` a `self._on_carregar`.
- `QPlainTextEdit` read-only para log — `self.txt_log`.
Finalize com `self.setWidget(central)`.

`_selected_source_ids(self)`: percorre `self.tree`, retorna a lista de
`item.data(0, Qt.UserRole)` dos filhos com `checkState(0) == Qt.Checked`.

### Trecho PRONTO 1 — resolucao do municipio (use como esta)

```python
def _info_municipio(self, code_muni):
    """Retorna (nome, bbox) do municipio via geobr read_municipality.
    bbox = (xmin, ymin, xmax, ymax) em EPSG:4674. Pode levantar excecao."""
    import processing
    res = processing.run("gisbr:read_municipality", {
        "CODE": str(code_muni), "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT",
    })
    layer = res["OUTPUT"]
    if isinstance(layer, str):
        from qgis.core import QgsVectorLayer
        layer = QgsProject.instance().mapLayer(layer) or QgsVectorLayer(layer, "muni", "ogr")
    feats = list(layer.getFeatures())
    if not feats:
        raise ValueError("Municipio {} nao encontrado no geobr.".format(code_muni))
    nome = feats[0]["name_muni"]
    ext = layer.extent()
    return nome, (ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum())
```

### Trecho PRONTO 2 — acao do botao (use como base; pode so logar o retorno)

```python
def _on_carregar(self):
    self.txt_log.clear()
    code = self.ed_muni.text().strip()
    gpkg = self.ed_gpkg.text().strip()
    ids = self._selected_source_ids()
    if not code or not gpkg or not ids:
        self.txt_log.appendPlainText("Informe municipio, GeoPackage e ao menos 1 fonte.")
        return
    try:
        nome, bbox = self._info_municipio(code)
    except Exception as exc:
        self.txt_log.appendPlainText("Falha ao resolver o municipio: {}".format(exc))
        return
    self.txt_log.appendPlainText("Municipio: {} ({})".format(nome, code))
    res = diagnostico.carregar_fontes(
        ids, code_muni=code, nome_muni=nome, bbox=bbox, gpkg_path=gpkg,
        add_basemap=self.chk_satelite.isChecked(), feedback=None)
    self.txt_log.appendPlainText("OK: {}".format(", ".join(res["ok"]) or "-"))
    for sid, msg in res["falhou"]:
        self.txt_log.appendPlainText("FALHOU {}: {}".format(sid, msg))
    for sid, msg in res["pulou"]:
        self.txt_log.appendPlainText("PULOU {}: {}".format(sid, msg))
```

### Fiacao EXATA no `geobr_qgis_plugin.py` (copie verbatim — so `initGui`/`unload`)

```python
    def initGui(self):
        self.initProcessing()
        from qgis.PyQt.QtWidgets import QAction
        from qgis.PyQt.QtCore import Qt
        from .gui.diagnostico_dock import DiagnosticoDock
        self.dock = DiagnosticoDock(self.iface)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.hide()
        self.action = QAction("Diagnostico Plano Diretor (GisBR)", self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.dock.setUserVisible)
        self.iface.addPluginToMenu("GisBR", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        if getattr(self, "action", None) is not None:
            self.iface.removePluginMenu("GisBR", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if getattr(self, "dock", None) is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock = None
```

(Mantenha o `import` de `QgsApplication` e `GeobrProvider` que ja existem no topo
do arquivo; nao mexa em `__init__` nem `initProcessing`.)

### Comandos de verificacao

```bash
make test
python3 -c "import ast; [ast.parse(open(f).read(), f) for f in ['gui/diagnostico_dock.py','geobr_qgis_plugin.py']]; print('ok')"
```

> Validacao funcional (abrir o QGIS, ver o dock, marcar SICAR + satelite, carregar
> BH) e do senior/Diego — NAO sua.

### Criterios de aceite

- `gui/diagnostico_dock.py` define `DiagnosticoDock(QgsDockWidget)` com os widgets
  e metodos acima; usa SOMENTE os imports permitidos; le de `SOURCES`.
- `geobr_qgis_plugin.py` com `initGui`/`unload` EXATOS acima; `initProcessing`
  e `__init__` inalterados; provider continua registrando.
- `make test` passa. Nenhuma dependencia externa nova.
- Nenhum arquivo proibido tocado.

### Resultado

- Criado o painel principal do diagnóstico (`gui/diagnostico_dock.py`) com layout Qt contendo campo de código de município, árvore de fontes dinâmica com checkboxes por eixo (lendo de `SOURCES`), seletor de arquivo de destino do GeoPackage, opção de basemap satélite Maxar/Esri e campo de logs de execução.
- Integrado o painel `DiagnosticoDock` no ponto de entrada do plugin (`geobr_qgis_plugin.py`) nas funções `initGui` e `unload` conforme especificado (verbatim), adicionando ação no menu "GisBR" e botão na barra de ferramentas.
- Executado `make test` com sucesso (*sintaxe OK*).
- Validação AST bem-sucedida para ambos os arquivos.
- Os arquivos `provider.py` e `algorithms/__init__.py` não foram tocados, mantendo o provider e algoritmos de base intactos.

---

## [T-013] Painel: combos de UF + Municipio (sem precisar do codigo)

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: diagnostico — Fase B (GUI)
- branch: `feat/diagnostico-plano-diretor`
- contexto: melhora a UX do `gui/diagnostico_dock.py` (T-011). Muitos usuarios
  nao sabem o codigo IBGE.

> **Metodo:** instrucoes fortes + trechos QGIS prontos. Voce ALTERA o
> `gui/diagnostico_dock.py` existente. Senior verifica depois.

### Objetivo

Adicionar dois `QComboBox` em cascata no topo do dock: **UF** (lista estatica) e
**Municipio** (preenchido ao escolher a UF, via `read_municipality`). Escolher um
municipio preenche o campo de codigo existente (`self.ed_muni`). **Manter** o
campo de codigo como alternativa/override. Cachear nome+bbox de cada municipio
para nao baixar de novo no "Carregar".

### Arquivos permitidos

- `gui/diagnostico_dock.py` (alterar)

### Arquivos proibidos / NAO FACA

- NAO tocar em nenhum outro arquivo (`core/**`, `provider.py`,
  `geobr_qgis_plugin.py`, etc.).
- NAO remover o campo `self.ed_muni` nem o `_info_municipio` (vira fallback).
- NAO mudar a assinatura de `carregar_fontes`.
- Imports novos permitidos: adicionar `QComboBox` ao import de
  `qgis.PyQt.QtWidgets` ja existente. Nada alem disso.

### Passos

1. Adicionar a constante de UFs no topo do modulo (apos os imports):
   ```python
   _UFS = [
       ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapa"), ("AM", "Amazonas"),
       ("BA", "Bahia"), ("CE", "Ceara"), ("DF", "Distrito Federal"),
       ("ES", "Espirito Santo"), ("GO", "Goias"), ("MA", "Maranhao"),
       ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"), ("MG", "Minas Gerais"),
       ("PA", "Para"), ("PB", "Paraiba"), ("PR", "Parana"), ("PE", "Pernambuco"),
       ("PI", "Piaui"), ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
       ("RS", "Rio Grande do Sul"), ("RO", "Rondonia"), ("RR", "Roraima"),
       ("SC", "Santa Catarina"), ("SP", "Sao Paulo"), ("SE", "Sergipe"),
       ("TO", "Tocantins"),
   ]
   ```

2. No `_build_ui`, ANTES do campo de codigo (`self.ed_muni`), inserir:
   - `QLabel("Estado (UF):")` + `self.cmb_uf = QComboBox()`. Popular:
     `self.cmb_uf.addItem("— selecione —", "")` e depois, para cada `(sig, nom)`
     em `_UFS`, `self.cmb_uf.addItem("{} - {}".format(sig, nom), sig)`. Conectar
     `self.cmb_uf.currentIndexChanged.connect(self._on_uf_changed)`.
   - `QLabel("Municipio:")` + `self.cmb_muni = QComboBox()`. Conectar
     `self.cmb_muni.currentIndexChanged.connect(self._on_muni_changed)`.
   - Manter o `QLabel` + `self.ed_muni` que ja existem (re-rotular para
     "Codigo IBGE (opcional / preenchido pela selecao):").
   - Inicializar `self._munis = {}` no `__init__` (antes de `_build_ui`).

3. Adicionar os 3 metodos abaixo (PRONTOS — use como estao):

   ```python
   def _listar_municipios(self, uf_sigla):
       """{code(str): (nome, bbox)} dos municipios da UF via read_municipality."""
       import processing
       res = processing.run("gisbr:read_municipality", {
           "CODE": uf_sigla, "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT",
       })
       layer = res["OUTPUT"]
       if isinstance(layer, str):
           from qgis.core import QgsVectorLayer
           layer = QgsProject.instance().mapLayer(layer) or QgsVectorLayer(layer, "m", "ogr")
       munis = {}
       for f in layer.getFeatures():
           code = str(f["code_muni"]).split(".")[0]
           nome = f["name_muni"]
           bb = f.geometry().boundingBox()
           munis[code] = (nome, (bb.xMinimum(), bb.yMinimum(),
                                 bb.xMaximum(), bb.yMaximum()))
       return munis

   def _on_uf_changed(self):
       uf = self.cmb_uf.currentData()
       self.cmb_muni.clear()
       if not uf:
           return
       self.txt_log.appendPlainText("Carregando municipios de {}...".format(uf))
       try:
           self._munis = self._listar_municipios(uf)
       except Exception as exc:
           self.txt_log.appendPlainText("Falha ao listar municipios: {}".format(exc))
           return
       for code in sorted(self._munis, key=lambda c: self._munis[c][0]):
           self.cmb_muni.addItem(self._munis[code][0], code)
       self.txt_log.appendPlainText("{} municipios carregados.".format(len(self._munis)))

   def _on_muni_changed(self):
       code = self.cmb_muni.currentData()
       if code:
           self.ed_muni.setText(str(code))
   ```

4. No `_on_carregar`, TROCAR a resolucao do municipio para usar o cache quando
   houver (mantendo `_info_municipio` como fallback). Onde hoje esta:
   ```python
       try:
           nome, bbox = self._info_municipio(code)
       except Exception as exc:
           self.txt_log.appendPlainText("Falha ao resolver o municipio: {}".format(exc))
           return
   ```
   passar a ser:
   ```python
       try:
           if getattr(self, "_munis", None) and code in self._munis:
               nome, bbox = self._munis[code]
           else:
               nome, bbox = self._info_municipio(code)
       except Exception as exc:
           self.txt_log.appendPlainText("Falha ao resolver o municipio: {}".format(exc))
           return
   ```

### Comandos de verificacao

```bash
make test
python3 -c "import ast; ast.parse(open('gui/diagnostico_dock.py').read()); print('ok')"
```

> Validacao funcional (escolher MG -> ver lista de municipios -> escolher BH ->
> Carregar) e do senior/Diego no QGIS.

### Criterios de aceite

- Dois `QComboBox` (`self.cmb_uf`, `self.cmb_muni`) em cascata; UF estatica,
  municipio populado via `read_municipality`.
- Selecionar municipio preenche `self.ed_muni`; campo de codigo continua editavel.
- `_on_carregar` usa o bbox cacheado quando disponivel, senao `_info_municipio`.
- `make test` passa; nenhum outro arquivo tocado; so `QComboBox` adicionado aos
  imports.

### Resultado

- Adicionados dois widgets `QComboBox` (`self.cmb_uf` e `self.cmb_muni`) no topo da interface.
- Implementado preenchimento assíncrono dos municípios em cascata a partir da UF selecionada chamando o processamento de `read_municipality`.
- Implementado cache local (`self._munis`) contendo o mapeamento de código para `(nome, bbox)` dos municípios da UF para evitar chamadas de rede redundantes no momento do clique no botão "Carregar".
- Mantido o campo `self.ed_muni` como caixa de texto editável e fallback, de modo que selecionar o município preenche o código mas o usuário ainda pode digitar um código diretamente se desejar.
- Integrado o cache no fluxo do botão `_on_carregar` com fallback automático para `_info_municipio(...)` caso o código não esteja presente no cache.
- `make test` executado com sucesso (*sintaxe OK*). AST do python validada. Nenhum outro arquivo modificado.

---

### Backlog / ideias (ainda nao viram tarefa)

Itens conhecidos do roadmap, mantidos como referencia (nao executar ate virarem
tarefa `pronta` com escopo definido):

- `read_comparable_areas` (amc): exige base com `start_year` + `end_year`, nao
  encaixa na `BaseReadAlgorithm` de ano unico.
- `read_health_region` com parametro `macro=True` (variante macro).
- `lookup_muni` como helper interno de traducao codigo <-> nome.
- Validar Fase 2 com mais downloads reais de datasets do censobr (arquivos de
  setor sao nacionais e pesados; filtrar pela camada de entrada).

Release / publicacao no QGIS:

- **i18n (ingles):** o repo oficial do QGIS espera o plugin em ingles. Avaliar
  internacionalizacao via Qt (`tr()`, arquivos `.ts`/`.qm`) com PT-BR como
  traducao, ou publicar com strings em ingles e PT-BR como traducao adicional.
  Decisao tomada: "botao/versao em ingles" mencionada pelo Diego.
- **Nome do plugin (em aberto):** hoje id/nome = `geobr`/`geobr_qgis`. "GeoBR" e
  o nome do pacote R/Python do IPEA; o Diego nao ve problema, mas vale consultar
  a equipe do IPEA antes de publicar com esse nome. Travar antes da submissao.
- Relocar `L10257.pdf` (Estatuto da Cidade, hoje solto na raiz) para `docs/` na
  T-003 — nao deve ficar na raiz nem ir no pacote (a skill ja o exclui).

Complemento Plano Diretor (so apos T-001 + T-002 e a decisao de arquitetura):

- Decidir a forma de juntar geobr-qgis + diagnostico (plugin separado que
  consome o geobr / novo grupo no provider / repo dedicado).
- Portar/adaptar o loader WFS de `desafio-2/src/plugin-qgis/core/wfs.py`
  (pilha de rede do QGIS, fallback `/vsicurl/`, `data_extracao`) como base dos
  conectores dos eixos.
- Avaliar reuso de `parecer.py` / `kpis_dock.py` para o relatorio de diagnostico.
