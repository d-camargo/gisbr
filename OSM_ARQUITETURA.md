# OSM Municipal — Arquitetura Atual (2026-07-03)

**Status:** Scaffolding Fase 1 completo. Integração no `diagnostico.py` aguardando task `T-OSM-001`.

---

## 📋 O que já existe

### 1️⃣ Conector OSM (`core/connectors/osm.py`)

```python
fetch_overpass_json(bbox, timeout=180)  # → JSON do Overpass
  └─ Enriquecido: User-Agent, POST com payload, retry
```

**Retorna:** dict com `{"elements": [...ways nodes...]}` (JSON Overpass)

---

### 2️⃣ Pipeline OSM (`core/osm_pipeline.py`)

#### **Funções de conversão JSON → QgsVectorLayer:**

| Função | O que faz | Entrada | Saída |
|--------|----------|---------|-------|
| `build_osm_municipal_network()` | **Orquestrador** — busca município, Overpass, recorta, grava GPKG | `code_muni, bbox, gpkg_path` | dict com `layers`, `metadata`, `raw_cache` |
| `_parse_osm_ways()` | Extrai `way[highway]` do JSON | JSON Overpass | Lista de ways |
| `_build_nodes_dict()` | Mapa `node_id → (lon, lat)` | JSON Overpass | dict |
| `_create_links_layer()` | JSON → QgsVectorLayer LineString (memory) | `ways, nodes_dict` | `QgsVectorLayer` (osm_links_raw) |
| `_extract_nodes_from_layer()` | **Detecta `isMultipart()`** — extremidades de linhas | `QgsVectorLayer` (LineString/MultiLineString) | set de (lon, lat) |
| `_create_nodes_layer()` | set (lon, lat) → QgsVectorLayer Point (memory) | set | `QgsVectorLayer` (osm_nodes) |
| `_recorta_poligono()` | Wrapper `native:clip` — recorta ao polígono | `layer, poligono` | `QgsVectorLayer` clipped |
| `_municipio_poligono()` | Traz polígono do município via `gisbr:read_municipality` | `code_muni` | `QgsVectorLayer` (município) |

---

### 3️⃣ Fonte declarada em `core/sources.py`

```python
{
    "id": "osm_vias",
    "eixo": "transportes",
    "nome": "OSM — Vias urbanas (Overpass)",
    "protocolo": "osm",  # ← detector em diagnostico.py (ainda falta)
    "licenca": "OpenStreetMap contributors"
}
```

---

### 4️⃣ Motor do diagnóstico (`core/diagnostico.py`)

```python
def carregar_fontes(
    source_ids,        # ["dnit_snv", "osm_vias", "sicar_imoveis"]
    code_muni,         # "3118402" (Contagem)
    nome_muni,         # "Contagem"
    bbox,              # (-44.05, -19.95, -43.95, -19.85)
    gpkg_path,         # "/home/diego/.cache/gisbr-diagnostico/diagnose_3118402.gpkg"
    force=False,       # se True, refetch mesmo com cache
    feedback=None      # PyQGIS feedback para log
):
    """
    Loop sobre cada source_id:
      if protocolo == "wfs":      → wfs.carregar_wfs()
      elif protocolo == "arcgis": → arcgis_rest.carregar_arcgis()
      elif protocolo == "geobr":  → processing.run("gisbr:read_*")
      elif protocolo == "osm":    → ❌ AQUI FALTA A INTEGRAÇÃO (T-OSM-001)
      elif protocolo == "basemap": → basemap.add_basemap()
    """
```

---

## 🔴 O que falta (Task T-OSM-001)

**Integrar protocolo `osm` em `diagnostico.py::carregar_fontes()`**

### Pseudocódigo esperado:

```python
elif protocolo == "osm":
    from . import osm_pipeline  # import local (dentro d condition)
    
    # Buscar dados
    result = osm_pipeline.build_osm_municipal_network(
        code_muni=code_muni,
        nome_muni=nome_muni,
        gpkg_path=gpkg_path,
        force=force,
        feedback=feedback
    )
    
    # Verificar sucesso
    if result["layers"]["osm_links"] is not None:
        # Adicionar camadas ao projeto
        QgsProject.instance().addMapLayer(result["layers"]["osm_links"])
        QgsProject.instance().addMapLayer(result["layers"]["osm_nodes"])
        adicionado.append(source_id)
    else:
        pulou.append(source_id)
```

### Detalhes críticos:

1. **Recorte com MultiLineString:**
   - `native:clip` **pode** gerar `MultiLineString` quando vias cruzam a borda do polígono
   - Código já trata isso em `_extract_nodes_from_layer()` linhas 79–86:
     ```python
     if geom.isMultipart():
         polylines = geom.asMultiPolyline()  # ← converte para lista
         for polyline in polylines:
             nodes_set.add((polyline[0].x(), polyline[0].y()))  # início
             if len(polyline) > 1:
                 nodes_set.add((polyline[-1].x(), polyline[-1].y()))  # fim
     ```
   - ✅ **Você não precisa reimplementar isso** — já está pronto.

2. **Persistência no GPKG:**
   - `build_osm_municipal_network()` **já chama** `_grava_gpkg()` internamente (linha 209–215)
   - Camadas são gravadas com nomes:
     - `osm_links_<code_muni>` → LineString das vias
     - `osm_nodes_<code_muni>` → Points dos nós

3. **Cache de consulta Overpass:**
   - Mantém JSON em disco (`cache_dir/osm_overpass_{code_muni}.json`)
   - Reutiliza se `force=False`
   - Evita múltiplas consultas ao servidor

---

## 🧪 Teste esperado (após T-OSM-001)

**No Console Python do QGIS:**

```python
# Já assumindo que T-OSM-001 foi done
import processing
from qgis.core import QgsProject

# Simular download de diagnóstico de Contagem/MG
processing.run("gisbr_diagnostico", {
    "UF": "MG",
    "MUNI": "Contagem",
    "EIXOS": ["transportes"],  # inclui osm_vias
    "GPKG": "/tmp/contagem_diag.gpkg"
})

# Verificar se as camadas foram criadas
project = QgsProject.instance()
layers = [l.name() for l in project.mapLayers().values()]
assert "osm_links_3118402" in layers
assert "osm_nodes_3118402" in layers
print("✅ Vias e nós carregados com sucesso")

# Inspecionar features
vias = project.mapLayersByName("osm_links_3118402")[0]
print(f"Total de vias: {vias.featureCount()}")
print(f"Atributos: {[f.name() for f in vias.fields()]}")
```

**Visualmente no QGIS:**
- Painel dock > UF="MG" > Município="Contagem" > checkbox "Transportes" > "Baixar"
- Aguarda ~30 segundos (Overpass + clip + gravação)
- Mapa mostra todas as vias urbanas de Contagem, recortadas ao limite municipal
- Points vermelhos nos nós de extremidade (interseções)

---

## 📐 Fluxo de dados

```
┌──────────────────────────────────────┐
│  Painel Dock: "Transportes" selecionado  │
└─────────────┬──────────────────────────┘
              │
              ↓
┌──────────────────────────────────────┐
│  diagnostico.py::carregar_fontes()        │
│  (itera source_ids=["osm_vias", ...])     │
└─────────────┬──────────────────────────┘
              │
              ↓ detecta protocolo="osm"
┌──────────────────────────────────────┐
│  osm_pipeline.build_osm_municipal_network()  │
└─────────────┬──────────────────────────┘
              │
      ┌───────┴──────────┬──────────────┬──────────────────┐
      ↓                  ↓              ↓                  ↓
  consultaOverpass    parseJSON    recortaPolígono   gravaGeoPackage
  _municipio_poligono_parse_ways_create_links_layer_
  bbox→JSON           →ways+nodes_→_recorta_poligono→osm_links.gpkg
  (30s)                     ↓
                    _extract_nodes_from_layer
                    (detecta isMultipart, deduplica)
                              ↓
                    _create_nodes_layer
                         ↓
                    osm_nodes.gpkg
```

---

## ✅ Checklist para T-OSM-001

- [ ] Ler esta arquitetura
- [ ] Abrir `ACTIONS.md` e ler `[T-OSM-001]` completo
- [ ] Editar `diagnostico.py::carregar_fontes()` → adicionar `elif protocolo == "osm"`
- [ ] Testar sintaxe: `python3 -m py_compile core/diagnostico.py`
- [ ] Teste no Console QGIS (painel dock → Contagem → Transportes → Baixar)
- [ ] Verificar GPKG: `gdalinfo /caminho/ao/gpkg | grep osm_links`
- [ ] Visualizar no mapa (deve estar recortado, não bbox-retângulo)

---

## 🔗 Referências
- `CLAUDE.md` §1.2 — Estado do diagnóstico
- `core/diagnostico.py` — motor (`carregar_fontes`)
- `core/osm_pipeline.py` — pipeline completa
- `skill proj-gisbr` → `references/osm-municipal-pattern.md`
- **ACTIONS.md `[T-OSM-001]`** — spec detalhada da task
