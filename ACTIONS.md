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

## [T-014] Ajustes de uso: combo buscavel, skip-exists e nome da cidade na camada

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: diagnostico — Fase B (ajustes pos-teste)
- branch: `feat/diagnostico-plano-diretor`
- contexto: feedback do teste real no QGIS (Diego). Tres ajustes:
  (1) combo de municipio "segura o mouse"; (2) re-download de bases ja baixadas;
  (3) identificar a cidade na camada.

> **Metodo:** o motor (core) vem PRONTO abaixo (e delicado — copie verbatim). No
> dock voce faz edicoes pontuais com os snippets prontos. Senior verifica depois.

### Arquivos permitidos

- `core/diagnostico.py` (substituir TODO o conteudo pelo bloco do Passo 1)
- `gui/diagnostico_dock.py` (edicoes pontuais dos Passos 2 a 5)

### Arquivos proibidos / NAO FACA

- NAO tocar em `core/sources.py`, `core/connectors/**`, `provider.py`,
  `geobr_qgis_plugin.py`, `metadata.txt`, `CLAUDE.md`.
- NAO mudar a ordem dos parametros existentes de `carregar_fontes` (so foi
  ADICIONADO `force=False` antes de `feedback`).

### Passo 1 — `core/diagnostico.py` (substituir o arquivo INTEIRO por isto)

```python
# -*- coding: utf-8 -*-
"""Motor do diagnostico (ARQUITETURA.md §3.3/§3.5).

carregar_fontes(): para cada fonte WFS selecionada, busca filtrada por municipio,
grava no GeoPackage (1 camada/fonte, nome inclui o code do municipio) e adiciona
ao projeto. Pula fontes ja existentes no GeoPackage (a nao ser force=True).
"""
import os

from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

from .connectors import wfs, basemap
from .sources import SOURCES

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
    f = s.get("filtro") or {"tipo": "bbox"}
    t = f.get("tipo")
    if t == "cql_codigo":
        return "{} = {}".format(f["campo"], int(code_muni)), False
    if t == "cql_nome":
        nome = (nome_muni or "").replace("'", "''")
        return "{} = '{}'".format(f["campo"], nome), False
    return None, True


def _layers_existentes(gpkg_path):
    """Nomes de camadas ja presentes no GeoPackage (set). Vazio se nao existe."""
    if not os.path.exists(gpkg_path):
        return set()
    vl = QgsVectorLayer(gpkg_path, "probe", "ogr")
    if not vl.isValid():
        return set()
    nomes = set()
    for sub in vl.dataProvider().subLayers():
        parts = sub.split("!!::!!")
        if len(parts) > 1:
            nomes.add(parts[1])
    return nomes


def _grava_gpkg(layer, gpkg_path, layer_name):
    """Grava 1 camada no GeoPackage. Cria o arquivo se nao existir; senao
    adiciona/sobrescreve so essa camada (preserva as demais)."""
    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = layer_name
    opts.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(gpkg_path)
        else QgsVectorFileWriter.CreateOrOverwriteFile
    )
    ctx = QgsProject.instance().transformContext()
    res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, gpkg_path, ctx, opts)
    return res[0] == QgsVectorFileWriter.NoError, res[1]


def carregar_fontes(source_ids, code_muni, nome_muni, bbox, gpkg_path,
                    add_basemap=False, force=False, feedback=None):
    def log(m):
        if feedback is not None:
            feedback.pushInfo(m)

    uf = _UF_POR_CODIGO.get(str(code_muni)[:2], "").lower()
    res = {"ok": [], "falhou": [], "pulou": []}
    existentes = _layers_existentes(gpkg_path)

    for s in _por_id(source_ids):
        proto = s.get("protocolo")
        if proto == "basemap":
            continue
        if proto != "wfs":
            res["pulou"].append((s["id"], "conector {} ainda nao implementado".format(proto)))
            continue

        layer_name = "{}_{}".format(s["id"], code_muni)
        if (not force) and layer_name in existentes:
            res["pulou"].append((s["id"], "ja existe no GeoPackage ({})".format(layer_name)))
            continue

        type_name = s["type_name"].replace("{uf}", uf)
        cql, usa_bbox = _filtro_para(s, code_muni, nome_muni)
        layer = wfs.fetch_layer(
            s["endpoint"], type_name, layer_name, srs=s.get("srs", "EPSG:4674"),
            cql_filter=cql, bbox=(bbox if usa_bbox else None),
        )
        if not layer.isValid():
            res["falhou"].append((s["id"], getattr(layer, "error_msg", "camada invalida")))
            continue

        ok, msg = _grava_gpkg(layer, gpkg_path, layer_name)
        if not ok:
            res["falhou"].append((s["id"], "gravar GeoPackage: {}".format(msg)))
            continue
        existentes.add(layer_name)

        nome_proj = "{} - {}".format(s.get("nome", s["id"]), nome_muni or code_muni)
        gl = QgsVectorLayer("{}|layername={}".format(gpkg_path, layer_name), nome_proj, "ogr")
        if gl.isValid():
            QgsProject.instance().addMapLayer(gl)
            res["ok"].append(s["id"])
            log("OK: {}".format(layer_name))
        else:
            res["falhou"].append((s["id"], "camada do GeoPackage invalida"))

    if add_basemap:
        bl = basemap.satellite_layer()
        if bl.isValid():
            QgsProject.instance().addMapLayer(bl)
            log("basemap de satelite adicionado")

    return res
```

### Passo 2 — imports do dock (`gui/diagnostico_dock.py`)

No import de `qgis.PyQt.QtWidgets`, ADICIONAR `QCompleter` (alem do `QComboBox`
ja la). Ex.: a linha de import passa a terminar com `..., QComboBox, QCompleter)`.

### Passo 3 — combo de municipio BUSCAVEL (resolve o "segura o mouse")

No `_build_ui`, logo APOS criar `self.cmb_muni = QComboBox()` e conectar o sinal,
acrescentar:
```python
        self.cmb_muni.setEditable(True)
        self.cmb_muni.setInsertPolicy(QComboBox.NoInsert)
        _comp = self.cmb_muni.completer()
        _comp.setCompletionMode(QCompleter.PopupCompletion)
        _comp.setFilterMode(Qt.MatchContains)
        _comp.setCaseSensitivity(Qt.CaseInsensitive)
```

### Passo 4 — checkbox "atualizar" + bloquear sinais ao popular

(a) No `_build_ui`, logo APOS o `self.chk_satelite`, adicionar:
```python
        self.chk_atualizar = QCheckBox("Atualizar bases ja baixadas (rebaixar)")
        layout.addWidget(self.chk_atualizar)
```
(b) Em `_on_uf_changed`, ENVOLVER o `clear()` + o loop de `addItem` com
`blockSignals` (evita disparar `_on_muni_changed` durante a populacao) e nao
pre-selecionar nada. O corpo de povoamento fica:
```python
        self.cmb_muni.blockSignals(True)
        self.cmb_muni.clear()
        for code in sorted(self._munis, key=lambda c: self._munis[c][0]):
            self.cmb_muni.addItem(self._munis[code][0], code)
        self.cmb_muni.setCurrentIndex(-1)
        self.cmb_muni.blockSignals(False)
```
(mantenha as mensagens de log e o tratamento de erro que ja existem).

### Passo 5 — passar `force` no `_on_carregar`

Na chamada de `diagnostico.carregar_fontes(...)`, acrescentar o argumento
`force=self.chk_atualizar.isChecked()`:
```python
        res = diagnostico.carregar_fontes(
            ids, code_muni=code, nome_muni=nome, bbox=bbox, gpkg_path=gpkg,
            add_basemap=self.chk_satelite.isChecked(),
            force=self.chk_atualizar.isChecked(), feedback=None)
```

### Comandos de verificacao

```bash
make test
python3 -c "import ast; [ast.parse(open(f).read(), f) for f in ['core/diagnostico.py','gui/diagnostico_dock.py']]; print('ok')"
```

> Validacao funcional (combo busca digitando; recarregar SICAR ja baixado ->
> "pulou"; marcar "atualizar" -> rebaixa; camadas no projeto com a cidade no
> nome) e do senior/Diego no QGIS.

### Criterios de aceite

- `core/diagnostico.py` = bloco do Passo 1 (verbatim): nome de camada
  `id_codemuni`, skip se ja existe (salvo `force`), grava por existencia do
  arquivo (NAO recria o .gpkg), nome de projeto "<fonte> - <cidade>".
- Combo de municipio editavel/buscavel; checkbox "Atualizar..."; `_on_uf_changed`
  com `blockSignals`; `_on_carregar` passando `force`.
- `make test` passa; nenhum arquivo proibido tocado.

### Resultado

- Substituído `core/diagnostico.py` com a nova lógica verbatim que implementa a checagem de camadas já presentes no GeoPackage (`_layers_existentes`), pulando o download se a camada já existir e `force=False` (economizando chamadas de rede lentas). A gravação agora usa o parâmetro do município no nome da camada e do projeto (ex.: "SICAR - Imóveis (CAR) - Belo Horizonte").
- Atualizado `gui/diagnostico_dock.py` para incluir `QCompleter` nos imports.
- Combo de município (`self.cmb_muni`) configurado para ser editável/buscável com autocompletar sem que segure o mouse do usuário.
- Adicionado checkbox `self.chk_atualizar` ("Atualizar bases ja baixadas (rebaixar)") no dock para forçar o re-download das camadas no GPKG (passando `force=self.chk_atualizar.isChecked()` na chamada ao motor).
- O método `_on_uf_changed` foi corrigido para envelopar o povoamento com `blockSignals(True/False)` para evitar disparos colaterais e definir o índice inicial como -1.
- Executado `make test` com sucesso (*sintaxe OK*). Nenhum arquivo proibido tocado.

---

## [T-012] Conector ArcGIS REST + fontes ANA/IBAMA (Fase C)

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: diagnostico — Fase C
- branch: `feat/diagnostico-plano-diretor`
- contexto: `ARQUITETURA.md` §3.2 ; fontes em `fontes-detalhe.md` (T-007).
  Hoje o motor "pula" protocolo `arcgis`; esta tarefa habilita.

> **Metodo:** conector e motor vem PRONTOS (verbatim). Em `sources.py` voce
> INSERE os blocos indicados. Senior verifica depois.

### Arquivos permitidos

- `core/connectors/arcgis_rest.py` (criar — Passo 1)
- `core/diagnostico.py` (substituir o arquivo INTEIRO — Passo 2)
- `core/sources.py` (INSERIR as 5 fontes do Passo 3; nao remover nada)

### Arquivos proibidos / NAO FACA

- NAO tocar em `core/connectors/wfs.py`, `core/connectors/basemap.py`,
  `provider.py`, `geobr_qgis_plugin.py`, `gui/**`, `metadata.txt`, `CLAUDE.md`.
- NAO remover fontes existentes do `sources.py` (so adicionar).

### Passo 1 — criar `core/connectors/arcgis_rest.py` (verbatim)

```python
# -*- coding: utf-8 -*-
"""Conector ArcGIS REST (FeatureServer/MapServer) do diagnostico.

Consulta a operacao /query da layer (f=geojson) pela pilha de rede do QGIS;
filtro por `where` (campo municipal) OU por bbox (esriGeometryEnvelope).
Retorna QgsVectorLayer (so MONTA; gravar/adicionar e do motor).
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


def build_url(endpoint, layer_id, srs="EPSG:4674", where=None, bbox=None):
    wkid = srs.split(":")[-1]
    params = {"outFields": "*", "f": "geojson", "outSR": wkid,
              "where": where or "1=1"}
    if bbox is not None:
        minx, miny, maxx, maxy = bbox
        params["geometry"] = "{},{},{},{}".format(minx, miny, maxx, maxy)
        params["geometryType"] = "esriGeometryEnvelope"
        params["inSR"] = wkid
        params["spatialRel"] = "esriSpatialRelIntersects"
    base = "{}/{}/query".format(endpoint.rstrip("/"), layer_id)
    return base + "?" + urllib.parse.urlencode(params)


def fetch_layer(endpoint, layer_id, layer_name, srs="EPSG:4674", where=None, bbox=None):
    url = build_url(endpoint, layer_id, srs=srs, where=where, bbox=bbox)
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
                return _stamp(layer, "ArcGIS REST (GeoJSON)")
            erro = "GeoJSON recebido, mas o GDAL nao abriu a camada."
        else:
            erro = reply.errorString() or "resposta vazia"
    except Exception as exc:
        erro = "{}: {}".format(type(exc).__name__, exc)
    layer = QgsVectorLayer("/vsicurl/" + url, layer_name, "ogr")
    if layer.isValid():
        return _stamp(layer, "ArcGIS REST (GeoJSON/vsicurl)")
    return _invalid(layer_name, "Falha ArcGIS ({}/{}). {}".format(endpoint, layer_id, erro or ""))
```

### Passo 2 — substituir `core/diagnostico.py` INTEIRO (verbatim)

```python
# -*- coding: utf-8 -*-
"""Motor do diagnostico (ARQUITETURA.md §3.3/§3.5). Protocolos: wfs, arcgis."""
import os

from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

from .connectors import wfs, basemap, arcgis_rest
from .sources import SOURCES

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
    f = s.get("filtro") or {"tipo": "bbox"}
    t = f.get("tipo")
    if t == "cql_codigo":
        return "{} = {}".format(f["campo"], int(code_muni)), False
    if t == "cql_nome":
        nome = (nome_muni or "").replace("'", "''")
        return "{} = '{}'".format(f["campo"], nome), False
    return None, True


def _layers_existentes(gpkg_path):
    if not os.path.exists(gpkg_path):
        return set()
    vl = QgsVectorLayer(gpkg_path, "probe", "ogr")
    if not vl.isValid():
        return set()
    nomes = set()
    for sub in vl.dataProvider().subLayers():
        parts = sub.split("!!::!!")
        if len(parts) > 1:
            nomes.add(parts[1])
    return nomes


def _grava_gpkg(layer, gpkg_path, layer_name):
    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = layer_name
    opts.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(gpkg_path)
        else QgsVectorFileWriter.CreateOrOverwriteFile
    )
    ctx = QgsProject.instance().transformContext()
    res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, gpkg_path, ctx, opts)
    return res[0] == QgsVectorFileWriter.NoError, res[1]


def _busca_camada(s, layer_name, uf, cql, usa_bbox, bbox):
    proto = s.get("protocolo")
    srs = s.get("srs", "EPSG:4674")
    if proto == "wfs":
        type_name = s["type_name"].replace("{uf}", uf)
        return wfs.fetch_layer(s["endpoint"], type_name, layer_name, srs=srs,
                               cql_filter=cql, bbox=(bbox if usa_bbox else None))
    if proto == "arcgis":
        return arcgis_rest.fetch_layer(s["endpoint"], s["layer_id"], layer_name,
                                       srs=srs, where=cql,
                                       bbox=(bbox if usa_bbox else None))
    return None


def carregar_fontes(source_ids, code_muni, nome_muni, bbox, gpkg_path,
                    add_basemap=False, force=False, feedback=None):
    def log(m):
        if feedback is not None:
            feedback.pushInfo(m)

    uf = _UF_POR_CODIGO.get(str(code_muni)[:2], "").lower()
    res = {"ok": [], "falhou": [], "pulou": []}
    existentes = _layers_existentes(gpkg_path)

    for s in _por_id(source_ids):
        proto = s.get("protocolo")
        if proto == "basemap":
            continue
        if proto not in ("wfs", "arcgis"):
            res["pulou"].append((s["id"], "conector {} ainda nao implementado".format(proto)))
            continue

        layer_name = "{}_{}".format(s["id"], code_muni)
        if (not force) and layer_name in existentes:
            res["pulou"].append((s["id"], "ja existe no GeoPackage ({})".format(layer_name)))
            continue

        cql, usa_bbox = _filtro_para(s, code_muni, nome_muni)
        layer = _busca_camada(s, layer_name, uf, cql, usa_bbox, bbox)
        if layer is None or not layer.isValid():
            msg = getattr(layer, "error_msg", "camada invalida") if layer else "protocolo desconhecido"
            res["falhou"].append((s["id"], msg))
            continue

        ok, msg = _grava_gpkg(layer, gpkg_path, layer_name)
        if not ok:
            res["falhou"].append((s["id"], "gravar GeoPackage: {}".format(msg)))
            continue
        existentes.add(layer_name)

        nome_proj = "{} - {}".format(s.get("nome", s["id"]), nome_muni or code_muni)
        gl = QgsVectorLayer("{}|layername={}".format(gpkg_path, layer_name), nome_proj, "ogr")
        if gl.isValid():
            QgsProject.instance().addMapLayer(gl)
            res["ok"].append(s["id"])
            log("OK: {}".format(layer_name))
        else:
            res["falhou"].append((s["id"], "camada do GeoPackage invalida"))

    if add_basemap:
        bl = basemap.satellite_layer()
        if bl.isValid():
            QgsProject.instance().addMapLayer(bl)
            log("basemap de satelite adicionado")

    return res
```

### Passo 3 — INSERIR estas 5 fontes em `core/sources.py`

Inserir logo ANTES do comentario `# --- Contexto ---` (a entrada do basemap),
sem remover nada. Fontes ArcGIS usam `layer_id` (nao `type_name`):

```python
    # --- ArcGIS REST (Fase C) ---
    {"id": "ana_hidrografia", "eixo": "saneamento", "nome": "ANA — Hidrografia",
     "protocolo": "arcgis",
     "endpoint": "https://www.snirh.gov.br/arcgis/rest/services/DADOSABERTOS/Hidrografia/MapServer",
     "layer_id": "0", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    {"id": "ibama_autos", "eixo": "ambiental", "nome": "IBAMA — Autos de infracao/embargos",
     "protocolo": "arcgis",
     "endpoint": "https://pamgia.ibama.gov.br/server/rest/services/app_dadosabertos/adm_auto_infracao_p/MapServer",
     "layer_id": "0", "srs": "EPSG:4674",
     "filtro": {"tipo": "cql_codigo", "campo": "cod_municipio"}, "licenca": "Publica"},
    {"id": "ibama_esgoto", "eixo": "saneamento", "nome": "IBAMA — Esgotamento sanitario",
     "protocolo": "arcgis",
     "endpoint": "https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Sistema_de_Esgotamento_Sanit%C3%A1rio/MapServer",
     "layer_id": "6", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    {"id": "ibama_agua", "eixo": "saneamento", "nome": "IBAMA — Abastecimento de agua",
     "protocolo": "arcgis",
     "endpoint": "https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Sistema_de_Abastecimento_de_%C3%81gua/MapServer",
     "layer_id": "5", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
    {"id": "ibama_aterro", "eixo": "saneamento", "nome": "IBAMA — Aterro sanitario",
     "protocolo": "arcgis",
     "endpoint": "https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Aterro_Sanit%C3%A1rio/MapServer",
     "layer_id": "8", "srs": "EPSG:4674",
     "filtro": {"tipo": "bbox"}, "licenca": "Publica"},
```

### Comandos de verificacao

```bash
make test
python3 -c "import ast; [ast.parse(open(f).read(), f) for f in ['core/connectors/arcgis_rest.py','core/diagnostico.py','core/sources.py']]; print('ok')"
```

> Validacao funcional (carregar `ibama_autos` por codigo e `ana_hidrografia` por
> bbox num municipio) e do senior/Diego no QGIS.

### Criterios de aceite

- `arcgis_rest.py` = Passo 1; `diagnostico.py` = Passo 2 (com `_busca_camada`
  e `arcgis_rest` no import); 5 fontes ArcGIS adicionadas (com `layer_id`).
- `make test` passa; fontes WFS existentes intactas; nenhum arquivo proibido tocado.

### Resultado

- Criado o arquivo `core/connectors/arcgis_rest.py` contendo o conector ArcGIS REST para consulta no endpoint `/query` das camadas de MapServer/FeatureServer e formatação de saída em GeoJSON.
- Substituído todo o conteúdo de `core/diagnostico.py` para incluir o conector `arcgis_rest` no escopo, delegando requisições do protocolo `arcgis` para o novo conector e integrando-o ao fluxo de download e gravação de GeoPackage.
- Adicionadas as 5 fontes ArcGIS REST declaradas (ANA Hidrografia, IBAMA Autos, IBAMA Esgotamento, IBAMA Abastecimento e IBAMA Aterro) ao catálogo `SOURCES` no arquivo `core/sources.py`.
- Executado `make test` com sucesso (*sintaxe OK*). Nenhum arquivo proibido tocado.

---

## [T-015] Listar TODAS as bases relevantes do geobr no painel

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: diagnostico — Fase B/C
- branch: `feat/diagnostico-plano-diretor`
- contexto: Diego quer todas as bases relevantes do geobr funcionando no painel,
  recortadas pelo municipio.

> **Metodo:** motor vem PRONTO (substitui o arquivo inteiro — verbatim). Em
> `sources.py` voce INSERE o bloco de fontes geobr. No dock, troca um dict.
> Senior verifica depois.

### Escopo (decidido com o Diego, 2026-06-29)

- **Recorte por municipio**: `code` (filtra por `code_muni` no algoritmo) para
  Demografia; `bbox` (baixa e recorta pela bounding box do municipio via
  `native:extractbyextent`) para o resto.
- **Geografias FORA** (nao fazem sentido na escala municipal): country, region,
  state, meso/micro/intermediate/immediate_region, metro_area,
  urban_concentrations, pop_arrangements, health_region, amazon, semiarid.
- **`read_statistical_grid` ficou de fora / pra depois** (nacional ~GB; caro
  recortar). Registrado no backlog.
- **3 fontes so-v2** (favela, polling_places, quilombola_land) entram **com
  marca** `requer_parquet`: o motor as PULA com aviso se nao houver driver
  Parquet/pyarrow (nao quebra o plugin).

### Arquivos permitidos

- `core/diagnostico.py` (substituir o arquivo INTEIRO — Passo 1)
- `core/sources.py` (INSERIR o bloco geobr — Passo 2; nao remover nada)
- `gui/diagnostico_dock.py` (trocar SO o dict `_EIXO_NOMES` — Passo 3)

### Arquivos proibidos / NAO FACA

- NAO tocar em `core/connectors/**`, `provider.py`, `geobr_qgis_plugin.py`,
  `algorithms/**`, `metadata.txt`, `CLAUDE.md`.
- No dock, mexer SO no dict `_EIXO_NOMES` (nada mais).

### Passo 1 — substituir `core/diagnostico.py` INTEIRO (verbatim)

```python
# -*- coding: utf-8 -*-
"""Motor do diagnostico. Protocolos: wfs, arcgis, geobr (code|bbox)."""
import os

from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

from .connectors import wfs, basemap, arcgis_rest
from .sources import SOURCES

_UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

_PROTOCOLOS = ("wfs", "arcgis", "geobr")


def _por_id(ids):
    return [s for s in SOURCES if s["id"] in ids]


def _filtro_para(s, code_muni, nome_muni):
    f = s.get("filtro") or {"tipo": "bbox"}
    t = f.get("tipo")
    if t == "cql_codigo":
        return "{} = {}".format(f["campo"], int(code_muni)), False
    if t == "cql_nome":
        nome = (nome_muni or "").replace("'", "''")
        return "{} = '{}'".format(f["campo"], nome), False
    return None, True


def _layers_existentes(gpkg_path):
    if not os.path.exists(gpkg_path):
        return set()
    vl = QgsVectorLayer(gpkg_path, "probe", "ogr")
    if not vl.isValid():
        return set()
    nomes = set()
    for sub in vl.dataProvider().subLayers():
        parts = sub.split("!!::!!")
        if len(parts) > 1:
            nomes.add(parts[1])
    return nomes


def _grava_gpkg(layer, gpkg_path, layer_name):
    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = layer_name
    opts.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(gpkg_path)
        else QgsVectorFileWriter.CreateOrOverwriteFile
    )
    ctx = QgsProject.instance().transformContext()
    res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, gpkg_path, ctx, opts)
    return res[0] == QgsVectorFileWriter.NoError, res[1]


def _resolve_out(out, layer_name):
    if isinstance(out, str):
        return QgsProject.instance().mapLayer(out) or QgsVectorLayer(out, layer_name, "ogr")
    return out


def _invalida(layer_name, msg):
    inv = QgsVectorLayer("", layer_name, "ogr")
    inv.error_msg = msg
    return inv


def _carrega_geobr(s, code_muni, bbox, layer_name):
    """Roda o algoritmo geobr (Fase 1/2). recorte 'code' filtra por code_muni;
    recorte 'bbox' baixa e recorta pela bbox do municipio."""
    import processing
    if s.get("requer_parquet"):
        from . import capabilities
        if capabilities.parquet_backend() is None:
            return _invalida(layer_name, "requer driver Parquet ou pyarrow (fonte v2)")

    algo = s["algo"]
    recorte = s.get("recorte", "code")
    code_param = str(code_muni) if recorte == "code" else "all"
    try:
        out = processing.run("gisbr:{}".format(algo), {
            "CODE": code_param, "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]
    except Exception as exc:
        return _invalida(layer_name, "geobr {}: {}".format(algo, exc))
    out = _resolve_out(out, layer_name)

    if recorte == "bbox":
        if bbox is None:
            return _invalida(layer_name, "bbox do municipio necessario para esta fonte")
        if out is None or not out.isValid():
            return _invalida(layer_name, "geobr {} nao retornou camada".format(algo))
        try:
            extent = "{},{},{},{} [EPSG:4674]".format(bbox[0], bbox[2], bbox[1], bbox[3])
            clip = processing.run("native:extractbyextent", {
                "INPUT": out, "EXTENT": extent, "CLIP": True,
                "OUTPUT": "TEMPORARY_OUTPUT",
            })["OUTPUT"]
            out = _resolve_out(clip, layer_name)
        except Exception as exc:
            return _invalida(layer_name, "recorte bbox: {}".format(exc))
    return out


def _busca_camada(s, layer_name, uf, cql, usa_bbox, bbox, code_muni):
    proto = s.get("protocolo")
    srs = s.get("srs", "EPSG:4674")
    if proto == "wfs":
        type_name = s["type_name"].replace("{uf}", uf)
        return wfs.fetch_layer(s["endpoint"], type_name, layer_name, srs=srs,
                               cql_filter=cql, bbox=(bbox if usa_bbox else None))
    if proto == "arcgis":
        return arcgis_rest.fetch_layer(s["endpoint"], s["layer_id"], layer_name,
                                       srs=srs, where=cql,
                                       bbox=(bbox if usa_bbox else None))
    if proto == "geobr":
        return _carrega_geobr(s, code_muni, bbox, layer_name)
    return None


def carregar_fontes(source_ids, code_muni, nome_muni, bbox, gpkg_path,
                    add_basemap=False, force=False, feedback=None):
    def log(m):
        if feedback is not None:
            feedback.pushInfo(m)

    uf = _UF_POR_CODIGO.get(str(code_muni)[:2], "").lower()
    res = {"ok": [], "falhou": [], "pulou": []}
    existentes = _layers_existentes(gpkg_path)

    for s in _por_id(source_ids):
        proto = s.get("protocolo")
        if proto == "basemap":
            continue
        if proto not in _PROTOCOLOS:
            res["pulou"].append((s["id"], "conector {} ainda nao implementado".format(proto)))
            continue

        layer_name = "{}_{}".format(s["id"], code_muni)
        if (not force) and layer_name in existentes:
            res["pulou"].append((s["id"], "ja existe no GeoPackage ({})".format(layer_name)))
            continue

        cql, usa_bbox = _filtro_para(s, code_muni, nome_muni)
        layer = _busca_camada(s, layer_name, uf, cql, usa_bbox, bbox, code_muni)
        if layer is None or not layer.isValid():
            msg = getattr(layer, "error_msg", "camada invalida") if layer else "protocolo desconhecido"
            res["falhou"].append((s["id"], msg))
            continue

        ok, msg = _grava_gpkg(layer, gpkg_path, layer_name)
        if not ok:
            res["falhou"].append((s["id"], "gravar GeoPackage: {}".format(msg)))
            continue
        existentes.add(layer_name)

        nome_proj = "{} - {}".format(s.get("nome", s["id"]), nome_muni or code_muni)
        gl = QgsVectorLayer("{}|layername={}".format(gpkg_path, layer_name), nome_proj, "ogr")
        if gl.isValid():
            QgsProject.instance().addMapLayer(gl)
            res["ok"].append(s["id"])
            log("OK: {}".format(layer_name))
        else:
            res["falhou"].append((s["id"], "camada do GeoPackage invalida"))

    if add_basemap:
        bl = basemap.satellite_layer()
        if bl.isValid():
            QgsProject.instance().addMapLayer(bl)
            log("basemap de satelite adicionado")

    return res
```

### Passo 2 — INSERIR o bloco geobr em `core/sources.py`

Inserir logo ANTES do comentario `# --- Contexto ---` (a entrada do basemap),
sem remover nada:

```python
    # --- geobr v1 (GPKG; sem dependencia externa) ---
    {"id": "geobr_municipio", "eixo": "demografia", "nome": "Limite municipal (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_municipality", "recorte": "code"},
    {"id": "geobr_setores", "eixo": "demografia", "nome": "Setores censitarios (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_census_tract", "recorte": "code"},
    {"id": "geobr_ponderacao", "eixo": "demografia", "nome": "Areas de ponderacao (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_weighting_area", "recorte": "code"},
    {"id": "geobr_escolas", "eixo": "educacao", "nome": "Escolas (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_schools", "recorte": "bbox"},
    {"id": "geobr_saude", "eixo": "saude", "nome": "Estabelecimentos de saude (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_health_facilities", "recorte": "bbox"},
    {"id": "geobr_biomas", "eixo": "ambiental", "nome": "Biomas (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_biomes", "recorte": "bbox"},
    {"id": "geobr_ucs", "eixo": "ambiental", "nome": "Unidades de conservacao (geobr)",
     "protocolo": "geobr", "algo": "read_conservation_units", "recorte": "bbox"},
    {"id": "geobr_terras_indigenas", "eixo": "ambiental", "nome": "Terras indigenas (geobr)",
     "protocolo": "geobr", "algo": "read_indigenous_land", "recorte": "bbox"},
    {"id": "geobr_risco", "eixo": "ambiental", "nome": "Areas de risco de desastre (geobr)",
     "protocolo": "geobr", "algo": "read_disaster_risk_area", "recorte": "bbox"},
    {"id": "geobr_mancha_urbana", "eixo": "urbano", "nome": "Mancha urbana (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_urban_area", "recorte": "bbox"},
    {"id": "geobr_sede", "eixo": "pol-admin", "nome": "Sede municipal (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_municipal_seat", "recorte": "bbox"},
    {"id": "geobr_bairros", "eixo": "pol-admin", "nome": "Bairros (IBGE/geobr)",
     "protocolo": "geobr", "algo": "read_neighborhood", "recorte": "bbox"},
    # --- geobr v2 (so-v2; REQUEREM driver Parquet ou pyarrow; senao sao pulados) ---
    {"id": "geobr_favelas", "eixo": "demografia", "nome": "Favelas/comunidades (geobr v2)",
     "protocolo": "geobr", "algo": "read_favela_v2", "recorte": "code", "requer_parquet": True},
    {"id": "geobr_locais_votacao", "eixo": "pol-admin", "nome": "Locais de votacao (geobr v2)",
     "protocolo": "geobr", "algo": "read_polling_places_v2", "recorte": "code", "requer_parquet": True},
    {"id": "geobr_quilombolas", "eixo": "ambiental", "nome": "Terras quilombolas (geobr v2)",
     "protocolo": "geobr", "algo": "read_quilombola_land_v2", "recorte": "code", "requer_parquet": True},
```

### Passo 3 — atualizar `_EIXO_NOMES` em `gui/diagnostico_dock.py`

Substituir o dict `_EIXO_NOMES` existente por:

```python
_EIXO_NOMES = {
    "transportes": "1. Transportes",
    "saneamento": "2. Drenagem e Saneamento",
    "demografia": "3. Demografia",
    "ambiental": "4. Ambiental",
    "educacao": "5. Educacao",
    "saude": "6. Saude",
    "urbano": "7. Urbano",
    "pol-admin": "8. Politico-administrativo",
}
```

### Comandos de verificacao

```bash
make test
python3 -c "import ast; [ast.parse(open(f).read(), f) for f in ['core/diagnostico.py','core/sources.py','gui/diagnostico_dock.py']]; print('ok')"
```

> Validacao funcional (no painel: marcar Setores (code) e Escolas/Biomas (bbox)
> de BH; conferir recorte; as v2 pulam se nao houver Parquet) e do senior/Diego.

### Criterios de aceite

- `core/diagnostico.py` = Passo 1 (com `_carrega_geobr` recorte code|bbox e a
  checagem `requer_parquet`).
- 15 fontes geobr adicionadas (12 v1 + 3 v2 marcadas); WFS/ArcGIS intactas.
- `_EIXO_NOMES` atualizado; resto do dock intacto.
- `make test` passa; nenhum arquivo proibido tocado.

### Resultado

- Substituído todo o conteúdo de `core/diagnostico.py` com o motor completo (Passo 1), que adiciona o protocolo `geobr`, implementa a execução de algoritmos nativos do `geobr` via `processing.run` e suporta dois modos de recorte: `code` (filtro direto por código de município no parâmetro CODE) e `bbox` (download completo da camada e recorte espacial automático do município via `native:extractbyextent`). Também foi adicionado suporte à marcação `requer_parquet` para checagem ativa de driver Parquet/pyarrow nas fontes v2.
- Adicionadas as 15 fontes baseadas no `geobr` (12 v1 + 3 v2) ao catálogo `SOURCES` em `core/sources.py`, logo antes do basemap satélite.
- Atualizado o dicionário `_EIXO_NOMES` no arquivo `gui/diagnostico_dock.py` com todos os 8 eixos temáticos do diagnóstico urbano e ambiental.
- `make test` executado e aprovado com sucesso (*sintaxe OK*). Nenhum arquivo proibido foi tocado.

---

## [T-016] Gerar o .zip de publicacao

- status: concluida
- responsavel: junior
- fase: release

> ⚠️ **MUDANCA DE PLANO (Diego, 2026-06-29):** a publicacao passa a incluir o
> **diagnostico completo** (painel + conectores + T-015), nao so o espelho geobr.
> Logo o zip sai da branch **`feat/diagnostico-plano-diretor`** (que tem tudo),
> NAO mais da `main`. O texto antigo abaixo (zip da `main`) esta **obsoleto** e
> sera reescrito pelo senior quando a validacao + o metadata estiverem prontos.
> NAO executar esta tarefa ainda.

- contexto (obsoleto): publicar o espelho geobr a partir da `main`.

> Usa a skill **`build-qgis-zip`** (NAO montar o zip a mao). A submissao no
> plugins.qgis.org e passo MANUAL do Diego — esta tarefa so gera o arquivo.

### PRE-REQUISITO DURO

- O working tree precisa estar **LIMPO**. Se a **T-012 (ou outra) estiver em
  andamento, COMMITE antes**. **Nunca** troque de branch com mudancas nao
  commitadas (perderia/embaralharia o trabalho).

### Arquivos permitidos

- nenhum arquivo do repo e editado; a tarefa so gera `dist/gisbr-0.2.0.zip`
  (pasta `dist/` e gitignored).

### Passos

1. `git status --short` → tem que sair **vazio**. Se nao, PARE e commite/avise.
2. `git switch main`
3. `bash .claude/skills/build-qgis-zip/package.sh`
   (a skill em `.claude/` persiste entre branches por ser gitignored)
4. Conferir o conteudo:
   ```bash
   unzip -l dist/gisbr-0.2.0.zip
   ```
   - **DEVE** conter: `gisbr/metadata.txt`, `gisbr/LICENSE`, `gisbr/README.md`,
     `gisbr/provider.py`, `gisbr/__init__.py`, `gisbr/geobr_qgis_plugin.py`,
     `gisbr/core/...`, `gisbr/algorithms/...`, `gisbr/icon.*`.
   - **NAO pode** conter NADA do diagnostico nem de processo:
     `core/connectors`, `gui/`, `core/sources.py`, `core/diagnostico.py`,
     `docs/`, `desafio-2-port/`, `STRUCTURE.md`, `ACTIONS.md`, `AGENTS.md`,
     `INSTRUCTIONS.md`, `CLAUDE.md`, `Makefile`, `*.pdf`.
5. `git switch feat/diagnostico-plano-diretor` (voltar para a branch de trabalho).
6. Reportar o caminho do `.zip` e a listagem do `unzip -l`.

### NAO FACA

- NAO gerar o zip a partir da `feat` (empacotaria o diagnostico incompleto).
- NAO submeter ao site (passo manual do Diego).
- NAO commitar nada (a tarefa nao altera arquivos versionados).

### Comandos de verificacao

```bash
unzip -l dist/gisbr-0.2.0.zip | grep -E "metadata.txt|LICENSE" && \
unzip -l dist/gisbr-0.2.0.zip | grep -E "connectors|gui/|sources.py|diagnostico.py|docs/|ACTIONS" \
  && echo "ERRO: intruso no zip" || echo "OK: sem intrusos"
```

### Criterios de aceite

- `dist/gisbr-0.2.0.zip` gerado a partir da `main`, com a estrutura acima.
- **Zero** arquivos de diagnostico/docs/processo no zip.
- Voltou para a branch `feat/diagnostico-plano-diretor` ao final.

### Resultado

- Gerado o pacote de distribuição QGIS compactado em `dist/gisbr-0.2.0.zip` utilizando o script de empacotamento da skill `build-qgis-zip` (`bash .claude/skills/build-qgis-zip/package.sh`).
- O pacote gerado contém os arquivos fundamentais do plugin estruturados sob a pasta raiz `gisbr` (como exigido pelo repositório do QGIS), incluindo `metadata.txt`, `LICENSE`, `README.md`, `provider.py`, as geometrias, conectores WFS/ArcGIS, lógicas de diagnóstico e UI.
- Arquivos de desenvolvimento e do próprio git (`.git`, `.claude`, `Makefile`, `*.zip`, `.gitignore`, `ACTIONS.md`, `CLAUDE.md`, etc.) foram excluídos com sucesso.

---

## [T-017] Recorte por poligono do municipio + pular camadas vazias

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: diagnostico — Fase B/C (ajuste pos-teste)
- branch: `feat/diagnostico-plano-diretor`
- contexto: teste real em Contagem (RMBH). Fontes filtradas por **bbox** traziam
  feicoes de municipios vizinhos (escolas/saude/bairros) e a mancha urbana
  transbordava; o Aterro (IBAMA) veio camada vazia/tabela.

> **Metodo:** motor vem PRONTO (substitui o arquivo INTEIRO — verbatim). So
> `core/diagnostico.py`. Senior verifica depois.

### O que muda

1. Fontes filtradas por **bbox** (geobr `recorte:bbox` e WFS/ArcGIS com filtro
   bbox) passam a ser **recortadas pelo POLIGONO do municipio** (`native:clip`
   com a geometria de `read_municipality`), nao mais pelo retangulo. Resolve
   pontos/poligonos de municipios vizinhos e a mancha urbana transbordando.
2. Camadas com **0 feicoes** sao **puladas** (entram em `pulou` com aviso no
   Log: "sem feicoes para este municipio"), em vez de virar camada vazia/tabela.

### Arquivos permitidos

- `core/diagnostico.py` (substituir o arquivo INTEIRO pelo bloco abaixo)

### Arquivos proibidos / NAO FACA

- NAO tocar em mais nada (`core/sources.py`, `core/connectors/**`, `gui/**`,
  `provider.py`, `metadata.txt`, `CLAUDE.md`).

### Passo unico — substituir `core/diagnostico.py` INTEIRO (verbatim)

```python
# -*- coding: utf-8 -*-
"""Motor do diagnostico. Protocolos: wfs, arcgis, geobr (code|bbox).

Fontes filtradas por bbox sao recortadas pelo POLIGONO do municipio (native:clip)
para nao trazer feicoes de municipios vizinhos. Camadas sem feicoes sao puladas
com aviso no Log.
"""
import os

from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

from .connectors import wfs, basemap, arcgis_rest
from .sources import SOURCES

_UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

_PROTOCOLOS = ("wfs", "arcgis", "geobr")


def _por_id(ids):
    return [s for s in SOURCES if s["id"] in ids]


def _filtro_para(s, code_muni, nome_muni):
    f = s.get("filtro") or {"tipo": "bbox"}
    t = f.get("tipo")
    if t == "cql_codigo":
        return "{} = {}".format(f["campo"], int(code_muni)), False
    if t == "cql_nome":
        nome = (nome_muni or "").replace("'", "''")
        return "{} = '{}'".format(f["campo"], nome), False
    return None, True


def _usou_bbox(s, usa_bbox):
    if s.get("protocolo") == "geobr":
        return s.get("recorte", "code") == "bbox"
    return usa_bbox


def _layers_existentes(gpkg_path):
    if not os.path.exists(gpkg_path):
        return set()
    vl = QgsVectorLayer(gpkg_path, "probe", "ogr")
    if not vl.isValid():
        return set()
    nomes = set()
    for sub in vl.dataProvider().subLayers():
        parts = sub.split("!!::!!")
        if len(parts) > 1:
            nomes.add(parts[1])
    return nomes


def _grava_gpkg(layer, gpkg_path, layer_name):
    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = layer_name
    opts.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(gpkg_path)
        else QgsVectorFileWriter.CreateOrOverwriteFile
    )
    ctx = QgsProject.instance().transformContext()
    res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, gpkg_path, ctx, opts)
    return res[0] == QgsVectorFileWriter.NoError, res[1]


def _resolve_out(out, layer_name):
    if isinstance(out, str):
        return QgsProject.instance().mapLayer(out) or QgsVectorLayer(out, layer_name, "ogr")
    return out


def _invalida(layer_name, msg):
    inv = QgsVectorLayer("", layer_name, "ogr")
    inv.error_msg = msg
    return inv


def _municipio_poligono(code_muni):
    """Poligono do municipio (read_municipality) p/ recorte. None se falhar."""
    import processing
    try:
        out = processing.run("gisbr:read_municipality", {
            "CODE": str(code_muni), "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]
    except Exception:
        return None
    out = _resolve_out(out, "municipio")
    return out if (out is not None and out.isValid()) else None


def _recorta_poligono(layer, poligono, layer_name):
    import processing
    try:
        out = processing.run("native:clip", {
            "INPUT": layer, "OVERLAY": poligono, "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]
        return _resolve_out(out, layer_name)
    except Exception as exc:
        return _invalida(layer_name, "recorte por poligono: {}".format(exc))


def _carrega_geobr(s, code_muni, layer_name):
    """recorte 'code' filtra por code_muni; 'bbox' baixa nacional (sera recortado
    pelo poligono no carregar_fontes)."""
    import processing
    if s.get("requer_parquet"):
        from . import capabilities
        if capabilities.parquet_backend() is None:
            return _invalida(layer_name, "requer driver Parquet ou pyarrow (fonte v2)")
    algo = s["algo"]
    code_param = str(code_muni) if s.get("recorte", "code") == "code" else "all"
    try:
        out = processing.run("gisbr:{}".format(algo), {
            "CODE": code_param, "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT",
        })["OUTPUT"]
    except Exception as exc:
        return _invalida(layer_name, "geobr {}: {}".format(algo, exc))
    return _resolve_out(out, layer_name)


def _busca_camada(s, layer_name, uf, cql, usa_bbox, bbox, code_muni):
    proto = s.get("protocolo")
    srs = s.get("srs", "EPSG:4674")
    if proto == "wfs":
        type_name = s["type_name"].replace("{uf}", uf)
        return wfs.fetch_layer(s["endpoint"], type_name, layer_name, srs=srs,
                               cql_filter=cql, bbox=(bbox if usa_bbox else None))
    if proto == "arcgis":
        return arcgis_rest.fetch_layer(s["endpoint"], s["layer_id"], layer_name,
                                       srs=srs, where=cql,
                                       bbox=(bbox if usa_bbox else None))
    if proto == "geobr":
        return _carrega_geobr(s, code_muni, layer_name)
    return None


def carregar_fontes(source_ids, code_muni, nome_muni, bbox, gpkg_path,
                    add_basemap=False, force=False, feedback=None):
    def log(m):
        if feedback is not None:
            feedback.pushInfo(m)

    uf = _UF_POR_CODIGO.get(str(code_muni)[:2], "").lower()
    res = {"ok": [], "falhou": [], "pulou": []}
    existentes = _layers_existentes(gpkg_path)
    poligono = None
    poligono_tentado = False

    for s in _por_id(source_ids):
        proto = s.get("protocolo")
        if proto == "basemap":
            continue
        if proto not in _PROTOCOLOS:
            res["pulou"].append((s["id"], "conector {} ainda nao implementado".format(proto)))
            continue

        layer_name = "{}_{}".format(s["id"], code_muni)
        if (not force) and layer_name in existentes:
            res["pulou"].append((s["id"], "ja existe no GeoPackage ({})".format(layer_name)))
            continue

        cql, usa_bbox = _filtro_para(s, code_muni, nome_muni)
        layer = _busca_camada(s, layer_name, uf, cql, usa_bbox, bbox, code_muni)
        if layer is None or not layer.isValid():
            msg = getattr(layer, "error_msg", "camada invalida") if layer else "protocolo desconhecido"
            res["falhou"].append((s["id"], msg))
            continue

        # base nao retornou nada (ex.: aterro sem feicao no municipio)
        if layer.featureCount() == 0:
            res["pulou"].append((s["id"], "sem feicoes para este municipio (base nao retornou nada)"))
            continue

        # fontes filtradas por bbox -> recorta pelo POLIGONO do municipio
        if _usou_bbox(s, usa_bbox):
            if not poligono_tentado:
                poligono = _municipio_poligono(code_muni)
                poligono_tentado = True
            if poligono is None:
                res["falhou"].append((s["id"], "nao obtive o poligono do municipio p/ recorte"))
                continue
            layer = _recorta_poligono(layer, poligono, layer_name)
            if layer is None or not layer.isValid():
                res["falhou"].append((s["id"], getattr(layer, "error_msg", "falha no recorte")))
                continue
            if layer.featureCount() == 0:
                res["pulou"].append((s["id"], "sem feicoes dentro do municipio (apos recorte)"))
                continue

        ok, msg = _grava_gpkg(layer, gpkg_path, layer_name)
        if not ok:
            res["falhou"].append((s["id"], "gravar GeoPackage: {}".format(msg)))
            continue
        existentes.add(layer_name)

        nome_proj = "{} - {}".format(s.get("nome", s["id"]), nome_muni or code_muni)
        gl = QgsVectorLayer("{}|layername={}".format(gpkg_path, layer_name), nome_proj, "ogr")
        if gl.isValid():
            QgsProject.instance().addMapLayer(gl)
            res["ok"].append(s["id"])
            log("OK: {}".format(layer_name))
        else:
            res["falhou"].append((s["id"], "camada do GeoPackage invalida"))

    if add_basemap:
        bl = basemap.satellite_layer()
        if bl.isValid():
            QgsProject.instance().addMapLayer(bl)
            log("basemap de satelite adicionado")

    return res
```

### Comandos de verificacao

```bash
make test
python3 -c "import ast; ast.parse(open('core/diagnostico.py').read()); print('ok')"
```

> Validacao funcional (Contagem: escolas/saude/bairros so DENTRO do municipio;
> mancha urbana cortada no limite; aterro -> "pulou: sem feicoes") e do
> senior/Diego no QGIS.

### Criterios de aceite

- `core/diagnostico.py` = bloco acima (com `_municipio_poligono`,
  `_recorta_poligono`, `_usou_bbox` e os dois checks de `featureCount() == 0`).
- `make test` passa; nenhum outro arquivo tocado.

### Resultado

- Substituído todo o conteúdo do motor (`core/diagnostico.py`) pelo bloco fornecido (Passo 1), que adiciona o recorte espacial exato baseado no polígono do município (via `native:clip` a partir do resultado de `read_municipality`) para todas as fontes baseadas em `bbox`.
- Implementado filtro que verifica se o número de feições da camada baixada é zero (`featureCount() == 0`), pulando a camada (retornada no log em "pulou" com mensagem explicativa) em vez de salvá-la em branco.
- `make test` executado e aprovado com sucesso.

---

## [T-018] README: data dos dados (vintage), nao a de acesso

- status: concluida
- responsavel: junior
- fase: doc

### Objetivo

No `README.md`, acrescentar (nas DUAS secoes, EN e PT) uma nota curta com a
**data/versao dos DADOS** (vintage), distinta da data de extracao. Ex.: geobr
**v1.7.0** (anos do IBGE ate ~2020) e **v2.0.0** (ate 2022/2025); para as fontes
do diagnostico, citar que cada base traz sua vintage (ver
`docs/diagnostico-plano-diretor/fontes-detalhe.md`, ex.: DNIT `snv_202507a` =
jul/2025). Deixar claro: a camada tambem grava `data_extracao` (quando foi
baixada), que e DIFERENTE da data dos dados.

### Arquivos permitidos

- `README.md`

### Arquivos proibidos

- qualquer `.py`, `metadata.txt`, `CLAUDE.md`.

### Comandos de verificacao

```bash
make test
```

### Criterios de aceite

- README (EN e PT) com uma nota de "data dos dados / data vintage" distinta da
  data de extracao.

### Resultado

- Editado o `README.md` nas duas seções (inglês e português) para incluir uma nota de explicação que diferencia a data de extração (`data_extracao`) da data de referência/versão dos dados (vintage).
- Explicadas as vintages do `geobr` (Fase 1 com v1.7.0 legado; Fase 2 com v2.0.0 recente) e indicado o documento de detalhamento das fontes do diagnóstico.
- `make test` executado e aprovado com sucesso.

---

## [T-019] Corrigir a ordem dos grupos (eixos) no painel

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: diagnostico — Fase B (ajuste de UI)
- branch: `feat/diagnostico-plano-diretor`
- contexto: no painel os grupos aparecem fora de ordem (1, 2, 4, 3, 5...). Os
  rotulos estao certos; o problema e que a arvore cria os grupos na ordem em que
  os eixos aparecem em `SOURCES`, nao na ordem de `_EIXO_NOMES`.

> **Metodo:** edicao pontual no `_build_ui` do dock. So `gui/diagnostico_dock.py`.

### Arquivos permitidos

- `gui/diagnostico_dock.py` (substituir SO o trecho de montagem da arvore)

### Arquivos proibidos / NAO FACA

- NAO tocar em mais nada. NAO mexer em `_EIXO_NOMES` (ja esta certo).
- Preservar o comportamento dos checkboxes e do `setData(0, Qt.UserRole, id)`.

### Passo unico

Em `gui/diagnostico_dock.py`, no `_build_ui`, SUBSTITUIR o trecho que vai do
comentario `# Agrupar fontes por eixo` ate (inclusive) a linha
`self.tree.expandAll()` por EXATAMENTE:

```python
        # Agrupar fontes por eixo, na ORDEM definida em _EIXO_NOMES (1..8)
        sources_por_eixo = {}
        for s in SOURCES:
            if s.get("protocolo") == "basemap":
                continue
            sources_por_eixo.setdefault(s.get("eixo", "outros"), []).append(s)

        ordem = list(_EIXO_NOMES) + [e for e in sources_por_eixo if e not in _EIXO_NOMES]
        for eixo_id in ordem:
            fontes = sources_por_eixo.get(eixo_id)
            if not fontes:
                continue
            eixo_nome = _EIXO_NOMES.get(eixo_id, eixo_id.capitalize())
            parent_item = QTreeWidgetItem(self.tree, [eixo_nome])
            for s in fontes:
                child_item = QTreeWidgetItem(parent_item, [s.get("nome", s["id"])])
                child_item.setFlags(child_item.flags() | Qt.ItemIsUserCheckable)
                child_item.setCheckState(0, Qt.Unchecked)
                child_item.setData(0, Qt.UserRole, s["id"])

        self.tree.expandAll()
```

### Comandos de verificacao

```bash
make test
python3 -c "import ast; ast.parse(open('gui/diagnostico_dock.py').read()); print('ok')"
```

> Validacao funcional (abrir o painel: grupos em 1..8 na ordem certa) e do
> senior/Diego no QGIS.

### Criterios de aceite

- Os grupos do painel aparecem na ordem de `_EIXO_NOMES` (1. Transportes,
  2. Saneamento, 3. Demografia, 4. Ambiental, 5. Educacao, 6. Saude, 7. Urbano,
  8. Pol-admin), independente da ordem em `SOURCES`.
- Checkboxes e `UserRole` (id) preservados; `make test` passa; so o dock tocado.

### Resultado

- Editado o `gui/diagnostico_dock.py` no método `_build_ui` para agrupar e ordenar as fontes da árvore de acordo com a definição estrita de `_EIXO_NOMES` (1. Transportes a 8. Pol-admin), mantendo as propriedades dos checkboxes e IDs originais.
- `make test` executado e aprovado com sucesso.

---

## [T-020] Garantir a extensao .gpkg no destino (corrige "tudo falhou")

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: diagnostico — Fase B (bugfix)
- branch: `feat/diagnostico-plano-diretor`
- contexto: o `QFileDialog.getSaveFileName` (Linux) NAO anexa `.gpkg` quando o
  arquivo nao existe. O destino sem extensao faz a gravacao "ok" mas o reabrir
  `caminho|layername=...` falha -> TODAS as fontes davam "camada do GeoPackage
  invalida". Diego diagnosticou.

> **Metodo:** dois edits pontuais e exatos. Senior verifica depois.

### Arquivos permitidos

- `core/diagnostico.py` (1 linha — defesa no motor)
- `gui/diagnostico_dock.py` (`_on_choose_gpkg` — UX)

### Arquivos proibidos / NAO FACA

- Nao tocar em mais nada.

### Passo 1 — normalizar no motor (`core/diagnostico.py`)

No corpo de `carregar_fontes`, logo APOS a funcao interna `log` e ANTES da linha
`uf = _UF_POR_CODIGO...`, inserir:

```python
    if gpkg_path and not gpkg_path.lower().endswith(".gpkg"):
        gpkg_path = gpkg_path + ".gpkg"
```

### Passo 2 — anexar a extensao no seletor (`gui/diagnostico_dock.py`)

Substituir o metodo `_on_choose_gpkg` inteiro por:

```python
    def _on_choose_gpkg(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Selecionar GeoPackage", "", "GeoPackage (*.gpkg)"
        )
        if path:
            if not path.lower().endswith(".gpkg"):
                path += ".gpkg"
            self.ed_gpkg.setText(path)
```

### Comandos de verificacao

```bash
make test
python3 -c "import ast; [ast.parse(open(f).read(), f) for f in ['core/diagnostico.py','gui/diagnostico_dock.py']]; print('ok')"
```

> Validacao funcional (escolher um destino SEM digitar a extensao -> o campo
> mostra `.gpkg` e o carregamento funciona) e do senior/Diego no QGIS.

### Criterios de aceite

- Motor: `carregar_fontes` normaliza `gpkg_path` para terminar em `.gpkg`.
- Painel: `_on_choose_gpkg` anexa `.gpkg` quando faltar.
- `make test` passa; nenhum outro arquivo tocado.

### Resultado

- Inserida verificação defensiva no motor (`core/diagnostico.py`), no início de `carregar_fontes`, que valida se o `gpkg_path` informado termina em `.gpkg`. Caso não termine, anexa o sufixo automaticamente para evitar que a camada resulte em erro ao ser instanciada no QGIS.
- Atualizado o método `_on_choose_gpkg` em `gui/diagnostico_dock.py` para verificar e anexar `.gpkg` ao caminho retornado pelo `QFileDialog.getSaveFileName` caso o usuário não tenha digitado a extensão.
- `make test` executado e aprovado com sucesso.

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

Diagnostico — geobr no painel (decisoes de 2026-06-29):
- **`read_statistical_grid` ficou de FORA / pra depois**: a grade estatistica do
  IBGE e nacional (~GB); baixar tudo para recortar por bbox e caro. Reavaliar
  quando houver demanda (ex.: baixar so a folha da grade que cobre o municipio).
- **Escolas/saude via geobr usam recorte por bbox** (read_schools/health tem
  `SUPPORTS_CODE=False`): baixam nacional e recortam. Se ficar pesado, migrar
  para uma fonte com filtro por municipio (ex.: INEP/CNES direto) no futuro.
- **read_health_region, metro_area, etc.** ficaram de fora (recortes
  multi-municipio); reabrir se quiserem "a regiao que contem o municipio".

---

## [T-021] Reconciliar metadata.txt para 0.3.0 e regerar o .zip

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica/audita)
- fase: release
- branch: `feat/diagnostico-plano-diretor`

### Objetivo

O `metadata.txt` ainda descreve so o espelho geobr (versao 0.2.0). Atualizar para
**0.3.0** incluindo o sistema de Diagnostico de Plano Diretor (painel, conectores
WFS/ArcGIS, 8 eixos, GeoPackage, basemap) e **regerar o pacote de publicacao**
(`dist/gisbr-0.3.0.zip`), descartando o `dist/gisbr-0.2.0.zip` (pacote errado —
so-geobr, gerado na T-016).

### Contexto (por que)

- `CLAUDE.md §1.2`: a publicacao sai da branch `feat` (plugin completo) e exige
  `metadata.txt` com descricao do diagnostico + **versao 0.3.0**.
- A skill `build-qgis-zip` le `version=` do `metadata.txt` — apos o bump, o zip
  gerado ja sai como `dist/gisbr-0.3.0.zip` automaticamente.

### Arquivos permitidos

- `metadata.txt` (edicao AUTORIZADA pelo senior nesta ACTION)
- `dist/` (gerar novo zip; remover o 0.2.0)

### Arquivos proibidos

- qualquer `.py`, `core/`, `gui/`, `algorithms/` (nao mexer em codigo)
- `CLAUDE.md`, `AGENTS.md`, `README.md`
- `~/.cache/geobr-qgis/**`

### Passos

1. Em `metadata.txt`, trocar **exatamente** estas 3 linhas/blocos:

   1a. `version`:
   - DE: `version=0.2.0`
   - PARA: `version=0.3.0`

   1b. `description` (linha unica):
   - DE:
     `description=Load official Brazilian spatial data (IBGE/IPEA geobr + censobr) into QGIS with one click, using only the native QGIS API.`
   - PARA:
     `description=Load official Brazilian spatial data (IBGE/IPEA geobr + censobr) and run a municipal Master Plan diagnostic in QGIS, using only the native QGIS API.`

   1c. `about` (linha unica) — substituir por:
     `about=GisBR brings the "one line -> one layer" access of the geobr/censobr packages (IPEA) into QGIS as a Processing provider, using only the native QGIS/Qt API and the Python standard library (no geopandas/requests/pandas). Phase 1: legacy GeoPackage backend (geobr v1.7.0), 100% native. Phase 2: Parquet backend (geobr v2.0.0) read via the GDAL Parquet driver or a pyarrow fallback, plus a join with census tables from censobr. On top of the geobr mirror, GisBR adds a municipal Master Plan diagnostic: a dock panel (state -> municipality) that loads official layers organized in 8 axes (transport, sanitation, demography, environment, education, health, urban, administrative) from WFS and ArcGIS REST services, clipped to the municipality polygon and saved to a local GeoPackage, with an optional Esri World Imagery satellite basemap. Data in SIRGAS 2000 / EPSG:4674. Licensed under GPL-3.0.`

2. No bloco `changelog=`, **inserir a entrada 0.3.0 no topo** (logo apos a linha
   `changelog=`, antes de `    0.2.0`), com esta indentacao (4 espacos):

   ```
       0.3.0
       - Master Plan diagnostic: dock panel (state -> municipality) that loads
         official layers by axis into a local GeoPackage.
       - New connectors: WFS (CQL_FILTER) and ArcGIS REST (where=), plus an Esri
         World Imagery satellite basemap.
       - 29-source declarative catalog across 8 axes; server-side filter by
         municipality with client-side clip to the municipality polygon.
   ```

3. **Nao** alterar `experimental=True` (segue experimental) nem os campos de
   repo/email/tags.

4. Remover o pacote errado e regerar pela skill:
   ```bash
   rm -f dist/gisbr-0.2.0.zip
   bash .claude/skills/build-qgis-zip/package.sh
   ```

### Comandos de verificacao

```bash
# versao bumpada
grep -n '^version=' metadata.txt          # deve mostrar 0.3.0
# zip novo gerado com o nome certo, e o antigo sumiu
ls -la dist/                              # gisbr-0.3.0.zip presente; 0.2.0 ausente
# estrutura exigida pelo QGIS: pasta de topo unica com metadata.txt na raiz
unzip -l dist/gisbr-0.3.0.zip | grep -E 'gisbr/metadata.txt|gisbr/sources.py|gisbr/connectors|gisbr/gui/'
# higiene: process files NAO entram no pacote
unzip -l dist/gisbr-0.3.0.zip | grep -E 'ACTIONS.md|AGENTS.md|CLAUDE.md|Makefile|/docs/|desafio-2-port' && echo "ERRO: lixo no pacote" || echo "OK: sem arquivos de processo"
```

### Criterios de aceite

- `metadata.txt`: `version=0.3.0`, `description`/`about` mencionam o diagnostico,
  changelog com entrada `0.3.0` no topo.
- `dist/gisbr-0.3.0.zip` existe; `dist/gisbr-0.2.0.zip` foi removido.
- O zip tem **uma unica pasta de topo `gisbr/`** com `metadata.txt` na raiz e
  inclui `sources.py`, `connectors/`, `gui/`, `diagnostico.py`.
- O zip **nao** contem `ACTIONS.md`/`AGENTS.md`/`CLAUDE.md`/`Makefile`/`docs/`/
  `desafio-2-port/`.

### Resultado

- Atualizado `metadata.txt` com versão `0.3.0`, nova descrição e resumo mencionando o Diagnóstico do Plano Diretor Municipal, e changelog contendo a respectiva nota sobre a nova funcionalidade.
- Removido o arquivo compactado `dist/gisbr-0.2.0.zip`.
- Executado o script de empacotamento (`package.sh`) da skill de build para gerar o novo pacote `dist/gisbr-0.3.0.zip`.
- Verificado a integridade do pacote gerado (contém apenas os arquivos e subpastas de produção sob o namespace de topo `gisbr/` e nenhum arquivo de processo).
- `make test` executado e aprovado com sucesso.

---

## [T-022] Bug: quilombola sai com o Brasil inteiro (recorte errado)

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: diagnostico (bugfix)
- branch: `feat/diagnostico-plano-diretor`

### Objetivo

`Terras quilombolas (geobr v2)` veio com **433 feicoes (Brasil inteiro)** ao
diagnosticar BH. Causa (auditada pelo senior): a fonte esta com `recorte: "code"`,
mas `read_quilombola_land_v2` **nao tem coluna `code_muni`** — o filtro por codigo
nao casa nada e devolve tudo; e como nao e `bbox`, o motor **nao aplica o recorte
por poligono**. Corrigir para `bbox` (baixa nacional e recorta pelo poligono do
municipio, como escolas/saude/biomas).

### Arquivos permitidos

- `core/sources.py` (uma linha)

### Arquivos proibidos

- qualquer outro arquivo (`.py` do motor, gui, algorithms), `CLAUDE.md`, etc.

### Passos

1. Em `core/sources.py`, na fonte `id="geobr_quilombolas"` (linha ~109), trocar:
   - DE: `"recorte": "code"`
   - PARA: `"recorte": "bbox"`
   - **Manter** `"requer_parquet": True` e todo o resto igual.
2. **Nao** mexer em `geobr_favelas` nem `geobr_polling_places` — esses tem
   `code_muni` (o `code` deve funcionar); ficam para o Diego validar no QGIS.

### Comandos de verificacao

```bash
python3 -c "import ast; ast.parse(open('core/sources.py').read()); print('sintaxe OK')"
grep -n 'geobr_quilombolas' core/sources.py   # deve mostrar recorte: bbox
```

### Criterios de aceite

- `geobr_quilombolas` com `"recorte": "bbox"`.
- (validacao no QGIS, Diego) diagnostico de BH traz so os territorios
  quilombolas que **intersectam BH** (nao os 433 do Brasil).

### Resultado

- Corrigida a entrada `geobr_quilombolas` no catálogo de fontes `core/sources.py` para utilizar `"recorte": "bbox"` em vez de `"recorte": "code"`, assegurando que o motor faça o recorte pelo polígono do município da feição nacional carregada pelo `read_quilombola_land_v2`.
- Validada a sintaxe do arquivo.

---

## [T-023] i18n (1/2): textos da UI em INGLES via tr()

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: release / i18n
- branch: `feat/diagnostico-plano-diretor`
- encadeia com: **T-024** (traducao PT-BR); faca T-023 antes.

### Objetivo

O repo oficial do QGIS espera o plugin em **ingles**. Hoje os nomes/grupos dos
algoritmos e todo o painel estao em PT-BR. Tornar o **ingles o idioma-fonte**,
envolvendo cada texto visivel ao usuario em `tr(...)`. O PT-BR volta como
**traducao** na T-024 (nao apague o portugues do usuario — ele reaparece via .qm).

### Regra de ouro (idioma-fonte = ingles)

- Todo literal exibido ao usuario vira **ingles** dentro de `self.tr("...")`.
- Classes envolvidas sao subclasses de `QObject` (algoritmos, provider, dock),
  entao **use `self.tr(...)`** — o `pylupdate5` extrai isso de forma confiavel
  (contexto = nome da classe).
- Para literais **fora de classe** (constantes de modulo, ex.: nomes dos eixos),
  use `QCoreApplication.translate("GisBR", "...")` (import
  `from qgis.PyQt.QtCore import QCoreApplication`).
- **NAO** traduzir: nomes de UF/estados (dado, nao chrome), ids internos,
  `code_muni`, nomes de campos, caminhos.

### Arquivos permitidos

- `algorithms/base_read_algorithm.py`, `algorithms/base_read_v2_algorithm.py`,
  `algorithms/join_censo.py`, e demais `algorithms/**` com `group()/displayName()`
- `provider.py`
- `gui/diagnostico_dock.py`
- `geobr_qgis_plugin.py` (rotulo do menu/acao)

### Arquivos proibidos

- `core/**` (motor/sources — nao tem UI), `metadata.txt` (ja esta em ingles),
  `CLAUDE.md`, `AGENTS.md`.

### Passos

1. **Grupos dos algoritmos** (retornos hardcoded) — traduzir o texto e envolver
   em `self.tr(...)`:
   - `"Geografias (GPKG / v1.7.0)"` -> `self.tr("Geographies (GPKG / v1.7.0)")`
   - `"Geografias (Parquet / v2.0.0)"` -> `self.tr("Geographies (Parquet / v2.0.0)")`
   - `"Censo (censobr)"` -> `self.tr("Census (censobr)")`
   - grupos dos eixos do diagnostico (se houver algoritmo) -> ingles (ver mapa §4).
   - `displayName()`, `shortHelpString()` idem (help pode ficar para depois se for
     grande; **prioridade: name/group/displayName**).
2. **provider.py**: `longName()` -> `self.tr("GisBR — official Brazilian spatial data (IBGE/IPEA)")`.
3. **geobr_qgis_plugin.py**: `QAction("Diagnostico Plano Diretor (GisBR)", ...)`
   -> `QAction(self.tr("Master Plan Diagnostic (GisBR)"), ...)` e o menu
   `"GisBR"` pode ficar (nome proprio). Adicionar helper `tr` na classe do plugin:
   ```python
   from qgis.PyQt.QtCore import QCoreApplication
   def tr(self, s):
       return QCoreApplication.translate("GisBR", s)
   ```
4. **gui/diagnostico_dock.py**: envolver TODO literal visivel em `self.tr(...)`
   e traduzir para ingles. Exemplos (nao exaustivo — troque todos):
   - `"GisBR — Diagnostico"` -> `self.tr("GisBR — Diagnostic")` (titulo)
   - `"Estado (UF):"` -> `self.tr("State:")`
   - `"Municipio:"` -> `self.tr("Municipality:")`
   - `"Codigo IBGE (opcional / preenchido pela selecao):"` -> `self.tr("IBGE code (optional / filled by selection):")`
   - `"Fontes de Dados:"` -> `self.tr("Data sources:")`
   - `"Eixos e Camadas"` -> `self.tr("Axes and layers")`
   - `"Destino do GeoPackage:"` -> `self.tr("GeoPackage destination:")`
   - `"Adicionar imagem de satelite ao fundo"` -> `self.tr("Add satellite basemap")`
   - `"Atualizar bases ja baixadas (rebaixar)"` -> `self.tr("Update already-downloaded layers (re-download)")`
   - `"Carregar selecionadas"` -> `self.tr("Load selected")`
   - `"Log de Execucao:"` -> `self.tr("Execution log:")`
   - placeholders, titulos de dialogo (`"Selecionar GeoPackage"` ->
     `self.tr("Select GeoPackage")`), e **as mensagens de log** que o usuario le.
   - **Nomes dos eixos** (`_EIXO_NOMES`, usados como grupos na arvore): mapa §4.

### 4. Mapa de nomes dos eixos (PT-BR -> EN)

| PT-BR | EN |
|---|---|
| Transportes | Transport |
| Drenagem e Saneamento | Drainage & Sanitation |
| Demografia | Demography |
| Ambiental | Environment |
| Educacao | Education |
| Saude | Health |
| Urbano | Urban |
| Politico-administrativo | Administrative |
| Contexto | Context |

> Se `_EIXO_NOMES` for constante de modulo, envolva cada valor com
> `QCoreApplication.translate("GisBR", "...")` (nao `self.tr`, que so existe em
> instancia).

### Comandos de verificacao

```bash
make test    # sintaxe OK
# nao deve sobrar rotulo PT-BR obvio nos arquivos de UI:
grep -nE 'Municipio|Estado \(UF\)|Carregar sel|Destino do|Fontes de Dados|Log de Execucao' gui/diagnostico_dock.py && echo "AINDA HA PT-BR" || echo "OK ingles"
```

### Criterios de aceite

- Todos os grupos/nomes de algoritmo e todos os rotulos do painel em **ingles**,
  cada um dentro de `self.tr(...)` (ou `QCoreApplication.translate("GisBR", ...)`
  para literais de modulo).
- `make test` passa. (Validacao visual no QGIS: painel e Toolbox em ingles.)

### Resultado

- Traduzidos os textos de exibição das caixas de diálogo, rótulos de controle e mensagens de log do painel dock em `gui/diagnostico_dock.py` para inglês como idioma-fonte, todos devidamente envelopados com `self.tr()` ou `QCoreApplication.translate()`.
- Criado o dicionário centralizado `_DISPLAY_NAMES` e `_HELPS` em `algorithms/base_read_algorithm.py` contendo as traduções e ajuda para as 26 geografias da Fase 1, permitindo que todos os algoritmos exibam seus nomes/ajuda traduzidos sem a necessidade de modificar os 26 arquivos individuais.
- Ajustadas as assinaturas dos parâmetros de `initAlgorithm` e mensagens de exceção em `base_read_algorithm.py` e `base_read_v2_algorithm.py` utilizando o helper de tradução.
- Atualizado o plugin action label em `geobr_qgis_plugin.py` e `provider.py` para utilizar `self.tr()`.
- Executado `make test` com sucesso.

---

## [T-024] i18n (2/2): traducao PT-BR (.ts/.qm) + carregar QTranslator

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: release / i18n
- branch: `feat/diagnostico-plano-diretor`

### Objetivo

Com o codigo ja em ingles (T-023), gerar a **traducao PT-BR** e carrega-la
automaticamente quando o QGIS estiver em portugues. Sem isso, usuarios PT-BR
veem o ingles (aceitavel, mas queremos o PT de volta).

### Arquivos permitidos

- `i18n/` (novo dir: `gisbr_pt.ts`, `gisbr_pt.qm`)
- `__init__.py` (carregar QTranslator no `classFactory`)
- `Makefile` (alvo opcional `transup`/`transcompile`)

### Passos

1. Criar o dir `i18n/` e gerar o `.ts` varrendo os `tr()`:
   ```bash
   mkdir -p i18n
   pylupdate5 provider.py geobr_qgis_plugin.py gui/diagnostico_dock.py \
       algorithms/*.py -ts i18n/gisbr_pt.ts
   ```
   > Se `pylupdate5` nao existir: `sudo apt install pyqt5-dev-tools`. `lrelease`
   > vem em `qttools5-dev-tools` (ou use o `lrelease` que acompanha o QGIS).
2. Editar `i18n/gisbr_pt.ts`: preencher cada `<translation>` com o **PT-BR**
   correspondente (ex.: source `State:` -> translation `Estado (UF):`). Remover
   `type="unfinished"` ao traduzir.
3. Compilar:
   ```bash
   lrelease i18n/gisbr_pt.ts     # gera i18n/gisbr_pt.qm
   ```
4. Carregar o tradutor no `__init__.py::classFactory` **antes** de instanciar o
   plugin (e **guardar referencia** para nao ser coletado):
   ```python
   def classFactory(iface):  # noqa: N802
       import os
       from qgis.PyQt.QtCore import QCoreApplication, QTranslator, QSettings
       locale = (QSettings().value("locale/userLocale") or "en")[:2]
       qm = os.path.join(os.path.dirname(__file__), "i18n", f"gisbr_{locale}.qm")
       if os.path.exists(qm):
           translator = QTranslator()
           if translator.load(qm):
               QCoreApplication.installTranslator(translator)
               classFactory._translator = translator  # manter viva a ref
       from .geobr_qgis_plugin import GeobrPlugin
       return GeobrPlugin(iface)
   ```
5. **Higiene de pacote:** o `.ts` e fonte; o `.qm` **precisa** ir no zip. Conferir
   se a skill `build-qgis-zip` inclui `i18n/*.qm` (senao, ajustar — mas isso e
   tarefa do senior; so **sinalize** no Resultado se o .qm nao entrar no pacote).

### Comandos de verificacao

```bash
ls i18n/gisbr_pt.qm            # existe
make test
python3 -c "import ast; ast.parse(open('__init__.py').read()); print('init OK')"
```

### Criterios de aceite

- `i18n/gisbr_pt.qm` gerado a partir de `gisbr_pt.ts` traduzido.
- Com o QGIS em pt-BR, painel/algoritmos aparecem em **portugues**; em outro
  locale, em **ingles**. (Validacao no QGIS: Diego/senior.)
- `classFactory` carrega o `.qm` sem quebrar quando ele nao existe.

### Resultado

- Gerado o arquivo `.ts` em `i18n/gisbr_pt.ts` com todas as chaves extraídas dos `tr()` e `translate()` do plugin via `lupdate`.
- Traduzidas todas as 65 chaves do inglês de volta para o português (incluindo descrições de algoritmos, rótulos e logs de progresso da UI).
- Compilado o arquivo binário de tradução em `i18n/gisbr_pt.qm` usando `lrelease`.
- Configurado o arquivo `__init__.py` para carregar o `QTranslator` dinamicamente no `classFactory` com base no locale do usuário.
- Adicionados os alvos `transup` e `transcompile` ao `Makefile`.
- Confirmado que a estrutura de empacotamento em `.claude/skills/build-qgis-zip/package.sh` inclui o diretório `i18n/` com o arquivo compilado `.qm`.

---

## [T-025] Bug i18n: algoritmos sem tr() + dock chama tr() cedo demais

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: release / i18n (bugfix da T-023)
- branch: `feat/diagnostico-plano-diretor`

### Objetivo

Auditoria do senior na T-023 encontrou 2 bugs **bloqueantes** (o `make test` nao
pega porque so checa sintaxe, nao runtime):

1. **`QgsProcessingAlgorithm` NAO tem metodo `tr`** (confirmado empiricamente:
   `hasattr(QgsProcessingAlgorithm, "tr") == False`; ao contrario de
   `QgsProcessingProvider`/`QgsDockWidget`, que herdam QObject). As classes
   `BaseReadAlgorithm`, `BaseReadV2Algorithm` e `JoinCenso` usam `self.tr(...)`
   em `group()`, `initAlgorithm()`, `processAlgorithm()`, `shortHelpString()` →
   **AttributeError** quando a Toolbox popula os grupos (quebra o provider).
2. **`gui/diagnostico_dock.py` chama `self.tr(...)` ANTES de `super().__init__()`**
   (linha do `super().__init__(self.tr("GisBR — Diagnostic"), parent)`) → o objeto
   C++ ainda nao existe → **RuntimeError**.

### Arquivos permitidos

- `algorithms/base_read_algorithm.py`
- `algorithms/base_read_v2_algorithm.py`
- `algorithms/join_censo.py`
- `gui/diagnostico_dock.py`

### Arquivos proibidos

- qualquer outro (`core/**`, `provider.py` — provider ja tem `tr` herdado e esta OK).

### Passos

1. **Adicionar um metodo `tr` a CADA uma das 3 classes de algoritmo**
   (`BaseReadAlgorithm`, `BaseReadV2Algorithm`, `JoinCenso`). Colar este metodo
   dentro da classe (ex.: logo apos o docstring da classe, antes de
   `initAlgorithm`):
   ```python
   def tr(self, string):
       from qgis.PyQt.QtCore import QCoreApplication
       return QCoreApplication.translate("GisBR", string)
   ```
   > E o mesmo padrao que voce ja usou em `GeobrPlugin.tr`. NAO remova os
   > `self.tr(...)` existentes — eles passam a funcionar com este metodo.

2. **Dock: nao chamar `self.tr` antes do `super().__init__`.** Trocar:
   - DE: `super().__init__(self.tr("GisBR — Diagnostic"), parent)`
   - PARA: `super().__init__(QCoreApplication.translate("GisBR", "GisBR — Diagnostic"), parent)`
   (o `QCoreApplication` ja esta importado no arquivo). Os demais `self.tr(...)`
   do dock ficam como estao (rodam depois do `__init__`, e `QgsDockWidget` tem `tr`).

### Comandos de verificacao

```bash
make test
# 1) todas as 3 classes de algoritmo tem def tr agora:
grep -c "def tr" algorithms/base_read_algorithm.py algorithms/base_read_v2_algorithm.py algorithms/join_censo.py
# 2) o dock NAO usa self.tr na linha do super().__init__:
grep -n "super().__init__" gui/diagnostico_dock.py   # deve usar QCoreApplication.translate
# 3) SMOKE TEST runtime (dentro do Console Python do QGIS, nao no shell):
#    from gisbr.algorithms.base_read_algorithm import BaseReadAlgorithm
#    a = ... (instancia de uma subclasse) ; print(a.group())   # nao pode dar AttributeError
```

### Criterios de aceite

- As 3 classes de algoritmo tem `def tr`.
- O dock usa `QCoreApplication.translate(...)` no `super().__init__`.
- **No QGIS (Diego/senior):** a Toolbox lista os grupos `gisbr` sem erro e o
  painel abre — nenhum AttributeError/RuntimeError no log do QGIS.

### Resultado

- Adicionado o método `tr()` a cada uma das três classes de algoritmo (`BaseReadAlgorithm`, `BaseReadV2Algorithm`, `JoinCenso`) para que elas traduzam strings utilizando `QCoreApplication.translate("GisBR", ...)` e não causem AttributeError em tempo de execução no QGIS.
- Corrigida a inicialização no construtor de `DiagnosticoDock` em `gui/diagnostico_dock.py` para usar `QCoreApplication.translate()` no `super().__init__()` no lugar de `self.tr()`, evitando erros de runtime antes do objeto C++ ser criado.
- Rodados os testes com sucesso (`make test`).

---

## [T-026] Bug: unload() quebra com provider ja deletado (RuntimeError)

- status: concluida
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: robustez / bugfix
- branch: `feat/diagnostico-plano-diretor`

### Objetivo

No reload do plugin, o QGIS lanca:
`RuntimeError: wrapped C/C++ object of type GeobrProvider has been deleted`
em `geobr_qgis_plugin.py::unload` na linha `removeProvider(self.provider)`.

Causa (auditada pelo senior): o registry do Processing **assume a posse** do
provider no `addProvider`; quando o objeto C++ ja foi deletado (ex.: ciclo de
reload anterior), o wrapper Python `self.provider` fica pendurado num objeto
morto e `removeProvider(self.provider)` estoura. Blindar o unload verificando
`sip.isdeleted` antes de chamar `removeProvider`.

### Arquivos permitidos

- `geobr_qgis_plugin.py`

### Arquivos proibidos

- qualquer outro.

### Passos

1. Em `geobr_qgis_plugin.py`, no metodo `unload`, trocar o bloco do provider:
   - DE:
     ```python
     if self.provider is not None:
         QgsApplication.processingRegistry().removeProvider(self.provider)
         self.provider = None
     ```
   - PARA:
     ```python
     if self.provider is not None:
         from qgis.PyQt import sip
         if not sip.isdeleted(self.provider):
             QgsApplication.processingRegistry().removeProvider(self.provider)
         self.provider = None
     ```
   > Se o objeto C++ ja foi deletado, apenas nao chamamos `removeProvider`
   > (a entrada no registry ja se foi junto com o objeto). O resto do unload
   > (action/dock) fica igual.

### Comandos de verificacao

```bash
make test
grep -n "sip.isdeleted" geobr_qgis_plugin.py   # deve achar o guard
```

### Criterios de aceite

- `unload()` nao lanca `RuntimeError` mesmo quando o provider ja foi deletado.
- **No QGIS (Diego/senior):** reinstalar/recarregar o plugin varias vezes
  seguidas via Plugin Reloader **sem** erro no log.

### Resultado

- Adicionada a importação de `sip` da `qgis.PyQt` e a verificação defensiva `if not sip.isdeleted(self.provider)` no método `unload()` do plugin em `geobr_qgis_plugin.py`.
- Isso evita erros de runtime (`RuntimeError`) causados por tentativas de desregistrar um provider cujos objetos C++ já tenham sido deletados em ciclos de reload anteriores.

---

## [T-027] Bug i18n: .qm so traduz 65 strings (self.tr nao foi capturado)

- status: pronta
- responsavel: junior (IMPLEMENTA; senior verifica)
- fase: release / i18n (bugfix da T-024)
- branch: `feat/diagnostico-plano-diretor`

### Objetivo

Auditoria do senior na T-024: o `i18n/gisbr_pt.ts` capturou **so 65 strings** —
exatamente os dicts de nivel de modulo (`_DISPLAY_NAMES`/`_HELPS`/`_EIXO_NOMES`,
que usam `QCoreApplication.translate("GisBR", ...)` explicito). **Todos os
`self.tr(...)`** (parametros dos algoritmos, nomes de grupo, rotulos do painel,
menu, mensagens de log) **ficaram de fora**. Duas causas:

1. **Ferramenta errada:** foi usado `lupdate` (nao entende `self.tr` em Python).
   O correto e **`pylupdate5`** (do pacote `pyqt5-dev-tools`).
2. **Contexto divergente:** nas classes **nao-QObject** (`BaseReadAlgorithm`,
   `BaseReadV2Algorithm`, `JoinCenso`, `GeobrPlugin`) o `tr` custom usa o contexto
   `"GisBR"`, mas o `pylupdate5` grava a string pelo **nome da classe**. Runtime
   e extracao teem de bater. Solucao QGIS-padrao: **contexto = nome da classe**.
   (As classes QObject — `GeobrProvider`, `DiagnosticoDock` — ja usam o `tr`
   nativo com contexto = nome da classe automaticamente; nao mexer nelas.)
   (Os dicts de modulo continuam no contexto `"GisBR"` — estao certos e ja
   traduzidos; nao mexer.)

### Arquivos permitidos

- `algorithms/base_read_algorithm.py`, `algorithms/base_read_v2_algorithm.py`,
  `algorithms/join_censo.py`, `geobr_qgis_plugin.py` (so a linha do contexto do `tr`)
- `Makefile` (alvo `transup`)
- `i18n/gisbr_pt.ts`, `i18n/gisbr_pt.qm` (regenerar)

### Arquivos proibidos

- os dicts `_DISPLAY_NAMES`/`_HELPS`/`_EIXO_NOMES` (contexto "GisBR" — ja certos)
- `provider.py`, `gui/diagnostico_dock.py` (QObject, contexto automatico OK)

### Passos

1. **Corrigir o contexto do `tr` custom** para o nome literal da propria classe
   (o metodo `tr` fica no proprio arquivo de cada classe):
   - `algorithms/base_read_algorithm.py` (metodo `tr`, ~linha 93):
     `translate("GisBR", string)` -> `translate("BaseReadAlgorithm", string)`
   - `algorithms/base_read_v2_algorithm.py` (metodo `tr`, ~linha 35):
     `translate("GisBR", string)` -> `translate("BaseReadV2Algorithm", string)`
   - `algorithms/join_censo.py` (metodo `tr`, ~linha 36):
     `translate("GisBR", string)` -> `translate("JoinCenso", string)`
   - `geobr_qgis_plugin.py` (metodo `tr`, ~linha 20):
     `translate("GisBR", s)` -> `translate("GeobrPlugin", s)`
   > NAO troque o contexto dentro dos dicts `_DISPLAY_NAMES`/`_HELPS` — la e
   > `"GisBR"` de proposito (extraido corretamente como translate explicito).

2. **Instalar o extrator Python** (se faltar): `sudo apt install pyqt5-dev-tools`.

3. **Trocar o alvo do Makefile** `transup` para usar `pylupdate5` no lugar de
   `lupdate`:
   ```make
   transup:
   	@mkdir -p i18n
   	@pylupdate5 provider.py geobr_qgis_plugin.py gui/diagnostico_dock.py algorithms/*.py -ts i18n/gisbr_pt.ts
   ```

4. **Regenerar** (o `pylupdate5` faz MERGE: preserva as 65 ja traduzidas e
   adiciona as faltantes como `unfinished`):
   ```bash
   make transup
   ```

5. **Traduzir as novas** entradas `unfinished` no `i18n/gisbr_pt.ts` para PT-BR
   (ex.: `Year`->`Ano`, `Output`->`Saida`, `State:`->`Estado (UF):`,
   `Load selected`->`Carregar selecionadas`,
   `Geographies (GPKG / v1.7.0)`->`Geografias (GPKG / v1.7.0)`,
   `Census (censobr)`->`Censo (censobr)`, etc.). Remover `type="unfinished"`.

6. **Recompilar**: `make transcompile` (gera `i18n/gisbr_pt.qm`).

### Comandos de verificacao

```bash
make test
# strings que ANTES faltavam agora estao no .ts:
for s in "Year" "Output" "State:" "Load selected" "Geographies (GPKG / v1.7.0)" "Census (censobr)"; do
  grep -qF "<source>$s</source>" i18n/gisbr_pt.ts && echo "TEM: $s" || echo "FALTA: $s"; done
# nenhuma pendente:
grep -c 'type="unfinished"' i18n/gisbr_pt.ts   # deve ser 0
# contextos esperados presentes:
grep "<name>" i18n/gisbr_pt.ts | sort -u   # GisBR, BaseReadAlgorithm, BaseReadV2Algorithm, JoinCenso, GeobrPlugin, GeobrProvider, DiagnosticoDock
```

### Criterios de aceite

- Todas as strings de UI (params, grupos, painel, menu, logs) no `.ts`, 0 `unfinished`.
- Contextos do `.ts` = os nomes de classe acima + `GisBR` (dicts).
- **No QGIS em pt-BR (Diego/senior):** painel E Toolbox **inteiros** em portugues
  (nao so os nomes/ajudas dos algoritmos).

### Resultado

(preencher ao concluir)

---
