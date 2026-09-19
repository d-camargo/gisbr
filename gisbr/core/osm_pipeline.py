# -*- coding: utf-8 -*-
"""Pipeline OSM municipal: JSON Overpass → topologia real → camadas QGIS.

Converte o resultado do Overpass em "arcos" (segmentos de via com a
topologia real do OSM — dois ways conectados sse compartilham um
`node_id`, ver `osm_topologia.py`) e gera três camadas: `osm_links`
(arcos), `osm_nodes` (nós from/to dos arcos mantidos) e `osm_problemas`
(achados de verificação geométrica/topológica), recortadas ao município.
"""
import math
import os
from pathlib import Path

from qgis.core import (QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
                       QgsPoint, QgsPointXY, QgsLineString, QgsFields,
                       QgsDistanceArea, QgsSpatialIndex, QgsRectangle,
                       QgsWkbTypes)

from . import qgis_compat
from .connectors import osm
from .osm_topologia import constroi_arcos, diagnostica

# Tolerância de "ponta quase conectada" (D — verificação geométrica a).
TOL_PONTA_M = 10.0

_URI_TIPOS = {"int": "long", "double": "double", "string": "string"}

_LINK_FIELDS = [
    ("arc_id", "int"), ("way_id", "int"), ("seq", "int"),
    ("from_node", "int"), ("to_node", "int"),
    ("highway", "string"), ("name", "string"), ("oneway", "string"),
    ("bridge", "string"), ("tunnel", "string"), ("layer", "string"),
    ("componente", "int"), ("componente_tam", "int"),
]

_NODE_FIELDS = [
    ("node_id", "int"), ("x", "double"), ("y", "double"),
    ("grau", "int"), ("componente", "int"),
]

_PROBLEMA_FIELDS = [
    ("tipo", "string"), ("severidade", "string"), ("detalhe", "string"),
    ("node_id", "int"), ("arc_id", "int"),
]


def _uri(geometry_type, campos):
    partes = "".join("&field={}:{}".format(nome, _URI_TIPOS[kind]) for nome, kind in campos)
    return "{}?crs=EPSG:4674{}".format(geometry_type, partes)


def _fields(campos):
    fields = QgsFields()
    for nome, kind in campos:
        fields.append(QgsField(nome, qgis_compat.field_type(kind)))
    return fields


def _parse_osm_ways(payload):
    """Extrai ways com tag highway do JSON Overpass."""
    if not payload or "elements" not in payload:
        return []
    ways = [e for e in payload["elements"] if e.get("type") == "way" and "tags" in e and "highway" in e["tags"]]
    return ways


def _build_nodes_dict(payload):
    """Cria mapa node_id → (lon, lat) do JSON Overpass."""
    nodes_dict = {}
    if payload and "elements" in payload:
        for el in payload["elements"]:
            if el.get("type") == "node" and "lat" in el and "lon" in el:
                nodes_dict[el["id"]] = (el["lon"], el["lat"])
    return nodes_dict


def _arco_para_linestring(arco):
    """Converte um arco (dict de osm_topologia) em QgsLineString (EPSG:4674 lon,lat)."""
    pts = [QgsPoint(lon, lat) for lon, lat in arco["coords"]]
    return QgsLineString(pts) if len(pts) >= 2 else None


def _arco_para_geometria(arco):
    ls = _arco_para_linestring(arco)
    return QgsGeometry(ls) if ls is not None else None


def _cria_links_raw(arcos, diag, layer_name="osm_links_raw"):
    """Cria a camada LineString de TODOS os arcos (antes do recorte municipal)."""
    layer = QgsVectorLayer(_uri("LineString", _LINK_FIELDS), layer_name, "memory")
    campos = _fields(_LINK_FIELDS)
    layer.startEditing()

    node_comp = diag["node_comp"]
    comp_tam = diag["comp_tam"]
    for arco in arcos:
        geom = _arco_para_linestring(arco)
        if geom is None:
            continue
        feat = QgsFeature(campos)
        feat.setGeometry(QgsGeometry(geom))
        comp = node_comp.get(arco["from_node"])
        feat["arc_id"] = arco["arc_id"]
        feat["way_id"] = arco["way_id"]
        feat["seq"] = arco["seq"]
        feat["from_node"] = arco["from_node"]
        feat["to_node"] = arco["to_node"]
        feat["highway"] = arco["highway"]
        feat["name"] = arco["name"]
        feat["oneway"] = arco["oneway"]
        feat["bridge"] = arco["bridge"]
        feat["tunnel"] = arco["tunnel"]
        feat["layer"] = arco["layer"]
        feat["componente"] = comp
        feat["componente_tam"] = comp_tam.get(comp)
        layer.addFeature(feat)

    layer.commitChanges()
    return layer


def _filtra_arcos_por_poligono(links_raw, engine, layer_name="osm_links"):
    """Mantém o arco INTEIRO se intersecta o polígono do município.

    Mudança deliberada em relação ao `native:clip`: clip cortaria o arco e
    deixaria `from_node`/`to_node` apontando para um nó fora da geometria
    resultante. `engine` já vem preparado (`QgsGeometry.createGeometryEngine`
    + `prepareGeometry`), mesmo padrão de `poi_pipeline.py`.
    """
    layer = QgsVectorLayer(_uri("LineString", _LINK_FIELDS), layer_name, "memory")
    campos = _fields(_LINK_FIELDS)
    layer.startEditing()

    for feat_raw in links_raw.getFeatures():
        geom = feat_raw.geometry()
        if geom is None or geom.isEmpty():
            continue
        # engine.intersects exige QgsAbstractGeometry vivo (constGet() de
        # geometria temporária mente — medido; `geom` fica na variável até
        # o fim do uso, então o ponteiro segue válido).
        if not engine.intersects(geom.constGet()):
            continue
        feat = QgsFeature(campos)
        feat.setGeometry(QgsGeometry(geom))
        for nome, _kind in _LINK_FIELDS:
            feat[nome] = feat_raw[nome]
        layer.addFeature(feat)

    layer.commitChanges()
    return layer


def _cria_nodes_layer(osm_links, diag, nodes_dict, layer_name="osm_nodes"):
    """Um ponto por node_id referenciado como from/to dos arcos mantidos."""
    node_ids = set()
    for feat in osm_links.getFeatures():
        node_ids.add(feat["from_node"])
        node_ids.add(feat["to_node"])

    layer = QgsVectorLayer(_uri("Point", _NODE_FIELDS), layer_name, "memory")
    campos = _fields(_NODE_FIELDS)
    layer.startEditing()

    grau_map = diag["grau"]
    comp_map = diag["node_comp"]
    for node_id in sorted(node_ids):
        if node_id not in nodes_dict:
            continue
        lon, lat = nodes_dict[node_id]
        feat = QgsFeature(campos)
        feat.setGeometry(QgsGeometry(QgsPoint(lon, lat)))
        feat["node_id"] = node_id
        feat["x"] = lon
        feat["y"] = lat
        feat["grau"] = grau_map.get(node_id, 0)
        feat["componente"] = comp_map.get(node_id)
        layer.addFeature(feat)

    layer.commitChanges()
    return layer


def _medidor_area():
    d = QgsDistanceArea()
    d.setEllipsoid("GRS80")  # elipsoide do SIRGAS 2000, mesmo padrão de poi_pipeline
    return d


def _geometria_municipio(municipio):
    geoms = [f.geometry() for f in municipio.getFeatures()
             if f.geometry() and not f.geometry().isEmpty()]
    if not geoms:
        return None
    if len(geoms) == 1:
        return geoms[0]
    return geoms[0].unaryUnion(geoms[1:])


def _bbox_tolerancia_graus(lon, lat, tol_m):
    dlat = tol_m / 111320.0
    dlon = tol_m / (111320.0 * max(math.cos(math.radians(lat)), 1e-6))
    return QgsRectangle(lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def ponta_quase_conectada(arcos, diag, nodes_dict):
    """Nós de grau 1 a <= TOL_PONTA_M de um arco NÃO incidente neles.

    Busca no índice espacial com bbox da tolerância (convertida em graus);
    distância real = ponto ao ponto mais próximo do arco
    (`closestSegmentWithContext`), medida com `QgsDistanceArea` no elipsoide
    do SIRGAS 2000. Uma ocorrência por nó (o arco mais próximo).

    Devolve lista de dicts `{node_id, arc_id, way_id, distancia_m, detalhe}`.
    """
    pontas = [n for n, d in diag["grau"].items() if d == 1]
    if not pontas:
        return []

    index = QgsSpatialIndex()
    geom_por_arco = {}
    for arco in arcos:
        geom = _arco_para_geometria(arco)
        if geom is None:
            continue
        geom_por_arco[arco["arc_id"]] = (geom, arco)
        feat = QgsFeature()
        feat.setId(arco["arc_id"])
        feat.setGeometry(geom)
        index.addFeature(feat)

    medidor = _medidor_area()
    resultados = []
    for node_id in pontas:
        if node_id not in nodes_dict:
            continue
        lon, lat = nodes_dict[node_id]
        pt = QgsPointXY(lon, lat)
        bbox = _bbox_tolerancia_graus(lon, lat, TOL_PONTA_M)
        melhor = None
        for arc_id in index.intersects(bbox):
            geom, arco = geom_por_arco[arc_id]
            if node_id == arco["from_node"] or node_id == arco["to_node"]:
                continue  # arco incidente no próprio nó — ignora
            _sqr_dist, ponto_proximo, _after, _left = geom.closestSegmentWithContext(pt)
            dist_m = medidor.measureLine(pt, QgsPointXY(ponto_proximo))
            if dist_m <= TOL_PONTA_M and (melhor is None or dist_m < melhor[0]):
                melhor = (dist_m, arc_id, arco["way_id"])
        if melhor is not None:
            dist_m, arc_id, way_id = melhor
            resultados.append({
                "node_id": node_id,
                "arc_id": arc_id,
                "way_id": way_id,
                "distancia_m": dist_m,
                "detalhe": "a {:.1f} m do arco {} (way {})".format(dist_m, arc_id, way_id),
            })
    return resultados


def _bridge_tunnel_ativo(valor):
    v = (valor or "").strip().lower()
    return v != "" and v != "no"


def _layer_normalizada(valor):
    v = (valor or "").strip()
    return v if v else "0"


def _pontos_da_intersecao(geom):
    pontos = []
    if geom is None or geom.isEmpty():
        return pontos
    if geom.type() == QgsWkbTypes.GeometryType.PointGeometry:
        if geom.isMultipart():
            for pt in geom.asMultiPoint():
                pontos.append((pt.x(), pt.y()))
        else:
            pt = geom.asPoint()
            pontos.append((pt.x(), pt.y()))
    else:
        # linhas sobrepostas/colecoes: usa os vertices da geometria de intersecao
        for v in geom.vertices():
            pontos.append((v.x(), v.y()))
    return pontos


def cruzamento_sem_no(arcos):
    """Pares de arcos cujas geometrias se cruzam num ponto que NÃO é nó
    compartilhado pelos dois.

    Ignora o par se algum dos dois tem `bridge`/`tunnel` com valor não vazio
    e != "no", ou se `layer` difere (vazio = "0"). Um registro por ponto de
    interseção (par A-B/B-A deduplicado).

    Devolve lista de dicts `{arc_a, arc_b, x, y, detalhe}`.
    """
    geom_por_arco = {}
    index = QgsSpatialIndex()
    for arco in arcos:
        geom = _arco_para_geometria(arco)
        if geom is None:
            continue
        geom_por_arco[arco["arc_id"]] = (geom, arco)
        feat = QgsFeature()
        feat.setId(arco["arc_id"])
        feat.setGeometry(geom)
        index.addFeature(feat)

    resultados = []
    vistos = set()
    for arc_id in sorted(geom_por_arco):
        geom, arco = geom_por_arco[arc_id]
        for cand_id in index.intersects(geom.boundingBox()):
            if cand_id <= arc_id:
                continue  # evita par duplicado (A-B/B-A) e auto-comparação
            geom2, arco2 = geom_por_arco[cand_id]

            if (_bridge_tunnel_ativo(arco["bridge"]) or _bridge_tunnel_ativo(arco["tunnel"])
                    or _bridge_tunnel_ativo(arco2["bridge"]) or _bridge_tunnel_ativo(arco2["tunnel"])):
                continue
            if _layer_normalizada(arco["layer"]) != _layer_normalizada(arco2["layer"]):
                continue
            if not geom.intersects(geom2):
                continue

            inter = geom.intersection(geom2)
            nos_compartilhados = set(arco["nodes"]) & set(arco2["nodes"])
            coords_compartilhadas = {
                tuple(coord) for n, coord in zip(arco["nodes"], arco["coords"])
                if n in nos_compartilhados
            }

            for x, y in _pontos_da_intersecao(inter):
                if any(abs(x - cx) < 1e-9 and abs(y - cy) < 1e-9 for cx, cy in coords_compartilhadas):
                    continue
                chave = (arc_id, cand_id, round(x, 9), round(y, 9))
                if chave in vistos:
                    continue
                vistos.add(chave)
                resultados.append({
                    "arc_a": arc_id, "arc_b": cand_id, "x": x, "y": y,
                    "detalhe": "arcos {} x {}".format(arc_id, cand_id),
                })
    return resultados


def _monta_problemas(arcos, diag, nodes_dict, engine):
    """Monta os registros de `osm_problemas`, filtrados aos pontos DENTRO
    do polígono municipal (`engine` já preparado sobre a geometria do
    município)."""
    def dentro(x, y):
        return engine.contains(QgsPoint(x, y))

    problemas = []

    # ilha / ilha_borda
    nos_por_comp = {}
    for node_id, comp_id in diag["node_comp"].items():
        nos_por_comp.setdefault(comp_id, []).append(node_id)
    for comp_id, n_arcos, representante in diag["ilhas"]:
        coord = nodes_dict.get(representante)
        if coord is None:
            continue
        x, y = coord
        if not dentro(x, y):
            continue
        algum_fora = any(
            not dentro(*nodes_dict[n]) for n in nos_por_comp.get(comp_id, []) if n in nodes_dict
        )
        tipo = "ilha_borda" if algum_fora else "ilha"
        problemas.append({
            "tipo": tipo,
            "severidade": "baixa" if tipo == "ilha_borda" else "alta",
            "detalhe": "componente {}: {} arcos".format(comp_id, n_arcos),
            "node_id": representante, "arc_id": None, "x": x, "y": y,
        })

    # pontas de grau 1: quase conectada (alta) ou solta (baixa)
    quase_conectadas_por_no = {p["node_id"]: p for p in ponta_quase_conectada(arcos, diag, nodes_dict)}
    for node_id in diag["pontas_soltas"]:
        coord = nodes_dict.get(node_id)
        if coord is None:
            continue
        x, y = coord
        if not dentro(x, y):
            continue
        if node_id in quase_conectadas_por_no:
            p = quase_conectadas_por_no[node_id]
            problemas.append({
                "tipo": "ponta_quase_conectada", "severidade": "alta",
                "detalhe": p["detalhe"], "node_id": node_id, "arc_id": p["arc_id"],
                "x": x, "y": y,
            })
        else:
            problemas.append({
                "tipo": "ponta_solta", "severidade": "baixa",
                "detalhe": "", "node_id": node_id, "arc_id": None,
                "x": x, "y": y,
            })

    # mão única sem saída
    for node_id in diag["mao_unica_sem_saida"]:
        coord = nodes_dict.get(node_id)
        if coord is None:
            continue
        x, y = coord
        if not dentro(x, y):
            continue
        problemas.append({
            "tipo": "mao_unica_sem_saida", "severidade": "alta",
            "detalhe": "", "node_id": node_id, "arc_id": None,
            "x": x, "y": y,
        })

    # cruzamento sem nó
    for c in cruzamento_sem_no(arcos):
        x, y = c["x"], c["y"]
        if not dentro(x, y):
            continue
        problemas.append({
            "tipo": "cruzamento_sem_no", "severidade": "media",
            "detalhe": c["detalhe"], "node_id": None, "arc_id": c["arc_a"],
            "x": x, "y": y,
        })

    return problemas


def _cria_problemas_layer(problemas, layer_name="osm_problemas"):
    layer = QgsVectorLayer(_uri("Point", _PROBLEMA_FIELDS), layer_name, "memory")
    campos = _fields(_PROBLEMA_FIELDS)
    layer.startEditing()
    for p in problemas:
        feat = QgsFeature(campos)
        feat.setGeometry(QgsGeometry(QgsPoint(p["x"], p["y"])))
        feat["tipo"] = p["tipo"]
        feat["severidade"] = p["severidade"]
        feat["detalhe"] = p["detalhe"]
        feat["node_id"] = p["node_id"]
        feat["arc_id"] = p["arc_id"]
        layer.addFeature(feat)
    layer.commitChanges()
    return layer


def _resolve_layer(out, layer_name):
    if isinstance(out, str):
        return QgsVectorLayer(out, layer_name, "ogr")
    return out


def _municipio_poligono(code_muni, nome_muni=None):
    import processing
    out = processing.run("gisbr:read_municipality", {
        "CODE": str(code_muni),
        "SIMPLIFIED": True,
        "OUTPUT": "TEMPORARY_OUTPUT",
    })["OUTPUT"]
    layer = _resolve_layer(out, "municipio")
    if layer is None or not layer.isValid():
        return None
    return layer


def _bbox_da_camada(layer):
    extent = layer.extent()
    return (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())


def _vazio(code_muni, nome_muni):
    return {"osm_links_raw": None, "osm_links": None, "osm_nodes": None, "osm_problemas": None}


def build_osm_municipal_network(code_muni, nome_muni, gpkg_path, force=False, feedback=None):
    """Constrói as camadas de topologia OSM (links/nós/problemas) do município."""
    def log(msg):
        if feedback is not None:
            feedback.pushInfo(msg)

    municipio = _municipio_poligono(code_muni, nome_muni)
    if municipio is None:
        return {"raw_cache": None, "layers": _vazio(code_muni, nome_muni),
                "metadata": {"code_muni": str(code_muni), "nome_muni": nome_muni, "erro": "nao foi possivel resolver o municipio"}}

    bbox = _bbox_da_camada(municipio)
    cache_dir = Path(os.path.dirname(gpkg_path) or ".")
    cache_path = cache_dir / "osm_overpass_{}.json".format(code_muni)
    payload = None
    if cache_path.exists() and not force:
        payload = osm.load_overpass_cache(cache_path)
        if payload is not None:
            log(f"OSM: cache reutilizado ({cache_path})")
        else:
            log(f"OSM: cache invalido ou corrompido em {cache_path}, consultando Overpass")
    if payload is None:
        log("OSM: consultando Overpass")
        try:
            payload = osm.fetch_overpass_json(bbox, timeout=180, cache_path=cache_path, feedback=feedback)
            osm.save_overpass_cache(payload, cache_path)
        except osm.OverpassError as e:
            log(f"Erro no Overpass: {e}")
            return {"raw_cache": None, "layers": _vazio(code_muni, nome_muni),
                    "metadata": {"code_muni": str(code_muni), "nome_muni": nome_muni, "erro": str(e)}}

    # Extrair ways e nós, e quebrar em arcos pela topologia real do OSM
    ways = _parse_osm_ways(payload)
    nodes_dict = _build_nodes_dict(payload)
    log(f"OSM: {len(ways)} ways encontrados, {len(nodes_dict)} nós")

    arcos, n_orfaos = constroi_arcos(ways, nodes_dict)
    if n_orfaos:
        log(f"OSM: {n_orfaos} refs de nó órfãs descartadas")

    if not arcos:
        log("OSM: nenhum way com highway encontrado no bbox")
        return {"raw_cache": str(cache_path), "layers": _vazio(code_muni, nome_muni),
                "metadata": {"code_muni": str(code_muni), "nome_muni": nome_muni, "bbox": bbox, "municipio_layer": municipio.name(),
                             "erro": "nenhum way com highway encontrado no bbox", "sem_vias": True}}

    diag = diagnostica(arcos)
    log(f"OSM: {len(arcos)} arcos, {len(diag['comp_tam'])} componentes")

    mun_geom = _geometria_municipio(municipio)
    if mun_geom is None:
        log("OSM: municipio sem geometria valida")
        return {"raw_cache": str(cache_path), "layers": _vazio(code_muni, nome_muni),
                "metadata": {"code_muni": str(code_muni), "nome_muni": nome_muni, "bbox": bbox, "municipio_layer": municipio.name(),
                             "erro": "municipio sem geometria valida"}}

    engine = QgsGeometry.createGeometryEngine(mun_geom.constGet())
    engine.prepareGeometry()

    osm_links_raw = _cria_links_raw(arcos, diag)
    log(f"OSM: {osm_links_raw.featureCount()} arcos no bbox")

    # RECORTE — mudança deliberada: NÃO native:clip (cortaria o arco e
    # deixaria from/to apontando para nó fora da geometria). Mantém o arco
    # inteiro se intersecta o polígono municipal.
    osm_links = _filtra_arcos_por_poligono(osm_links_raw, engine)
    if osm_links.featureCount() == 0:
        log("OSM: nenhum arco intersecta o polígono municipal")
        return {"raw_cache": str(cache_path), "layers": dict(_vazio(code_muni, nome_muni), osm_links_raw=osm_links_raw),
                "metadata": {"code_muni": str(code_muni), "nome_muni": nome_muni, "bbox": bbox, "municipio_layer": municipio.name(),
                             "erro": "nenhum arco intersecta o poligono municipal"}}

    log(f"OSM: {osm_links.featureCount()} arcos dentro do município (arco inteiro, sem clip)")

    osm_nodes = _cria_nodes_layer(osm_links, diag, nodes_dict)
    log(f"OSM: {osm_nodes.featureCount()} nós (from/to dos arcos mantidos)")

    # Verificações geométricas/topológicas sobre TODOS os arcos (antes do
    # filtro por município); só entram problemas com o ponto dentro do
    # polígono.
    problemas = _monta_problemas(arcos, diag, nodes_dict, engine)
    osm_problemas = _cria_problemas_layer(problemas)

    contagem_tipos = {}
    for p in problemas:
        contagem_tipos[p["tipo"]] = contagem_tipos.get(p["tipo"], 0) + 1
    if contagem_tipos:
        log("OSM: verificação — " + ", ".join("{}: {}".format(k, v) for k, v in sorted(contagem_tipos.items())))
    else:
        log("OSM: verificação — nenhum problema encontrado")

    # ponytail: gravar em GeoPackage (reutiliza _grava_gpkg existente)
    from .diagnostico import _grava_gpkg
    ok_links, _ = _grava_gpkg(osm_links, gpkg_path, f"osm_links_{code_muni}")
    ok_nodes, _ = _grava_gpkg(osm_nodes, gpkg_path, f"osm_nodes_{code_muni}")
    ok_problemas, _ = _grava_gpkg(osm_problemas, gpkg_path, f"osm_problemas_{code_muni}")
    if ok_links:
        log(f"OSM: gravados {osm_links.featureCount()} arcos em osm_links.gpkg")
    if ok_nodes:
        log(f"OSM: gravados {osm_nodes.featureCount()} nós em osm_nodes.gpkg")
    if ok_problemas:
        log(f"OSM: gravados {osm_problemas.featureCount()} problemas em osm_problemas.gpkg")

    return {
        "raw_cache": str(cache_path),
        "layers": {"osm_links_raw": osm_links_raw, "osm_links": osm_links, "osm_nodes": osm_nodes, "osm_problemas": osm_problemas},
        "metadata": {
            "code_muni": str(code_muni),
            "nome_muni": nome_muni,
            "bbox": bbox,
            "municipio_layer": municipio.name(),
            "links_raw": osm_links_raw.featureCount(),
            "links_clipped": osm_links.featureCount(),
            "nodes": osm_nodes.featureCount(),
            "arcos": len(arcos),
            "orfaos": n_orfaos,
            "componentes": len(diag["comp_tam"]),
            "verificacao": contagem_tipos,
            "gpkg_ok": ok_links and ok_nodes and ok_problemas,
        },
    }
