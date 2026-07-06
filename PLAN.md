# PLAN — gisbr (skip-exists para OSM, alinhado ao "Atualizar bases já baixadas")

## Objetivo

Fazer o protocolo `osm` (Overpass, `core/osm_pipeline.py`) respeitar a mesma regra
de **skip-if-exists** que já vale para as fontes `wfs`/`arcgis`/`geobr` em
`core/diagnostico.py::carregar_fontes()`: se as camadas OSM já estiverem gravadas
no GeoPackage do município, **não rebaixar do Overpass nem reprocessar** — a
menos que o usuário marque o checkbox **"Update already-downloaded layers
(re-download)"** (`chk_atualizar` no dock, parâmetro `force`).

Hoje isso não acontece: o bloco especial de OSM em `carregar_fontes()` (linhas
167–188) **sempre** chama `osm_pipeline.build_osm_municipal_network(...)`,
que só decide reusar/pular o **cache do JSON do Overpass** (arquivo
`osm_overpass_<code_muni>.json`) — mas sempre reprocessa (parse, clip,
dedup de nós) e **sempre regrava** `osm_links`/`osm_nodes` no GPKG, mesmo que
já existam e não tenham mudado. Isso é inconsistente com o resto do motor e
desperdiça uma consulta Overpass (rate-limited, ~180s de timeout) toda vez que
o diagnóstico roda de novo para o mesmo município.

## Decisões de arquitetura

- **Reaproveitar o mecanismo já existente**, não criar um novo: `carregar_fontes()`
  já calcula `existentes = _layers_existentes(gpkg_path)` (nomes de camadas do
  GeoPackage) e, para as demais fontes, faz `if (not force) and layer_name in
  existentes: pular`. O fix do OSM é fazer o **mesmo check antes de chamar**
  `build_osm_municipal_network`, não alterar `_layers_existentes` nem o
  contrato de `force`.
- **Corrigir a divergência de nomenclatura primeiro — é pré-requisito, não
  extra.** A spec original (`ACTIONS.md`, T-OSM-001) definia as camadas como
  `osm_links_<code_muni>` / `osm_nodes_<code_muni>` (mesmo padrão de todas as
  outras fontes: `"{id}_{code_muni}"`). A implementação atual gravou/lê com
  nomes **fixos** `osm_links` / `osm_nodes` (sem sufixo de município). Isso é
  um bug latente: com um único GeoPackage compartilhado entre municípios (o
  padrão do restante do sistema), rodar o diagnóstico para um segundo
  município reescreveria as camadas OSM do primeiro. Sem esse fix, um
  skip-if-exists genérico ficaria **incorreto** (pularia o Overpass de um
  município B pensando que já tem dados, quando na verdade tem dados do
  município A). Portanto o passo de nomenclatura entra neste mesmo plano.
- **Onde fica o check:** dentro de `carregar_fontes()`, junto ao bloco
  especial de OSM (não dentro de `osm_pipeline.py`) — mantém o mesmo lugar
  onde o skip-if-exists das outras fontes já vive, e mantém
  `build_osm_municipal_network()` livre de responsabilidade sobre o GeoPackage
  já ter ou não as camadas (ele só grava; grava sempre que é chamado).
- **Semântica do skip igual às demais fontes:** ao pular, não adicionar nenhuma
  camada ao projeto (mesmo comportamento de `res["pulou"]` para wfs/arcgis/
  geobr — hoje eles também não recarregam a camada já existente
  automaticamente). Simplicidade > tentar "carregar do GPKG mesmo pulando" —
  isso pode vir depois se o Diego pedir.
- **Não mexer no cache de JSON do Overpass** (`osm_overpass_<code_muni>.json`,
  controlado por `force` dentro de `build_osm_municipal_network`) — ele
  continua útil como uma segunda camada de otimização para quando o
  skip-if-exists **não** se aplica (ex.: GPKG apagado mas cache do Overpass
  ainda em disco).
- **Remover código morto:** o branch `if proto == "osm":` dentro de
  `_busca_camada()` (`core/diagnostico.py` linhas 143–148) nunca executa —
  o `source_id` do OSM já é removido de `source_ids` antes do loop principal
  chegar em `_busca_camada`. Não superconstruir em cima de código morto;
  removê-lo deixa claro que o OSM só tem um caminho (o bloco especial).

## Passos (executor marca [x] ao concluir)

- [x] 1. Corrigir nomes de camada no GeoPackage para incluir o sufixo do
      município, alinhando com o padrão `"{id}_{code_muni}"` das demais
      fontes e com a spec original (`ACTIONS.md` T-OSM-001):
      `osm_links_<code_muni>` e `osm_nodes_<code_muni>` (em vez de
      `osm_links`/`osm_nodes` fixos). — arquivos: `core/osm_pipeline.py`
      (chamadas a `_grava_gpkg(..., "osm_links")` / `"osm_nodes"` dentro de
      `build_osm_municipal_network`), `core/diagnostico.py` (leitura via
      `"{}|layername=osm_links".format(gpkg_path)` /
      `"...osm_nodes..."` no bloco especial OSM, linhas ~174–175).
- [x] 2. No bloco especial de OSM em `carregar_fontes()`, calcular os nomes
      esperados (`"osm_links_{}".format(code_muni)`,
      `"osm_nodes_{}".format(code_muni)`) e, **antes** de chamar
      `osm_pipeline.build_osm_municipal_network(...)`, checar se ambos já
      estão em `existentes` (mesma variável já calculada no topo da função via
      `_layers_existentes(gpkg_path)`). — arquivos: `core/diagnostico.py`.
- [x] 3. Se ambos existirem e `force` for `False`: **pular** o pipeline
      inteiro (sem chamar Overpass, sem resolver polígono do município, sem
      regravar), registrar em `res["pulou"].append((osm_source["id"], "ja
      existe no GeoPackage (osm_links_<code>/osm_nodes_<code>)"))`, no mesmo
      formato de mensagem usado pelas demais fontes (linha ~200). Caso
      contrário (não existe, ou `force=True`), seguir o fluxo atual
      (chamar `build_osm_municipal_network`, carregar do GPKG, `addMapLayer`).
      — arquivos: `core/diagnostico.py`.
- [x] 4. Remover o branch morto `if proto == "osm":` dentro de
      `_busca_camada()` (nunca é alcançado, pois o OSM é removido de
      `source_ids` antes do loop principal) — só para não deixar dois
      caminhos incoerentes para o mesmo protocolo. — arquivos:
      `core/diagnostico.py`.
- [x] 5. Verificação estática: `python3 -m py_compile core/diagnostico.py
      core/osm_pipeline.py` sem erros; `grep -n "osm_links\b\|osm_nodes\b"
      core/diagnostico.py core/osm_pipeline.py` confirma que não sobrou
      nenhuma referência aos nomes antigos sem sufixo de município (fora dos
      nomes internos de camada em memória `"osm_links"`/`"osm_nodes"`
      passados como `layer_name` de exibição, que podem continuar iguais —
      só os nomes gravados/lidos do GPKG precisam do sufixo).
- [x] 6. Validação manual no QGIS (Diego), no dock de diagnóstico, para um
      município já testado (ex.: Contagem, `code_muni=3118402`):
      1) rodar o diagnóstico com "Transportes" marcado e checkbox "Update
      already-downloaded layers" **desmarcado** — 1ª vez baixa do Overpass e
      grava `osm_links_3118402`/`osm_nodes_3118402`; 2) rodar de novo, mesmo
      município, checkbox ainda desmarcado — log deve mostrar mensagem de
      "já existe no GeoPackage" e **nenhuma** chamada ao Overpass (sem espera
      de ~180s, sem novo `OSM: consultando Overpass` no log); 3) marcar o
      checkbox e rodar de novo — deve rebaixar/regravar normalmente.
- [x] 7. Atualizar `docs/osm-municipal-pattern.md` com uma seção curta
      registrando o comportamento de skip-if-exists e a correção do nome de
      camada (`osm_links_<code_muni>`/`osm_nodes_<code_muni>`), no mesmo
      estilo das fases já documentadas (Fase 4). — arquivos:
      `docs/osm-municipal-pattern.md`.

## Critério de aceite

- Rodar o diagnóstico duas vezes seguidas para o mesmo município com "Update
  already-downloaded layers" **desmarcado**: a segunda vez não faz nenhuma
  requisição ao Overpass e não regrava o GeoPackage — aparece em `pulou`,
  igual ao comportamento já existente para `wfs`/`arcgis`/`geobr`.
- Com o checkbox **marcado**, o comportamento atual de rebaixar/regravar
  continua funcionando sem regressão.
- As camadas no GeoPackage passam a se chamar `osm_links_<code_muni>` e
  `osm_nodes_<code_muni>`, consistente com o padrão `"{id}_{code_muni}"` do
  resto do sistema e com a spec original do T-OSM-001.
- Nenhuma outra fonte (`wfs`, `arcgis`, `geobr`, `basemap`) é afetada
  (`python3 -m py_compile` limpo; fluxo dessas fontes inalterado).
- `docs/osm-municipal-pattern.md` reflete o novo comportamento.
