# 🏗️ Guia Rápido para Junior — T-OSM-001

**Leia isto antes de começar. Tempo: ~5 min.**

---

## Onde está cada coisa?

| O quê | Arquivo | Status | Seu trabalho |
|-------|---------|--------|-------------|
| **Fonte declarada** | `core/sources.py` L.30-31 | ✅ Pronto | NÃO EDITAR |
| **Conector Overpass** | `core/connectors/osm.py` | ✅ Pronto | Só usar |
| **Pipeline JSON→QgsLayer** | `core/osm_pipeline.py` | ✅ Pronto | Só usar |
| **Motor diagnóstico** | `core/diagnostico.py` | 🔴 **INCOMPLETO** | **VOCÊ EDITA AQUI** |
| **Task detalhada** | `ACTIONS.md [T-OSM-001]` | ✅ Pronto | Siga passo a passo |
| **Arquitetura visual** | `OSM_ARQUITETURA.md` | ✅ Pronto | Consulte quando tiver dúvida |

---

## O que você precisa fazer (Resumo)

**Um arquivo. Uma função. Uma condição.**

```python
# Arquivo: core/diagnostico.py
# Função: carregar_fontes()
# Adicione isto no loop if/elif:

elif protocolo == "osm":
    from . import osm_pipeline
    
    result = osm_pipeline.build_osm_municipal_network(
        code_muni=code_muni,
        nome_muni=nome_muni,
        gpkg_path=gpkg_path,
        force=force,
        feedback=feedback
    )
    
    if result["layers"]["osm_links"] is not None:
        QgsProject.instance().addMapLayer(result["layers"]["osm_links"])
        QgsProject.instance().addMapLayer(result["layers"]["osm_nodes"])
        adicionado.append(source_id)
    else:
        pulou.append(source_id)
```

**É isto.** Não precisa reimplementar nada. `osm_pipeline` já faz TODO O RESTO:
- Busca Overpass
- Converte JSON
- Recorta (MultiLineString já é tratado lá)
- Grava GPKG
- Retorna dict com status

---

## Validação sua (antes de chamar senior)

### 1. ✅ Sintaxe

```bash
python3 -m py_compile core/diagnostico.py
# Nenhuma output = sucesso; se der erro, mostre
```

### 2. ✅ Teste no QGIS Console

```python
# Copie/cola NO Console Python do QGIS (não em terminal):
from qgis.core import QgsProject
from gisbr.core.diagnostico import carregar_fontes

result = carregar_fontes(
    source_ids=["osm_vias"],
    code_muni="3118402",
    nome_muni="Contagem",
    bbox=(-44.05, -19.95, -43.95, -19.85),
    gpkg_path="/tmp/test_osm.gpkg",
    municipio_layer=None,  # deixa ser None por enquanto
    force=True,
    feedback=None  # deixa ser None
)

print(f"✅ Adicionado: {result[0]}")
print(f"❌ Pulou: {result[1]}")

# Se vir "✅ Adicionado: ['osm_vias']" = funciona!
```

### 3. ✅ Visualize no mapa

- Painel dock diagnóstico
- UF = "MG"
- Município = "Contagem"
- Checkbox "Transportes" (que contém `osm_vias`)
- Botão "Baixar"
- Espere ~30s
- Deve aparecer 2 camadas novas: `osm_links_3118402` + `osm_nodes_3118402`
- Zoom para ver as vias (linha vermelha = vias; ponto vermelho = nó)

---

## Se travar ou tiver dúvida

**Leia nesta ordem:**

1. `ACTIONS.md` — [T-OSM-001] tem MUITO detalhe (código de exemplo, armadilhas, etc.)
2. `OSM_ARQUITETURA.md` — visual + fluxo de dados
3. `core/diagnostico.py` — veja como otros protocolos (WFS, ArcGIS) implementam (copie o padrão)
4. `core/osm_pipeline.py` — veja o que cada função retorna

**Se precisar de ajuda: ping o senior** (Diego ou eu) com:
- A linha de `diagnostico.py` onde está travado
- O erro exato (`Traceback` completo)
- O que você tentou

---

## Importante: ARMADILHAS

### ❌ Não faça isto:

- **Não edite** `sources.py` (fonte já está registrada)
- **Não edite** `provider.py` ou `metadata.txt` (quebra o plugin)
- **Não adicione import no topo** (`from . import osm_pipeline`) — só dentro da condição `elif`
- **Não reimplemente** `fetch_overpass_json()` ou `_create_links_layer()` — já existe
- **Não ignore** `feedback.pushWarning()` — use para erros (Overpass indisponível)

### ✅ Faça isto:

- Import **dentro** da condição `elif protocolo == "osm"`
- Use `osm_pipeline.build_osm_municipal_network()` (é a orquestração completa)
- Adicione ambas as camadas (links + nodes) ao projeto
- Teste com `code_muni="3118402"` (Contagem é conhecida, fácil debugar)

---

## Timeline esperada

| Etapa | Tempo | Fazer |
|-------|-------|-------|
| 1. Ler esta guia + `ACTIONS.md` | 15 min | Entender o escopo |
| 2. Ler `osm_pipeline.py` | 10 min | Ver o que existe |
| 3. Editar `diagnostico.py` | 15 min | Adicionar condição OSM |
| 4. Teste local (Console QGIS) | 30 min | Validar funcional |
| 5. Documentar resultado | 5 min | Preencher "Resultado" em `ACTIONS.md` |

**Total: ~75 min**

Se travar no "Teste local", pare aí e chame o senior. Diag senior pode completar de novo. Não perca tempo refazendo.

---

## Links rápidos

- Task: `ACTIONS.md` busque por `## [T-OSM-001]`
- Código: `core/diagnostico.py` busque por `def carregar_fontes`
- Padrão OSM: `core/osm_pipeline.py` função `build_osm_municipal_network`
- Exemplo de outro protocolo: `core/diagnostico.py` busque por `elif protocolo == "wfs"`

---

**Estou pronto. Abra `ACTIONS.md [T-OSM-001]` e comece! 🚀**
