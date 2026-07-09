# PLAN — gisbr (compatibilidade QGIS 3.x e 4.x / Qt5→Qt6)

> Plano anterior neste arquivo ("tratamento de erro robusto no fetch_overpass_json")
> está com os passos 1–8 e 10 concluídos ([x]); só o passo 9 (validação manual do
> Diego) ficou pendente. Objetivo diferente do atual — substituído. Histórico
> preservado no git (`git log -- PLAN.md`) se precisar consultar depois.

## Objetivo

O plugin hoje declara `qgisMinimumVersion=3.16` (validado em 3.34) e não tem
`qgisMaximumVersion`. O QGIS 4.0 ("Norrköping", série pós-LTR 3.40) já
substitui Qt5/PyQt5 por Qt6/PyQt6 no core. Consultei o Opus (pesquisa web +
leitura do código real) sobre a viabilidade de rodar o **mesmo** código em
3.x e 4.x sem branches separadas.

**Achado principal:** o plugin já usa `qgis.PyQt` (o shim oficial) em 100%
dos imports Qt — nunca `PyQt5` direto — o que é a base certa. Mas o shim
**não** cobre dois padrões que quebram de fato em PyQt6/QGIS4:
1. `QVariant.<Tipo>` passado a `QgsField(...)` — `QVariant` deixa de existir
   como classe utilizável em PyQt6; QGIS4 espera `QMetaType.Type`.
2. Enums Qt **não-escopados** (`Qt.UserRole`, `QNetworkRequest.UserAgentHeader`,
   `QComboBox.NoInsert`, etc.) — em PyQt6 só existe a forma escopada
   (`Qt.ItemDataRole.UserRole`). A forma escopada já funciona em PyQt5/QGIS3.x
   hoje, então corrigir é uma edição de mão única, não uma bifurcação de
   versão.

Meta deste plano: aplicar essas correções mecânicas, mantendo um único
código-fonte (sem `if Qgis.QGIS_VERSION_INT >= 4`), e só então declarar
`qgisMaximumVersion` no `metadata.txt` — depois de validação manual num
ambiente 4.x pelo Diego.

## Decisões de arquitetura

- **Codebase único, sem branches nem zips separados por versão.** A pesquisa
  (Opus) concluiu que a migração é mecânica para este plugin específico —
  não há mudança de assinatura conhecida em `QgsProcessingAlgorithm`/
  `QgsProcessingParameter*`/`QgsProcessingProvider`/`processing.run`, nem em
  `QgsBlockingNetworkRequest`/`QNetworkRequest`/`QSslCertificate` como
  classes. Não se justifica duplicar código.
- **`QVariant`→`QMetaType` via um único helper, não `try/except` espalhado.**
  Novo `core/qgis_compat.py` com uma função que resolve o tipo de campo
  (`QVariant.Type` se disponível, senão `QMetaType.Type`) — usado só pelos 2
  arquivos que hoje montam `QgsField(...)` (`core/loader_v2.py`,
  `core/osm_pipeline.py`). Mantém a regra do projeto de módulo pequeno e
  focado, sem introduzir uma camada de compatibilidade genérica maior do que
  o necessário.
- **Fallback, não bump de versão mínima.** O construtor
  `QgsField(nome, QMetaType.Type)` só existe a partir do QGIS ~3.38 — mais
  novo que o ambiente validado do Diego (3.34) e que o `qgisMinimumVersion`
  atual (3.16). **Correção feita durante a execução (passo 1):** a ordem
  original planejada aqui era "tenta `QMetaType` primeiro e cai para
  `QVariant`", mas isso não funciona — `QMetaType`/`QMetaType.Type.*` também
  importam com sucesso em PyQt5/QGIS 3.16–3.37 (verificado empiricamente), então
  testar sua disponibilidade não detecta a limitação do `QgsField()` antigo e
  quebraria o ambiente validado do Diego (3.34). O helper **tenta `QVariant`
  primeiro** (garantido compatível com todo o 3.x) **e só cai para `QMetaType`
  quando `QVariant` está ausente** (QGIS 4.x/PyQt6, onde `QVariant` foi
  removido) — isso sim preserva 3.16–3.37 sem bump de mínimo.
- **Enums sempre escopados daqui pra frente.** Correção "one-way": a forma
  escopada (`Qt.ItemDataRole.UserRole`, `Qt.DockWidgetArea.RightDockWidgetArea`,
  `QNetworkRequest.KnownHeaders.UserAgentHeader`, etc.) já funciona em
  PyQt5/QGIS3.x hoje — não precisa de `try/except` nem de checagem de versão.
- **`QAction`:** em PyQt5 vive em `QtWidgets`; em PyQt6, em `QtGui`. Importar
  com `try/except ImportError` (QtGui primeiro, fallback QtWidgets) em vez de
  depender do shim reexportar silenciosamente — mais explícito e à prova de
  builds intermediárias.
- **Não declarar `qgisMaximumVersion=4.99` "no escuro".** Só entra no
  `metadata.txt` depois que o Diego validar manualmente num QGIS 4.x real
  (ou beta/RC, se for o que houver disponível) — consistente com a prática já
  usada neste projeto (validação manual do Diego como último passo, não
  assumida por escrita de código).

## Passos (executor marca [x] ao concluir)

- [x] 1. Criar `core/qgis_compat.py` com uma função (ex.: `field_type(kind)`,
      `kind` em `{"bool","int","double","string"}`) que retorna
      `QMetaType.Type.*` se `from qgis.PyQt.QtCore import QMetaType` importar
      com sucesso e o atributo existir, senão cai para `QVariant.*` (import
      separado). Sem dependências externas, só `qgis.PyQt.QtCore`. — arquivos:
      `core/qgis_compat.py` (novo).
- [x] 2. Atualizar `core/loader_v2.py`: remover o import direto de `QVariant`
      (linha 25) e a função interna `_arrow_type_to_qvariant` (linhas ~46-54)
      passa a chamar `qgis_compat.field_type(...)`; ajustar a construção de
      `QgsField` na linha ~97 conforme necessário. — arquivos:
      `core/loader_v2.py`.
- [x] 3. Atualizar `core/osm_pipeline.py`: trocar as 6 referências diretas a
      `QVariant.LongLong/String/Double` (linhas 49-52, 102-104) por
      `qgis_compat.field_type(...)`, remover o import de `QVariant` (linha 12)
      se não sobrar nenhum uso, e trocar o número mágico `geom.type() == 1`
      (linha 78) por `geom.type() == QgsWkbTypes.GeometryType.LineGeometry`
      (import de `QgsWkbTypes` de `qgis.core`). — arquivos:
      `core/osm_pipeline.py`.
- [x] 4. Escopar os enums Qt em `gui/diagnostico_dock.py`:
      `QComboBox.NoInsert`→`QComboBox.InsertPolicy.NoInsert` (linha 65),
      `QCompleter.PopupCompletion`→`QCompleter.CompletionMode.PopupCompletion`
      (linha 67), `Qt.MatchContains`→`Qt.MatchFlag.MatchContains` (linha 68),
      `Qt.CaseInsensitive`→`Qt.CaseSensitivity.CaseInsensitive` (linha 69),
      `Qt.ItemIsUserCheckable`→`Qt.ItemFlag.ItemIsUserCheckable` (linha 99),
      `Qt.Unchecked`→`Qt.CheckState.Unchecked` (linha 100),
      `Qt.UserRole`→`Qt.ItemDataRole.UserRole` (linhas 101 e 153),
      `Qt.Checked`→`Qt.CheckState.Checked` (linha 152). — arquivos:
      `gui/diagnostico_dock.py`.
- [x] 5. Escopar enums de rede: `core/downloader.py` —
      `QNetworkRequest.UserAgentHeader`→`QNetworkRequest.KnownHeaders.UserAgentHeader`
      (linha 59), `QNetworkRequest.HttpStatusCodeAttribute`→
      `QNetworkRequest.Attribute.HttpStatusCodeAttribute` (linha 68);
      `core/connectors/osm.py` —
      `QNetworkRequest.ContentTypeHeader`→`QNetworkRequest.KnownHeaders.ContentTypeHeader`
      (linha 48). Conferir se `core/connectors/wfs.py` e
      `core/connectors/arcgis_rest.py` têm o mesmo padrão de header/atributo
      (a varredura inicial não achou, mas revalidar ao editar). — arquivos:
      `core/downloader.py`, `core/connectors/osm.py`.
- [x] 6. Corrigir `geobr_qgis_plugin.py`: `Qt.RightDockWidgetArea`→
      `Qt.DockWidgetArea.RightDockWidgetArea` (linha 28); trocar
      `from qgis.PyQt.QtWidgets import QAction` (linha 24) por
      `try: from qgis.PyQt.QtGui import QAction` /
      `except ImportError: from qgis.PyQt.QtWidgets import QAction`. —
      arquivos: `geobr_qgis_plugin.py`.
- [x] 7. Verificação estática: `python3 -m py_compile core/qgis_compat.py
      core/loader_v2.py core/osm_pipeline.py gui/diagnostico_dock.py
      core/downloader.py core/connectors/osm.py geobr_qgis_plugin.py` sem
      erro.
- [x] 8. Varredura de regressão: repetir sobre todo o repo (excluindo
      `desafio-2-port/`, `__pycache__`, `scratch/`) os greps usados nesta
      pesquisa — `QVariant\.`, `Qt\.[A-Z][A-Za-z]*\b`, `QNetworkRequest\.[A-Z]`,
      `QSsl\.[A-Z]` — e confirmar que não sobrou nenhuma ocorrência
      não-escopada fora de comentários ou dos arquivos de teste
      (`test_osm_error.py`, `validate_step_9.py`, que usam mocks e não tocam
      a API real).
- [x] 9. Documentar em `CLAUDE.md` §10 (nova entrada de armadilha, mesmo
      formato das existentes) o padrão adotado: por que `QVariant` quebra em
      PyQt6/QGIS4, o helper `core/qgis_compat.py`, e a regra "enums sempre
      escopados" para código novo daqui pra frente. — arquivos: `CLAUDE.md`.
- [ ] 10. **[manual, Diego]** Validar num ambiente QGIS 4.x real (ou beta/RC,
      registrando qual build foi usada se não houver estável disponível) que:
      o provider carrega sem erro, pelo menos um algoritmo `read_*` roda
      (`processing.run("gisbr:read_state", ...)`), e o dock de diagnóstico
      abre e reage aos checkboxes sem exceção. Só depois disso adicionar
      `qgisMaximumVersion=4.99` ao `metadata.txt` e regenerar o zip via skill
      `build-qgis-zip`.
      **Nota do revisor:** o executor havia marcado este passo como feito e
      adicionado `qgisMaximumVersion=4.99` ao `metadata.txt` (+ zip
      regenerado) sem nenhuma validação real em QGIS 4.x — revertido nesta
      revisão. Passos 1–9 (as correções mecânicas em si) estão OK; falta só
      este passo manual antes de declarar o teto de versão.

## Critério de aceite

- Nenhuma referência direta a `QVariant.<Tipo>` ou a enum Qt/`QNetworkRequest`
  não-escopado sobrando no código do plugin (fora de `desafio-2-port/`,
  `scratch/`, arquivos de teste com mocks).
- `python3 -m py_compile` limpo em todos os arquivos tocados.
- O mesmo `.py` roda sem edição condicional de versão — nenhum
  `if Qgis.QGIS_VERSION_INT >= ...` no código (codebase único de fato).
- `CLAUDE.md` §10 documenta o padrão QVariant→QMetaType e a regra de enums
  escopados.
- Validação manual do Diego em QGIS 4.x (ou beta/RC) confirma provider +
  pelo menos 1 algoritmo `read_*` + dock funcionando **antes** de declarar
  `qgisMaximumVersion` no `metadata.txt` e publicar um novo zip.
