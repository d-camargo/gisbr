# Tópico: atualizacao-4-0
_Memória deste tópico. O orquestrador lê isto no início de toda conversa._
Atualizado: 2026-07-13 · HEAD: 4ac437f

## Objetivo
Compatibilizar o gisbr com QGIS 4.x (Qt6/PyQt6) mantendo **um único codebase**
(sem branches/zips separados por versão) — plano completo em `PLAN.md`.

## Estado atual (o que JÁ está feito e verificado)
- Passos 1–9 do `PLAN.md` concluídos e **reverificados agora**:
  - `core/qgis_compat.py` criado (`field_type()`: tenta `QVariant` primeiro, cai
    pra `QMetaType` se ausente).
  - `core/loader_v2.py`, `core/osm_pipeline.py` usam o helper (sem `QVariant.*`
    direto fora do próprio `qgis_compat.py`).
  - Enums escopados em `gui/diagnostico_dock.py`, `core/downloader.py`,
    `core/connectors/osm.py`, `geobr_qgis_plugin.py` (`QAction` com
    `try/except` QtGui→QtWidgets).
  - `python3 -m py_compile` limpo nos 7 arquivos tocados (reconferido).
  - Grep de regressão (`QVariant\.`, `Qt\.[A-Z]`, `QNetworkRequest\.[A-Z]`,
    `QSsl\.[A-Z]`) não achou uso não-escopado fora do próprio `qgis_compat.py`.
  - `CLAUDE.md` §10 documenta o padrão (última entrada da seção).
- `metadata.txt`: `version=0.4.0`, `experimental=False`, `qgisMinimumVersion=3.16`.
- `dist/gisbr-0.4.0.zip` existe e foi empacotado (commit `15da5f7`, HEAD-2).

## Decisões tomadas
- Codebase único, sem `if Qgis.QGIS_VERSION_INT >= 4`.
- Helper único `core/qgis_compat.py` (não `try/except` espalhado).
- `QAction`: import com fallback QtGui (PyQt6) → QtWidgets (PyQt5).
- `qgisMaximumVersion` só deveria ser declarado **depois** da validação manual
  do Diego em QGIS 4.x real (critério de aceite do próprio `PLAN.md`).

## Pendências / próximo passo
- **⚠️ Passo 10 do PLAN.md (validação manual em QGIS 4.x real) está PENDENTE —
  ninguém validou.** Não existe nenhum registro (doc, commit, changelog) de teste
  em ambiente QGIS 4.x/beta real.
- **⚠️ Inconsistência encontrada:** o `PLAN.md` (nota do "revisor" no passo 10)
  afirma que `qgisMaximumVersion=4.99` foi **revertido** do `metadata.txt` por
  ter sido declarado sem validação. Isso é **falso no estado atual do repo**:
  `qgisMaximumVersion=4.99` está presente em `metadata.txt` (adicionado no
  commit `889f6bd`, nunca removido — o commit seguinte `0b03e82` só restaurou
  `version/author/email`, não tocou nessa linha) e **já foi empacotado** no
  `dist/gisbr-0.4.0.zip` publicado. Ou seja, o teto de versão foi declarado e
  distribuído sem a validação manual que o próprio plano exige.
- Próximo passo real: (a) decidir com o Diego se remove `qgisMaximumVersion=4.99`
  do `metadata.txt` até validar de fato em QGIS 4.x, ou (b) fazer a validação
  manual (passo 10) o quanto antes. Enquanto isso não resolver, tratar a
  declaração de suporte a QGIS 4.x como **não confirmada**.

## Armadilhas (o que já deu errado aqui — pra não repetir)
- Histórico de commits de empacotamento ficou bagunçado nesta sessão (zips
  renomeados `0.3.2→0.0→removido`, depois `0.4.0` recriado) — sem perda final
  (estado atual limpo), mas indica que o fluxo de `package:` foi rodado várias
  vezes manualmente em vez de via skill/Makefile de forma consistente.
- **Não confiar no texto do `PLAN.md` sem checar o git.** O plano registra uma
  reversão que não aconteceu de fato no arquivo — sempre conferir `metadata.txt`
  e `git log -p` antes de assumir que uma nota de revisão foi aplicada.
