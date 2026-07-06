# PLAN — gisbr (tratamento de erro robusto no fetch_overpass_json)

> Plano anterior neste arquivo ("skip-exists para OSM") está com todos os
> passos concluídos ([x]) e foi substituído — objetivo diferente. Histórico
> preservado no git (`git log -- PLAN.md`) se precisar consultar depois.

## Objetivo

Hoje `fetch_overpass_json` (`core/connectors/osm.py`) propaga `json.JSONDecodeError`
sem tratamento sempre que a API do Overpass devolve algo que não é JSON válido
(erro HTTP disfarçado de corpo de texto/HTML, resposta truncada por timeout do
servidor, rate-limit "Too Many Requests" em texto puro, etc.). Isso derruba o
diagnóstico inteiro no meio do fluxo (`osm_pipeline.build_osm_municipal_network`),
mesmo quando já existe um cache local utilizável do mesmo município.

Meta: tornar `fetch_overpass_json` resiliente a essas respostas — detectar e
reportar o erro de forma clara (sem stack trace de `JSONDecodeError` cru),
cair para o cache local em disco quando existir, e corrigir o parâmetro
`timeout` que hoje é aceito mas **ignorado** (bug latente relacionado a
"validação de timeout").

## Decisões de arquitetura

- **Erro tipado, não `RuntimeError` genérico:** criar `OverpassError(Exception)`
  em `core/connectors/osm.py` para erros de rede/parse do Overpass. Mantém
  `try/except OverpassError` específico possível no chamador, sem capturar
  acidentalmente outras exceções (ex.: bug de programação).
- **Fallback de cache é uma nova camada, não substitui a existente:**
  `osm_pipeline.build_osm_municipal_network` já verifica o cache **antes** de
  chamar `fetch_overpass_json` (reuso se existe e `force=False`). Essa lógica
  não muda. O que falta é: quando o Overpass **falha** (rede ou JSON inválido)
  e o cache existe mas não foi usado (porque estava desatualizado ou
  `force=True`), cair para ele em vez de propagar a exceção — degradação
  graciosa, não substituição da regra de atualização.
- **Onde entra o fallback:** dentro de `fetch_overpass_json`, via parâmetro
  opcional `cache_path=None`. Se a consulta falhar (`OverpassError`) e
  `cache_path` apontar para um arquivo existente, carregar via
  `load_overpass_cache` (função já existente) e devolver esse payload com um
  aviso (via `feedback` opcional, mesmo padrão `pushInfo` usado no resto do
  projeto). Sem `cache_path` ou sem arquivo, propaga o `OverpassError`.
  Mantém tudo dentro de `osm.py`, sem duplicar lógica de cache no pipeline.
- **Correção do `timeout`:** hoje `build_query` usa a constante de módulo
  `_OVERPASS_TIMEOUT` (180) e **ignora** o argumento `timeout` recebido por
  `fetch_overpass_json`/`_post_overpass` — é passado mas nunca chega à query
  `[out:json][timeout:...]`. Corrigir para usar o valor efetivo recebido,
  com validação simples (inteiro positivo, clamp para uma faixa razoável,
  ex.: 10–600s) para não gerar uma query Overpass QL inválida ou uma espera
  absurda. Sem taxonomia nova de exceção para isso — só `ValueError` já é
  suficiente (erro de programação/uso, não de rede).
- **Sem retry automático nem backoff:** fora de escopo — Overpass é
  rate-limited e um retry mal feito pode piorar (bloqueio de IP). Se o Diego
  quiser retry mais pra frente, é uma decisão separada.
- **Prefeitura da solução mais simples:** não criar um módulo de "circuit
  breaker" nem persistir métricas de falha — só try/except + fallback de
  cache + validação de timeout, como pedido.

## Passos (executor marca [x] ao concluir)

- [x] 1. Adicionar `class OverpassError(Exception): pass` em
      `core/connectors/osm.py` (logo após os imports/constantes). — arquivos:
      `core/connectors/osm.py`.
- [x] 2. Em `_post_overpass`, checar o erro de rede da resposta antes de olhar
      o corpo: usar `reply.error()` / `blocking.errorCode()` (verificar qual
      API o `QgsBlockingNetworkRequest` local expõe — mesmo cuidado já
      registrado no `CLAUDE.md` §5 sobre variação de assinatura entre versões
      do QGIS) e, se indicar erro, levantar `OverpassError` com mensagem
      incluindo `reply.errorString()`. Manter o `raise` atual para corpo vazio,
      mas trocando `RuntimeError` por `OverpassError`. — arquivos:
      `core/connectors/osm.py`.
- [x] 3. Em `fetch_overpass_json`, envolver o `json.loads(...)` em
      `try/except json.JSONDecodeError` e relançar como `OverpassError`,
      incluindo no texto um trecho curto da resposta crua (ex.: primeiros
      200 caracteres, sem `ensure_ascii` gigante) para facilitar diagnóstico
      sem despejar o payload inteiro no log. — arquivos:
      `core/connectors/osm.py`.
- [x] 4. Corrigir o `timeout` morto: `build_query` passa a receber o `timeout`
      efetivo (não a constante `_OVERPASS_TIMEOUT`) e validar
      (`int(timeout)`, `ValueError` se não for inteiro positivo; clamp para
      10–600). Atualizar `_post_overpass`/`fetch_overpass_json` para
      encaminhar o valor validado até `build_query`. Manter
      `_OVERPASS_TIMEOUT = 180` só como default do parâmetro. — arquivos:
      `core/connectors/osm.py`.
- [x] 5. Adicionar parâmetros opcionais `cache_path=None, feedback=None` a
      `fetch_overpass_json`. No `except OverpassError`, se `cache_path` for
      passado e o arquivo existir, chamar `load_overpass_cache(cache_path)`;
      se retornar payload não-nulo, emitir aviso (`feedback.pushInfo(...)` se
      `feedback` não for `None`) e devolver esse payload em vez de propagar o
      erro. Caso não haja `cache_path`/arquivo/parse válido, relançar o
      `OverpassError` original. — arquivos: `core/connectors/osm.py`.
- [x] 6. Atualizar a chamada em
      `osm_pipeline.build_osm_municipal_network` (linha ~177,
      `osm.fetch_overpass_json(bbox, timeout=180)`) para passar
      `cache_path=cache_path, feedback=feedback`, aproveitando as variáveis já
      calculadas na função. Envolver a chamada em `try/except OverpassError`
      só para logar via `feedback.pushInfo` e devolver o dict de erro já
      usado pela função (mesmo formato do `return` quando `municipio is None`,
      linha ~164) em vez de deixar a exceção subir até o dock. — arquivos:
      `core/osm_pipeline.py`.
- [x] 7. Verificação estática: `python3 -m py_compile core/connectors/osm.py
      core/osm_pipeline.py` sem erros.
- [x] 8. Teste manual/local do parsing de erro (sem depender do Overpass
      real): no console Python do QGIS ou script avulso, chamar
      `osm.fetch_overpass_json` mockando `_post_overpass` (ou testar
      diretamente `json.loads` do trecho novo) com (a) bytes vazios, (b) bytes
      de HTML de erro (`b"<html>Too Many Requests</html>"`), (c) um
      `cache_path` válido presente — confirmar que (a)/(b) sem cache levantam
      `OverpassError` com mensagem legível, e que com `cache_path` válido
      devolvem o payload do cache em vez de lançar.
- [ ] 9. Validação manual no QGIS (Diego): rodar o diagnóstico com
      "Transportes" marcado para um município com cache OSM já gravado em
      disco (`osm_overpass_<code_muni>.json`), simulando falha de rede
      (ex.: desconectar a internet momentaneamente ou apontar
      `_OVERPASS_URL` para um endpoint inválido) — confirmar que o
      diagnóstico não quebra, usa o cache e loga o aviso de fallback.
      **Nota do executor:** `validate_step_9.py` automatiza esse cenário
      (PyQGIS standalone headless) e roda com sucesso — confirma que o
      fallback funciona via `carregar_fontes`. Isso não substitui a
      validação manual do Diego no dock real (UI, checkboxes, satélite);
      mantido `[ ]` até ele confirmar.
- [x] 10. Atualizar `docs/osm-municipal-pattern.md` (seção de pitfalls) com o
      novo comportamento: `OverpassError` tipado, fallback para cache local
      em falha de rede/JSON inválido, e a correção do `timeout` antes
      ignorado. — arquivos: `docs/osm-municipal-pattern.md`.

## Critério de aceite

- `fetch_overpass_json` nunca propaga `json.JSONDecodeError` cru — qualquer
  falha de parse ou rede vira `OverpassError` com mensagem legível.
- Quando existe cache local (`osm_overpass_<code_muni>.json`) e o Overpass
  falha (rede ou resposta inválida), o diagnóstico completa usando o cache,
  com aviso no log, em vez de travar o eixo Transportes inteiro.
- Sem cache disponível e falha do Overpass, o erro chega ao usuário como
  mensagem clara (via `feedback.pushInfo`/exceção tratada no dock), não como
  traceback de `JSONDecodeError`.
- O parâmetro `timeout` passado para `fetch_overpass_json` realmente altera o
  `[out:json][timeout:N]` da query enviada ao Overpass (hoje é ignorado).
- `python3 -m py_compile core/connectors/osm.py core/osm_pipeline.py` limpo.
- Nenhuma outra fonte (`wfs`, `arcgis`, `geobr`, `basemap`) é afetada.
