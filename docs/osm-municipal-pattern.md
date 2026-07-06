# Padrão OSM Municipal — Ingestão de Vias (2026-07-03)

## O que foi entregue

Fase 1–3 de ingestão municipal de vias OSM via Overpass, na branch `feat/osm-municipal`.

### Fase 1: Scaffold (commit 169639c)

- `core/connectors/osm.py` — conector Overpass via `QgsBlockingNetworkRequest`
  - `build_query(bbox)` → query Overpass QL para `way[\"highway\"]`
  - `fetch_overpass_json(bbox, timeout=180)` → POST, retorna dict parseado
  - `save_overpass_cache(payload, cache_path)` / `load_overpass_cache(cache_path)` — cache JSON local
  - `overpass_cache_key(code_muni, bbox, filters=None)` — nomear arquivo cache
- `core/osm_pipeline.py` — pipeline vazia (retorna `layers: {osm_links_raw: None, ...}`)
  - `build_osm_municipal_network(code_muni, nome_muni, gpkg_path, force=False, feedback=None)`
  - resolve município via `gisbr:read_municipality`, calcula bbox
  - consulta Overpass com fallback de cache local em disco
  - retorna dict com `raw_cache`, `layers`, `metadata`
- `core/diagnostico.py` — integração mínima
  - `_PROTOCOLOS += "osm"` 
  - `_busca_camada` branch `if proto == "osm"` → chama pipeline, marca como pendente com mensagem honesta
- `core/sources.py` — entrada declarativa
  - `{"id": "osm_vias", "eixo": "transportes", "nome": "OSM — Vias urbanas (Overpass)", "protocolo": "osm", ...}`

### Fase 2: Topologia (commit e8f3801 → 2f95e65)

Expandiu `core/osm_pipeline.py` com completo:

- `_parse_osm_ways(payload)` — extrai ways com tag `highway` do JSON
- `_build_nodes_dict(payload)` — mapa node_id → (lon, lat)
- `_way_to_linestring(way_osm, nodes_dict)` → QgsLineString
- `_create_links_layer(ways, nodes_dict)` → QgsVectorLayer(LineString, EPSG:4674)
  - campos: `way_id`, `highway`, `name`, `oneway`
- `_extract_nodes_from_layer(layer)` — deduplica pontos de extremidade de LineStrings
  - **PITFALL**: clip via `native:clip` pode gerar `MultiLineString` (divide vias na borda do polígono)
  - **FIX**: detectar `isMultipart()` e iterar com `asMultiPolyline()`, não só `asPolyline()`
- `_create_nodes_layer(nodes_set)` → QgsVectorLayer(Point, EPSG:4674)
  - campos: `node_id`, `x`, `y`
- `_recorta_poligono(layer, poligono)` — clip via `native:clip` ao polígono municipal
- `build_osm_municipal_network(...)` — retorna camadas preenchidas
  - `osm_links_raw` — todos os ways do bbox
  - `osm_links` — ways dentro do município após clip
  - `osm_nodes` — nós de extremidade deduplicados
  - metadata com nomes: `links_raw`, `links_clipped`, `nodes` (feature count)

### Fase 2b: Múltiplas camadas (atributos privados)

- `_busca_camada` anexa `osm_nodes` como atributo privado `layer._osm_nodes` da camada de links
- `carregar_fontes` em `diagnostico.py` detecta `hasattr(layer, "_osm_nodes")` e adiciona nodes como segunda layer
- **PITFALL**: atributos privados Python em `QgsVectorLayer` NÃO persistem — Qt descarta ao passar por internals
- **FIX**: não usar atribetos privados. Em vez disso, usar **special-case** (`if proto == "osm":` no início de `carregar_fontes`), chamar pipeline **fora do loop**, adicionar ambas as layers direto antes do processamento regular

### Fase 3: Persistência em GeoPackage (commit ced85c2 → 4702714)

Em `core/osm_pipeline.py`, após gerar camadas:
```python
from .diagnostico import _grava_gpkg
ok_links, _ = _grava_gpkg(osm_links, gpkg_path, "osm_links")
ok_nodes, _ = _grava_gpkg(osm_nodes, gpkg_path, "osm_nodes")
return {"layers": {...}, "metadata": {"gpkg_ok": ok_links and ok_nodes, ...}}
```

Em `core/diagnostico.py`, **special-case OSM** cedo (antes do loop de processed regular):
```python
osm_source = next((s for s in _por_id(source_ids) if s.get("protocolo") == "osm"), None)
if osm_source:
    result = osm_pipeline.build_osm_municipal_network(code_muni, nome_muni, gpkg_path, ...)
    if result.get("metadata", {}).get("gpkg_ok"):
        # RECARREGAR DO GPKG, NÃO REXIBIR MEMORY
        osm_links = QgsVectorLayer("{}|layername=osm_links".format(gpkg_path), "osm_links - ...", "ogr")
        osm_nodes = QgsVectorLayer("{}|layername=osm_nodes".format(gpkg_path), "osm_nodes - ...", "ogr")
        if osm_links.isValid():
            QgsProject.instance().addMapLayer(osm_links)
        if osm_nodes.isValid():
            QgsProject.instance().addMapLayer(osm_nodes)
```

**PITFALL**: se devolveres `osm_links` memory (not GPKG), parece funcionar no QGIS mas desaparece ao fechar o projeto. Contractor expecta persistência.
**FIX**: gravar → carregar DO GPKG → exibir. Memory é só etapa intermediária, not final output.

### Fase 4: Otimização (Skip-if-exists) e Nomenclatura por Município

- **Nomenclatura Única por Município**: Ajuste dos nomes das camadas salvas e lidas no GeoPackage para incluir o código do município (`osm_links_<code_muni>` e `osm_nodes_<code_muni>`), seguindo o padrão `{id}_{code_muni}` das demais fontes. Isso previne que rodar o diagnóstico para múltiplos municípios em um único GeoPackage acabe sobrescrevendo dados.
- **Mecanismo de Skip-if-exists**: Adicionado check de existência das camadas no GeoPackage antes de disparar o Overpass. Se as camadas já existirem e a flag `force` (botão de atualização da UI) estiver desligada (`False`), o processamento e o download são pulados (e logados em `pulou`), poupando banda e evitando timeouts de API.

### Fase 5: Robustez no Fetch Overpass (Erros e Timeout)

- **Tratamento de Erros Robustos**: Uso do erro tipado `OverpassError` para encapsular falhas de rede (`QgsBlockingNetworkRequest`) e problemas de decodificação de JSON inválido (por exemplo, erros HTTP com corpo em HTML/texto ou respostas truncadas), prevenindo exceções brutas como `json.JSONDecodeError` de travarem o fluxo principal.
- **Validação e Repasse de Timeout**: O parâmetro `timeout` passado no `fetch_overpass_json` agora é validado (garantindo que seja um inteiro positivo entre 10 e 600 segundos) e devidamente encaminhado para a query Overpass QL (`[timeout:N]`), corrigindo um bug latente em que o parâmetro era aceito mas ignorado em favor da constante `_OVERPASS_TIMEOUT`.
- **PITFALL**: Instabilidades de rede ou o limite de requisições da API Overpass (HTTP 429) resultando em dados corrompidos ou falhas de conexão derrubavam o diagnóstico por completo, mesmo havendo uma versão válida em cache.
- **FIX**: Implementação de fallback para o cache local (`osm_overpass_<code_muni>.json`) quando ocorre um `OverpassError`. O fluxo degrada graciosamente utilizando os dados locais previamente salvos e gerando um aviso (`feedback.pushInfo`) em vez de abortar o processo.

## Técnica: JSON Overpass → QgsVectorLayer → GeoPackage

1. **Parse JSON nativo** (`json` stdlib) — não há parsing de XML, JSON vem direto do Overpass
2. **Georeferência EPSG:4674** (lon,lat SIRGAS 2000) — **não reproje** nesta fase; nativos + clip nativos
3. **Memory layers transitórias** → converte para GPKG com `_grava_gpkg` (reutiliza helper existente)
4. **Recorte obrigatório** pelo polígono municipal via `native:clip` (sem vazar vizinhos)
5. **Deduplica nós** por coordenada exata no layer
6. **MultiLineString handling**: clip divide vias → `isMultipart()` + `asMultiPolyline()` em loop
7. **Múltiplas camadas** (links + nós) — special-case em `diagnostico.py` fora do loop de processamento normal

## Sem dependências externas

- HTTP: `QgsBlockingNetworkRequest` + `QNetworkRequest` (nativos QGIS)
- JSON: stdlib `json`
- Geometria: `QgsPoint`, `QgsLineString`, `QgsFeature`, `QgsField` (PyQGIS)
- Clip + persistência: `native:clip` + `_grava_gpkg` (existentes no gisbr)

## Estado ao fim de 2026-07-03

- ✅ Camadas em memória (links + nós), válidas para computação
- ✅ Recortadas ao polígono municipal
- ✅ Deduplicadas (nós únicos)
- ✅ **Gravadas em GeoPackage** (persistência)
- ✅ **Carregadas do GPKG** ao projeto (não memory transitória)
- ❌ Ainda não integra filtros por `highway` type (residential, primary, etc)
- ❌ Ainda não popula `lanes`, `speed`, `capacity` (schema GMNS)
- ✅ Pronto para teste manual no QGIS do Diego na branch `feat/osm-municipal`

## Padrão para futuras features multi-fase

### Quando fase anterior travada/rate-limitada

1. Júnior bate no rate limit → você não espera
2. Implementa **fase essencial** (core algorithm) direto
3. Deixa persistência/UI/refinement para depois
4. Commit intermediário + branch temática → destranca fluxo

Exemplo aqui: `HTTP 429` no júnior → você fez 100+ linhas do parsing JSON + topologia em 30min, desatravou tudo.

### Integração de múltiplas camadas em backend

- **Não use atributos privados** em QgsVectorLayer — Qt descarta
- **Special-case o protocolo** cedo no `carregar_fontes` (antes do loop)
- **Chamar pipeline fora do loop** → adicionar ambas layers ao projeto/GPKG
- **Remover protocolo de source_ids** para não processar duas vezes

### Contratos honestos

Pipeline retorna `gpkg_ok: false` quando não conseguiu gravar. Backend verifica, não fingir sucesso. Facilita debug.

---

**Commits desta sessão** (`feat/osm-municipal`):
- `169639c` — Fase 1 scaffold
- `e8f3801` — Fase 2: JSON parsing + topologia
- `2f95e65` — Fase 2b: MultiLineString fix
- `ced85c2` — Fase 3a: gravar GPKG
- `4702714` — Fase 3b: carregar do GPKG (não memory)
