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

- status: pronta
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

(preencher ao concluir)

---

## [T-002] Varredura de geoservers por eixo tematico

- status: bloqueada
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
4. Reverificar cada endpoint no ar e **registrar a data de acesso**. Reaproveitar
   os endpoints ja validados em `desafio-2` (SICAR WFS, INCRA i3geo).
5. No indice, marcar para cada eixo: **"ja coberto pelo geobr-qgis"**,
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
- Eixos 3, 5 e 6 deixam explicito o que o geobr-qgis **ja resolve**.
- O indice classifica cada eixo por esforco (ja coberto / conector novo / so
  download).
- Nenhum arquivo de codigo foi tocado.

### Resultado

(preencher ao concluir)

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
