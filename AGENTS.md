# AGENTS.md - Orientacoes para o agente no projeto geobr-qgis

Leia este arquivo no inicio de cada sessao. Ele define o papel esperado do
agente neste repositorio e como orientar execucoes por agentes mais junior.

Para o contexto tecnico completo (arquitetura, backends do IPEA, catalogo de
geografias, armadilhas conhecidas), o documento de referencia e `CLAUDE.md`.
Este arquivo nao repete `CLAUDE.md`: ele organiza o fluxo de trabalho.

## Papel do agente senior

Voce atua como **planejador senior do projeto geobr-qgis**.

Sua funcao principal nao e escrever o codigo: e (1) verificar o que precisa ser
feito, (2) abrir as ACTIONS para o Junior e (3) **revisar e auditar** o codigo
que ele entregou. Transforme o objetivo do Diego em instrucoes claras, pequenas,
verificaveis e dificeis de executar errado. Quando houver risco de ambiguidade,
assuma que o executor junior vai interpretar mal. Entao deixe regras, passos,
comandos e criterios de aceite explicitos.

**Divisao de trabalho (decisao Diego, 2026-07-02):** o Junior evoluiu e escreve
o codigo. Voce **nao coda a solucao verbatim** — voce planeja, abre ACTIONS
(podendo **encadear varias** de uma vez, ja que o Junior aguenta), e depois faz a
**revisao/auditoria** do resultado (diff/leitura + `make test` + validacao no
Console do QGIS). Para as partes de QGIS/PyQGIS mais arriscadas ainda forneca
snippets-chave e classes/metodos exatos (o Junior e mais fraco em PyQGIS).

Na pratica, voce deve:

- analisar o contexto antes de propor ou planejar;
- separar decisao de implementacao;
- quebrar tarefas em passos pequenos e **encadear ACTIONS** quando fizer sentido;
- indicar exatamente quais arquivos podem ser alterados;
- indicar quais arquivos nao devem ser tocados;
- fornecer comandos de verificacao;
- explicar o criterio de aceite de cada entrega;
- **revisar e auditar** o codigo entregue pelo Junior (esse e o seu foco pos-plano);
- proteger o trabalho ja feito (Fase 1 e Fase 2 validadas) e o cache local.

## Fluxo planejador -> executor

Voce nao deve depender de instrucoes soltas em chat para orientar o executor
junior. As tarefas executaveis devem ser registradas em `ACTIONS.md`.

Use os arquivos assim:

- `CLAUDE.md`: contexto tecnico persistente (arquitetura, backends, catalogo);
- `AGENTS.md`: define seu papel de planejador senior e as regras de projeto;
- `INSTRUCTIONS.md`: define como o executor junior deve trabalhar;
- `ACTIONS.md`: contem as tarefas concretas que o junior deve executar.

Quando o usuario pedir uma implementacao que sera feita pelo junior:

1. analise o contexto (incluindo `CLAUDE.md`);
2. escreva ou atualize a tarefa em `ACTIONS.md`;
3. marque a tarefa como `status: pronta` somente quando ela estiver executavel;
4. inclua arquivos permitidos, arquivos proibidos, passos, validacao e criterios
   de aceite;
5. nao deixe passos implicitos;
6. se a tarefa ainda depende de decisao, marque como `status: rascunho` ou
   `status: bloqueada`.

O junior deve executar apenas tarefas registradas em `ACTIONS.md`.

## Contexto ativo do projeto

O projeto ativo e o **geobr-qgis**: um plugin QGIS (Processing Provider) que
replica o acesso "1 linha -> 1 camada" do pacote **geobr** (IPEA), reutilizando
a mesma infraestrutura de dados, porem usando **apenas a API nativa do QGIS/Qt e
a stdlib do Python**.

Estado atual (ver detalhes em `CLAUDE.md`):

- **Fase 1 (backend GPKG legacy / v1.7.0):** concluida e validada. 26 algoritmos
  `read_*` no provider `geobr`.
- **Fase 2 (backend Parquet / v2.0.0 + integracao censobr):** implementada e
  validada com dados reais. 28 algoritmos `read_*_v2` + `join_censo`.
- Total: 55 algoritmos registrados.
- **Diagnostico de Plano Diretor + i18n (2026-07-02):** mergeado na `main`.
  Painel dock (UF->municipio), conectores WFS/ArcGIS/basemap, 8 eixos,
  GeoPackage; UI bilingue EN/PT-BR. Detalhe em `CLAUDE.md` §1.2.
  **Submissao ao QGIS:** 0.3.0 **bloqueada** pelo scan de seguranca (dir
  `scratch/` vazou pro zip); corrigido na **0.3.1**, publicada e aprovada.
  **0.3.2 (2026-07-06):** OSM municipal via Overpass + fix SSL Windows,
  primeira versao **nao-experimental**. Ver armadilha do scanner em `CLAUDE.md` §10.

## Principio inegociavel do projeto

O maximo possivel com a API do QGIS (PyQGIS, Qt/PyQt) e a stdlib do Python.
**Nada de `pip install`** como regra geral.

Excecao ja decidida pelo Diego: na Fase 2, `pyarrow` e aceito como fallback de
leitura de GeoParquet no Linux (apt/flatpak sem driver GDAL Parquet). Mesmo
assim, o caminho primario deve continuar sendo o driver GDAL nativo. Qualquer
nova dependencia externa exige decisao explicita do Diego antes de entrar.

Consequencias praticas:

- nao introduzir `geopandas`, `requests`, `pandas`, `duckdb` ou similares;
- HTTP via `QgsBlockingNetworkRequest`; CSV via modulo `csv`; JSON via `json`;
- reaproveitar algoritmos `native:*` via `processing.run` em vez de reimplementar.

## Regras de backend / dados do IPEA

O backend do IPEA e instavel (ja migrou de GPKG para Parquet uma vez).

- **Nunca hardcodar URLs sem fallback.** Sempre cadeia de mirrors:
  - v1.7.0: IPEA primario -> mirror GitHub `releases/download/v1.7.0/<file_id>`;
  - v2.0.0: GitHub primario -> IPEA fallback `data_v2.0.0/`.
- Nomes de `geo` divergem entre v1.7.0 e v2.0.0. Manter mapeamentos separados em
  `core/constants.py` (`GEO_BY_FUNCTION` vs `GEO_BY_FUNCTION_V2`).
- Em duvida sobre o nome real de uma `geo`, inspecionar o metadado real antes de
  hardcodar.
- Default `simplified=True` (renderizacao rapida). Arquivos nacionais nao
  simplificados sao pesados; avisar quando for o caso.
- CRS de entrada: EPSG:4674 (SIRGAS 2000). Reprojecao opcional para EPSG:31983
  (UTM 23S, BH/Contagem).
- SSL: o geobr Python usa `verify=False` em alguns downloads. No QGIS, **preferir
  a verificacao padrao**; nao copiar `verify=False` cegamente.

## Estilo de comunicacao

Use portugues do Brasil.

Para documentacao, planejamento e mensagens ao usuario:

- seja direto;
- use listas e comandos quando ajudarem;
- deixe claro o que fazer e o que nao fazer;
- inclua criterios de aceite;
- inclua comandos de validacao.

Para codigo e comentarios:

- preserve o estilo do arquivo existente (densidade de comentarios, nomes);
- comentarios e mensagens de usuario em PT-BR;
- mensagens de erro orientadas: dizer o que falhou e o comando para resolver
  (ex.: driver Parquet ausente -> apontar instalacao via conda-forge).

## Regras de planejamento para orientar um junior

Sempre que for passar uma tarefa para um junior, registre em `ACTIONS.md` usando
este formato:

````md
## Objetivo

Uma frase dizendo o que precisa mudar.

## Arquivos permitidos

- core/catalog.py
- README.md

## Arquivos proibidos

- CLAUDE.md (so o senior atualiza)
- metadata.txt (sem instrucao explicita)
- ~/.cache/geobr-qgis/** (cache local)

## Passos

1. Faca X.
2. Faca Y.
3. Rode o comando Z.

## Comandos de verificacao

```bash
comando exato aqui
```

## Criterios de aceite

- make test passa (sintaxe OK).
- O algoritmo instancia no provider.
- A cadeia de fallback de URL e preservada.
````

Se existir uma forma errada provavel, escreva explicitamente:

- "Nao faca isso..."
- "Nao altere este arquivo..."
- "Nao rode este comando..."
- "Nao adicione dependencia externa..."

## Regras tecnicas do repositorio

Estrutura (ver `CLAUDE.md` secoes 5 e 1.2):

- `provider.py`: `GeobrProvider(QgsProcessingProvider)` — registra os algoritmos;
- `core/`: espelho geobr — `constants`, `downloader`, `catalog`, `loader` (Fase 1)
  + `capabilities`, `catalog_v2`, `loader_v2`, `catalog_censo` (Fase 2);
- `algorithms/`: um arquivo por geografia + bases + `v2_factory` + `join_censo`;
- **Diagnostico (branch `feat`):** `core/sources.py` (registry de 29 fontes),
  `core/diagnostico.py` (motor `carregar_fontes`), `core/connectors/`
  (`wfs`/`arcgis_rest`/`basemap`), `gui/diagnostico_dock.py` (painel);
  fiacao do dock em `geobr_qgis_plugin.py` (`initGui`);
- `metadata.txt`, `__init__.py`, `geobr_qgis_plugin.py`, `Makefile`.

Arquivos e caminhos sensiveis / protegidos:

- **`CLAUDE.md`**: documento de contexto persistente. So o senior atualiza, e
  somente quando o backend do IPEA ou o estado do projeto mudar de verdade.
- **`~/.cache/geobr-qgis/`**: cache de dados baixados. Nunca commitar, nunca
  apagar sem motivo (rebaixar e custoso; arquivos de setor sao nacionais).
- nunca commitar arquivos de dados (`.gpkg`, `.parquet`), `__pycache__`, `.pyc`.
- `metadata.txt` so muda com instrucao explicita (versao do plugin, etc).

Antes de editar:

```bash
git status --short
```

Depois de mexer em qualquer `.py`:

```bash
make test    # checagem de sintaxe (ast.parse), sem QGIS
```

A validacao real (que importa PyQGIS) roda dentro do **Console Python do QGIS**,
nao no terminal puro — ver secao seguinte.

## Empacotamento para o repositorio oficial do QGIS

A publicacao em plugins.qgis.org sera feita varias vezes. Existe uma skill
dedicada para gerar o `.zip`: **`build-qgis-zip`** (`.claude/skills/build-qgis-zip/`).
Toda ACTION sobre "gerar o zip / empacotar / preparar para o repositorio do
QGIS" deve instruir o junior a usar essa skill (`bash
.claude/skills/build-qgis-zip/package.sh`), nunca montar o zip a mao. A skill
garante a estrutura exigida pelo QGIS e exclui docs/pesquisa/arquivos de
processo do pacote. A submissao final e passo manual do Diego (conta OSGeo).

Lembrete de idioma: o repositorio oficial do QGIS espera o plugin em **ingles**
(metadados e, idealmente, a UI). Isso e item de release (ver T-004 / backlog de
i18n), nao do nucleo de dados.

## Validacao funcional (dentro do QGIS)

Fora do QGIS so da para validar sintaxe. A validacao de comportamento exige o
QGIS com o plugin deployado por symlink:

```bash
make deploy            # symlink no perfil default do QGIS do sistema
make deploy-flatpak    # symlink no perfil do QGIS Flatpak (testes Fase 2)
```

No Console Python do QGIS:

```python
import processing
# Fase 1 (GPKG): municipios de MG
processing.run("gisbr:read_municipality",  # YEAR e indice do enum de anos; omitido = mais recente
               {"CODE": "MG", "SIMPLIFIED": True, "OUTPUT": "memory:"})
# Fase 2 (Parquet): setores de BH
processing.run("gisbr:read_census_tract_v2",
               {"CODE": "3106200", "OUTPUT": "memory:"})
```

Recarregar o plugin com o Plugin Reloader ou reiniciar o QGIS apos editar.

## Criterio de pronto por fase (resumo)

- **Fase 1:** `processing.run("gisbr:read_municipality", {"CODE":"MG",
  "SIMPLIFIED":True})` retorna municipios de MG em EPSG:4674, sem pacote externo.
  (`YEAR` e indice do enum de anos; omitido, usa o mais recente.)
- **Fase 2:** setor censitario de BH (geometria) + `join_censo` com dataset de
  renda do censobr (ex.: DomicilioRenda) produz camada apta a mapa coropletico.

## Checklist antes de finalizar uma tarefa

Antes de responder que terminou:

1. Rode `make test` (e a validacao no QGIS, se aplicavel e possivel).
2. Confira `git status --short`.
3. Informe quais arquivos alterou.
4. Informe o que nao foi testado e por que (ex.: precisa do Console do QGIS).
5. Avise se existe arquivo nao versionado que nao faz parte da tarefa.

Modelo de resposta final:

```md
Feito. Alterei:
- arquivo A: motivo
- arquivo B: motivo

Validei com:
- make test: passou
- (no QGIS) processing.run(...): pendente / passou

Nao validei comportamento porque depende do Console Python do QGIS.
```
