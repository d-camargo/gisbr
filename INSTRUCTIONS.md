# INSTRUCTIONS.md - Como o executor junior deve trabalhar

Este arquivo e para o agente ou desenvolvedor junior que vai executar tarefas no
projeto geobr-qgis.

Voce nao e o planejador. Voce e o executor.

Sua responsabilidade e implementar exatamente a tarefa recebida, com o menor
escopo possivel, validando o resultado e reportando o que foi feito. Se a tarefa
estiver ambigua, pare e peca esclarecimento antes de inventar uma solucao.

## Regra principal

Siga a tarefa registrada pelo planejador senior em `ACTIONS.md`.

Nao adicione funcionalidades extras.
Nao reestruture arquivos sem pedido.
Nao mude documentacao fora do escopo.
Nao "melhore" textos, fluxos ou arquitetura por conta propria.
Nao corrija problemas que voce encontrou se eles nao bloqueiam a tarefa.

Se achar um problema fora do escopo, registre no final como observacao.

## O principio inegociavel do projeto

Este plugin usa **apenas PyQGIS (Qt/PyQt) + stdlib do Python**. **Nao instale
dependencias com pip.**

- nao introduza `geopandas`, `requests`, `pandas`, `duckdb` ou similares;
- HTTP via `QgsBlockingNetworkRequest`; CSV via `csv`; JSON via `json`;
- reaproveite algoritmos `native:*` via `processing.run`.

Unica excecao ja aprovada: `pyarrow` como fallback de leitura de GeoParquet na
Fase 2. Nao use isso como porta para outras libs. Qualquer dependencia nova
exige autorizacao explicita do Diego — pare e pergunte.

## Ordem obrigatoria de execucao

Execute sempre nesta ordem:

1. Leia a tarefa inteira antes de mexer em qualquer arquivo.
2. Leia `ACTIONS.md` e identifique a tarefa marcada como `status: pronta`.
3. Leia `INSTRUCTIONS.md`.
4. Leia `AGENTS.md` e `CLAUDE.md` apenas para contexto e regras do projeto.
5. Confira o estado do git.
6. Leia apenas os arquivos permitidos pela tarefa.
7. Confirme mentalmente quais arquivos sao proibidos.
8. Faca a menor alteracao possivel.
9. Rode os comandos de validacao indicados.
10. Confira `git status --short`.
11. Preencha o resultado da tarefa em `ACTIONS.md`, se a tarefa pedir isso.
12. Responda com resumo objetivo.

Nao execute tarefas que nao estejam em `ACTIONS.md`.
Nao execute tarefas com `status: rascunho`, `status: bloqueada` ou
`status: concluida`.

Comando inicial obrigatorio:

```bash
git status --short
```

## Arquivos e diretorios protegidos

Nao altere estes caminhos, a menos que a tarefa permita explicitamente:

- `CLAUDE.md` (documento de contexto persistente — so o senior atualiza);
- `metadata.txt` (sem instrucao explicita);
- `provider.py` (registro de algoritmos — so com instrucao explicita);
- `~/.cache/geobr-qgis/**` (cache de dados baixados — nunca apagar nem commitar);
- `__pycache__/**` e `*.pyc`;
- qualquer arquivo de dados (`.gpkg`, `.parquet`).

Nunca commite arquivos de dados, cache ou bytecode. O `.gitignore` ja cobre
`__pycache__/`, `*.py[cod]` e `.claude/`.

## Como editar

Faca edicoes pequenas.

Preferencias:

- preserve o estilo do arquivo existente;
- mantenha portugues do Brasil em comentarios e mensagens de usuario;
- nao misture refatoracao com funcionalidade;
- nao renomeie funcoes ou arquivos sem necessidade;
- nao apague codigo que ainda pode ser usado, salvo instrucao explicita;
- mensagens de erro devem ser orientadas (dizer o que falhou e como resolver).

Ao mexer em download/catalogo:

- preserve sempre a cadeia de fallback de URL (mirror IPEA <-> GitHub);
- nao hardcode URL sem fallback;
- respeite os mapeamentos de `geo` separados por backend (`GEO_BY_FUNCTION` v1 x
  `GEO_BY_FUNCTION_V2` v2 em `core/constants.py`);
- nao use `verify=False` para SSL.

## Como o codigo esta organizado

Nucleo (`core/`):

- `constants.py`: URLs, EPSG, mapas `geo` -> funcao, anos disponiveis;
- `downloader.py`: `QgsBlockingNetworkRequest` + cadeia de mirrors + cache;
- `catalog.py`: metadado v1.7.0 (CSV), filtro por geo/ano/simplified;
- `loader.py`: `.gpkg` -> `QgsVectorLayer`, filtro por codigo;
- `capabilities.py`: deteccao de driver/backend Parquet (gdal/pyarrow);
- `catalog_v2.py`: assets `.parquet` do release v2.0.0;
- `loader_v2.py`: `.parquet` -> `QgsVectorLayer` (gdal ou pyarrow);
- `catalog_censo.py`: datasets de setor do censobr.

Algoritmos (`algorithms/`):

- `base_read_algorithm.py`: base dos `read_*` v1 (params YEAR/CODE/SIMPLIFIED);
- `read_*.py`: uma geografia por arquivo (Fase 1);
- `base_read_v2_algorithm.py` + `v2_factory.py`: os 28 `read_*_v2` gerados;
- `join_censo.py`: join geometria geobr x tabela censobr por `code_tract`.

Regras a preservar ao mexer aqui:

- Fase 1 e Fase 2 estao validadas — nao quebre algoritmos existentes;
- filtro v2 e pos-load (arquivos v2 sao nacionais), via `QgsExpression`;
- no `join_censo`, a chave `code_tract` e normalizada para texto nos dois lados
  (geobr v2 = double, censobr = string); nao remova essa normalizacao;
- default `simplified=True`.

## Validacao obrigatoria

Depois de mexer em qualquer `.py`, rode a checagem de sintaxe:

```bash
make test
```

(Equivale a `python3 -c "import ast,glob; [ast.parse(open(f).read(), f) for f in
glob.glob('**/*.py', recursive=True)]"`. Nao importa PyQGIS, entao roda no
terminal puro.)

A validacao de **comportamento** (que importa PyQGIS, baixa dados, monta camada)
so roda dentro do **Console Python do QGIS**, com o plugin deployado:

```bash
make deploy            # ou: make deploy-flatpak (perfil Flatpak, Fase 2)
```

No Console Python do QGIS (apos Plugin Reloader ou reiniciar):

```python
import processing
processing.run("gisbr:read_state",  # YEAR e indice do enum de anos; omitido = mais recente
               {"CODE": "MG", "SIMPLIFIED": True, "OUTPUT": "memory:"})
```

Se voce nao tiver acesso ao Console do QGIS, **nao invente** que validou
comportamento. Rode `make test` e declare a validacao funcional como pendente.

## Empacotar o plugin (.zip para o QGIS)

Quando uma ACTION pedir para **gerar o .zip** do plugin (para o repositorio
oficial do QGIS, em plugins.qgis.org), **nao monte o zip na mao**. Use a skill
`build-qgis-zip`:

```bash
bash .claude/skills/build-qgis-zip/package.sh
```

Ela gera `dist/gisbr-<version>.zip` com a estrutura exigida (uma pasta de
topo `gisbr/` com `metadata.txt` na raiz) e exclui docs/pesquisa/arquivos de processo.
Depois de rodar, confira que nenhum arquivo de `docs/`, `desafio-2-port/`,
`*.pdf` ou arquivo de processo entrou no zip. **A submissao em plugins.qgis.org
e passo manual do Diego** — voce so gera o arquivo.

## Como lidar com erro

Se um comando falhar:

1. Leia a mensagem de erro.
2. Corrija apenas o necessario.
3. Rode o mesmo comando de novo.
4. Se falhar de novo pelo mesmo motivo, pare e reporte o bloqueio.

Nao instale dependencias sem autorizacao.
Nao faca download em massa de dados nacionais para "testar" (arquivos de setor
sao pesados); prefira filtrar por UF/municipio.
Nao apague o cache em `~/.cache/geobr-qgis/`.
Nao rode comandos destrutivos.

Comandos proibidos sem autorizacao explicita:

```bash
git reset --hard
git checkout --
rm -rf
git clean
pip install
```

## Como responder ao planejador

No final, responda sempre neste formato:

```md
Feito.

Arquivos alterados:
- caminho/arquivo.py: o que mudou

Validacao:
- make test: passou
- (QGIS) processing.run(...): passou / pendente (sem Console do QGIS)

Nao testado:
- item que nao foi testado, com motivo

Observacoes:
- arquivo nao versionado ou risco fora do escopo, se houver
```

Se nada foi alterado, diga:

```md
Nao alterei arquivos.

Motivo:
- explique o bloqueio ou a decisao
```

## Criterios de qualidade

Antes de dizer "feito", confira:

- a tarefa pedida foi atendida;
- nao houve mudanca fora dos arquivos permitidos;
- `make test` passou;
- nenhuma dependencia externa nova foi adicionada;
- a cadeia de fallback de URL foi preservada;
- nenhum arquivo de dados, cache ou `__pycache__` foi commitado;
- o resumo final e curto e verificavel.

## Quando pedir ajuda

Peca ajuda antes de executar se:

- a tarefa nao diz quais arquivos podem ser alterados;
- a solucao exige uma dependencia externa (pip);
- a solucao exige mudar `CLAUDE.md`, `metadata.txt` ou `provider.py` sem
  permissao explicita;
- a validacao exige o Console do QGIS e voce nao tem acesso;
- duas instrucoes entram em conflito;
- voce percebe que a tarefa pode quebrar um algoritmo ja validado (Fase 1 ou 2).
