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
from .osm_topologia import constroi_arcos, diagnostica, velocidade_kmh

# Tolerância de "ponta quase conectada" (D — verificação geométrica a).
TOL_PONTA_M = 10.0

# Severidade estratificada por distância: erro de digitalização real fica
# em poucos metros; a cauda de 7-10 m medida em Contagem é majoritariamente
# via paralela que legitimamente não se liga (não é bug de traçado).
TOL_PONTA_ALTA_M = 3.0

_URI_TIPOS = {"int": "long", "double": "double", "string": "string"}

_LINK_FIELDS = [
    ("arc_id", "int"), ("way_id", "int"), ("seq", "int"),
    ("from_node", "int"), ("to_node", "int"),
    ("highway", "string"), ("name", "string"), ("oneway", "string"),
    ("bridge", "string"), ("tunnel", "string"), ("layer", "string"),
    ("veicular", "int"), ("pedestre", "int"),
    # `componente`/`componente_tam` sao GENERICOS: refletem a rede que
    # rodou nesta execucao (ver `metadata["rede"]` em `compute_osm_network`),
    # nao mais fixos em veicular com um par `_pe` — cada execucao roda uma
    # unica rede, entao nao ha por que carregar os dois pares sempre.
    ("componente", "int"), ("componente_tam", "int"),
    # atributos de custo p/ o logis parar de calcular por conta propria
    # (`_parse_speed`/`_calcular_comprimento_metros` em
    # ~/projects/logis/logis/core/network/osm_pipeline.py). `comprimento_m`
    # e do ARCO INTEIRO (mesma geometria de `osm_links`), inclusive quando o
    # arco cruza a divisa municipal — nao e recortado na fronteira.
    ("maxspeed", "string"), ("velocidade_kmh", "double"), ("comprimento_m", "double"),
]

_NODE_FIELDS = [
    ("node_id", "int"), ("x", "double"), ("y", "double"),
    # `grau`/`componente` GENERICOS, da rede que rodou nesta execucao — nao
    # mais fixos em veicular com um par `grau_pe`/`componente_pe`.
    ("grau", "int"),
    ("componente", "int"),
]

_PROBLEMA_FIELDS = [
    ("tipo", "string"), ("severidade", "string"), ("detalhe", "string"),
    ("node_id", "int"), ("arc_id", "int"), ("rede", "string"),
]


def _reporta_progresso(feedback, pct, texto=None):
    """`feedback` é sempre opcional — protege todas as chamadas para quem
    roda o núcleo sem UI (script, teste, chamada direta sem painel)."""
    if feedback is None:
        return
    if texto is not None:
        feedback.setProgressText(texto)
    feedback.setProgress(pct)


def _interpola(faixa, fracao):
    if faixa is None:
        return None
    lo, hi = faixa
    return lo + (hi - lo) * fracao


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


def _cria_links_raw(arcos, diag, rede, layer_name="osm_links_raw"):
    """Cria a camada LineString de TODOS os arcos (antes do recorte municipal).

    `componente`/`componente_tam` são da rede que RODOU nesta execução
    (`rede`, `diag` = `diagnostica(arcos_todos, rede)` — ver
    `compute_osm_network`) — -1/None se o arco não pertence a ela.
    `veicular`/`pedestre` seguem vindo de graça da classificação do arco
    (`classifica_modos`), independente de `rede`.
    """
    layer = QgsVectorLayer(_uri("LineString", _LINK_FIELDS), layer_name, "memory")
    campos = _fields(_LINK_FIELDS)
    layer.startEditing()

    node_comp = diag["node_comp"]
    comp_tam = diag["comp_tam"]
    medidor = _medidor_area()
    for arco in arcos:
        geom = _arco_para_linestring(arco)
        if geom is None:
            continue
        qgeom = QgsGeometry(geom)
        feat = QgsFeature(campos)
        feat.setGeometry(qgeom)
        if arco.get(rede):
            comp = node_comp.get(arco["from_node"], -1)
        else:
            comp = -1
        comp_tam_val = comp_tam.get(comp) if comp != -1 else None
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
        feat["veicular"] = 1 if arco["veicular"] else 0
        feat["pedestre"] = 1 if arco["pedestre"] else 0
        feat["componente"] = comp
        feat["componente_tam"] = comp_tam_val
        feat["maxspeed"] = arco.get("maxspeed", "")
        feat["velocidade_kmh"] = velocidade_kmh(arco)
        feat["comprimento_m"] = medidor.measureLength(qgeom)
        layer.addFeature(feat)

    layer.commitChanges()
    return layer


def _filtra_arcos(arcos, engine):
    """Mantém o arco INTEIRO se intersecta o polígono do município.

    Sucessora de `_filtra_arcos_por_poligono`: opera sobre uma LISTA de
    arcos — dados puros, nunca uma `QgsVectorLayer` — porque roda dentro de
    `compute_osm_network`, que uma `QgsTask` pode chamar fora da thread
    principal. Devolve a lista dos arcos mantidos, na mesma ordem.

    Mudança deliberada em relação ao `native:clip`: clip cortaria o arco e
    deixaria `from_node`/`to_node` apontando para um nó fora da geometria
    resultante. `engine` já vem preparado (`QgsGeometry.createGeometryEngine`
    + `prepareGeometry`), mesmo padrão de `poi_pipeline.py`.
    """
    mantidos = []
    for arco in arcos:
        geom = _arco_para_geometria(arco)
        if geom is None or geom.isEmpty():
            continue
        # engine.intersects exige QgsAbstractGeometry vivo (constGet() de
        # geometria temporária mente — medido; `geom` fica na variável até
        # o fim do uso, então o ponteiro segue válido).
        if not engine.intersects(geom.constGet()):
            continue
        mantidos.append(arco)
    return mantidos


def _cria_nodes_layer(arcos, diag, nodes_dict, layer_name="osm_nodes"):
    """Um ponto por node_id referenciado como from/to dos arcos mantidos.

    `arcos` é a LISTA de arcos mantidos (dados puros), não a camada
    `osm_links` — o node_id é lido direto do dict do arco
    (`from_node`/`to_node`), sem depender de `QgsVectorLayer.getFeatures()`.

    `grau`/`componente` são GENÉRICOS, da rede que rodou nesta execução
    (`diag`, ver `compute_osm_network`) — não mais fixos em veicular com um
    par `grau_pe`/`componente_pe`.
    """
    node_ids = set()
    for arco in arcos:
        node_ids.add(arco["from_node"])
        node_ids.add(arco["to_node"])

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
        feat["componente"] = comp_map.get(node_id, -1)
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


def ponta_quase_conectada(arcos, diag, nodes_dict, feedback=None, faixa=None):
    """Nós de grau 1 a <= TOL_PONTA_M de um arco NÃO incidente neles.

    Busca no índice espacial com bbox da tolerância (convertida em graus);
    distância real = ponto ao ponto mais próximo do arco
    (`geom.nearestPoint(...)`), medida com `QgsDistanceArea` no elipsoide
    do SIRGAS 2000. Uma ocorrência por nó (o arco mais próximo).

    NÃO usar `closestSegmentWithContext`: medido devolvendo `(0.0, pt, ...)`
    — o próprio ponto de busca como "ponto mais próximo" — quando `pt` cai
    dentro do bbox de busca do arco mas fora da geometria dele, inflando
    toda ponta cujo bbox de tolerância toca outro arco em falso positivo a
    0,0 m.

    `feedback`/`faixa` (tupla `(lo, hi)`) são opcionais — a cada ~200 nós
    reporta progresso interpolado dentro de `faixa` e verifica
    `feedback.isCanceled()`; se cancelado, interrompe o laço e devolve os
    achados parciais (quem decide abortar o pipeline é o chamador).

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
    total = len(pontas)
    resultados = []
    for i, node_id in enumerate(pontas):
        if feedback is not None and i % 200 == 0:
            if feedback.isCanceled():
                break
            pct = _interpola(faixa, i / total) if total else None
            if pct is not None:
                _reporta_progresso(feedback, int(pct))
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
            ponto_proximo = geom.nearestPoint(QgsGeometry.fromPointXY(pt)).asPoint()
            dist_m = medidor.measureLine(pt, ponto_proximo)
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


def cruzamento_sem_no(arcos, feedback=None, faixa=None):
    """Pares de arcos cujas geometrias se cruzam num ponto que NÃO é nó
    compartilhado pelos dois.

    Ignora o par se algum dos dois tem `bridge`/`tunnel` com valor não vazio
    e != "no", ou se `layer` difere (vazio = "0"). Um registro por ponto de
    interseção (par A-B/B-A deduplicado).

    `feedback`/`faixa` (tupla `(lo, hi)`) são opcionais — a cada ~200 arcos
    reporta progresso interpolado dentro de `faixa` e verifica
    `feedback.isCanceled()`; se cancelado, interrompe o laço e devolve os
    achados parciais (quem decide abortar o pipeline é o chamador).

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
    arc_ids_ordenados = sorted(geom_por_arco)
    total = len(arc_ids_ordenados)
    for i, arc_id in enumerate(arc_ids_ordenados):
        if feedback is not None and i % 200 == 0:
            if feedback.isCanceled():
                break
            pct = _interpola(faixa, i / total) if total else None
            if pct is not None:
                _reporta_progresso(feedback, int(pct))
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


def _monta_problemas(arcos_rede, diag, nodes_dict, engine, rede,
                      incluir_pontas_soltas=False, feedback=None, faixa=None):
    """Monta os registros de `osm_problemas` de UMA rede (`rede` =
    "veicular"|"pedestre"), filtrados aos pontos DENTRO do polígono
    municipal (`engine` já preparado sobre a geometria do município).

    `arcos_rede`/`diag` já vêm filtrados para a rede pedida (ver
    `diagnostica(arcos, rede)`).

    Por padrão (`incluir_pontas_soltas=False`) `ponta_solta` NÃO é emitido —
    beco sem saída/entrada de garagem/acesso de condomínio é o normal da
    malha viária, não um erro, e em Contagem eram 2593 dos ~3,9 mil pontos
    da camada, afogando o que de fato pede atenção. A contagem NUNCA é
    descartada muda: quantas seriam listadas sai no segundo item da tupla
    devolvida (`ponta_solta_nao_listadas`). `incluir_pontas_soltas=True`
    restaura a listagem. Na rede pedestre `ponta_solta` nunca é emitido nem
    contado (becos de calçada são a norma, não pedem contagem à parte).

    `mao_unica_sem_saida`/`mao_unica_borda` saem UM PONTO POR GRUPO (SCC),
    não um por nó — a armadilha (o sentido único sem volta) é do grupo, não
    de cada nó dele; um ponto por nó era ruído redundante. O representante é
    o menor `node_id` do grupo que esteja dentro do polígono, e `detalhe`
    ganha "N nós" (tamanho do grupo).

    `faixa` (tupla `(lo, hi)`) é dividida ao meio entre os dois laços
    longos — `ponta_quase_conectada` (primeira metade) e `cruzamento_sem_no`
    (segunda metade) — que reportam progresso e checam
    `feedback.isCanceled()` por conta própria.

    Devolve `(problemas, ponta_solta_nao_listadas)`.
    """
    meio = _interpola(faixa, 0.5) if faixa is not None else None
    faixa_pontas = (faixa[0], meio) if faixa is not None else None
    faixa_cruzamentos = (meio, faixa[1]) if faixa is not None else None
    def dentro(x, y):
        return engine.contains(QgsPoint(x, y))

    problemas = []
    ponta_solta_nao_listadas = 0

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
            "node_id": representante, "arc_id": None, "x": x, "y": y, "rede": rede,
        })

    # pontas de grau 1: quase conectada (alta se <= TOL_PONTA_ALTA_M, senão
    # media) ou solta (baixa, so fora da rede pedestre)
    quase_conectadas_por_no = {p["node_id"]: p for p in ponta_quase_conectada(
        arcos_rede, diag, nodes_dict, feedback=feedback, faixa=faixa_pontas)}
    for node_id in diag["pontas_soltas"]:
        coord = nodes_dict.get(node_id)
        if coord is None:
            continue
        x, y = coord
        if not dentro(x, y):
            continue
        if node_id in quase_conectadas_por_no:
            p = quase_conectadas_por_no[node_id]
            severidade = "alta" if p["distancia_m"] <= TOL_PONTA_ALTA_M else "media"
            problemas.append({
                "tipo": "ponta_quase_conectada", "severidade": severidade,
                "detalhe": p["detalhe"], "node_id": node_id, "arc_id": p["arc_id"],
                "x": x, "y": y, "rede": rede,
            })
        elif rede != "pedestre":
            if incluir_pontas_soltas:
                problemas.append({
                    "tipo": "ponta_solta", "severidade": "baixa",
                    "detalhe": "", "node_id": node_id, "arc_id": None,
                    "x": x, "y": y, "rede": rede,
                })
            else:
                ponta_solta_nao_listadas += 1

    # mão única sem saída / mão única de borda (sempre vazio para rede
    # pedestre — diagnostica ja garante). Agrupado por SCC (mesmo padrão de
    # ilha/ilha_borda): se algum nó da SCC está fora do polígono, o oneway
    # atravessa a borda e a volta pode estar fora do bbox consultado — não
    # dá pra afirmar que é de fato sem saída, então sai como "borda"
    # (severidade baixa) em vez de "sem_saida" (severidade alta). UM PONTO
    # POR GRUPO — a armadilha, não o nó — representado pelo menor `node_id`
    # do grupo que esteja dentro do polígono (grupo sem nenhum nó dentro
    # não gera ponto algum).
    scc_map = diag["scc"]
    nos_por_scc = {}
    for node_id in diag["mao_unica_sem_saida"]:
        nos_por_scc.setdefault(scc_map.get(node_id), []).append(node_id)
    for scc_id, nos_scc in nos_por_scc.items():
        algum_fora = any(
            not dentro(*nodes_dict[n]) for n in nos_scc if n in nodes_dict
        )
        nos_dentro = sorted(
            n for n in nos_scc if n in nodes_dict and dentro(*nodes_dict[n])
        )
        if not nos_dentro:
            continue
        representante = nos_dentro[0]
        x, y = nodes_dict[representante]
        tipo = "mao_unica_borda" if algum_fora else "mao_unica_sem_saida"
        severidade = "baixa" if algum_fora else "alta"
        problemas.append({
            "tipo": tipo, "severidade": severidade,
            "detalhe": "{} nós".format(len(nos_scc)),
            "node_id": representante, "arc_id": None,
            "x": x, "y": y, "rede": rede,
        })

    # cruzamento sem nó
    for c in cruzamento_sem_no(arcos_rede, feedback=feedback, faixa=faixa_cruzamentos):
        x, y = c["x"], c["y"]
        if not dentro(x, y):
            continue
        problemas.append({
            "tipo": "cruzamento_sem_no", "severidade": "media",
            "detalhe": c["detalhe"], "node_id": None, "arc_id": c["arc_a"],
            "x": x, "y": y, "rede": rede,
        })

    return problemas, ponta_solta_nao_listadas


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
        feat["rede"] = p["rede"]
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


_CACHE_DIR_PADRAO = Path(os.path.expanduser("~/.cache/gisbr-diagnostico"))


def resolve_municipio(code_muni, nome_muni=None):
    """Thread principal: resolve o polígono do município (usa
    `processing.run("gisbr:read_municipality")`) e sua geometria unida
    (`_geometria_municipio`).

    Separado de `build_osm_network_layers` para poder rodar ANTES de
    despachar `OsmNetworkTask` (`core/osm_task.py`) — a tarefa em segundo
    plano recebe `bbox`/`mun_geom` já prontos e nunca chama
    `processing.run`/toca `QgsVectorLayer` fora da thread principal.

    Devolve:
    - `(None, None, None)` se o município não pôde ser resolvido
      (`_municipio_poligono` devolveu `None`);
    - `(municipio_layer, bbox, None)` se resolveu mas a geometria é inválida
      (`mun_geom` sai `None`) — quem decide o que fazer com isso é o
      chamador. IMPORTANTE: a geometria passou a ser CALCULADA aqui, cedo,
      mas a VALIDAÇÃO dela continua onde estava — `compute_osm_network` só
      reporta "município sem geometria válida" DEPOIS de confirmar que há
      vias no bbox (mesma ordem de antes: `sem_vias` na frente de
      "geometria inválida"), não aqui;
    - `(municipio_layer, bbox, mun_geom)` no caminho feliz.
    """
    municipio = _municipio_poligono(code_muni, nome_muni)
    if municipio is None:
        return None, None, None
    bbox = _bbox_da_camada(municipio)
    mun_geom = _geometria_municipio(municipio)
    return municipio, bbox, mun_geom


def compute_osm_network(code_muni, nome_muni, bbox, mun_geom, cache_dir=None, force=False,
                         feedback=None, rede="veicular", incluir_pontas_soltas=False):
    """Núcleo SEM `QgsVectorLayer`/`QgsProject` — dados puros, seguros para
    uma `QgsTask` calcular fora da thread principal.

    Recebe `bbox` e `mun_geom` JÁ resolvidos (ver `resolve_municipio`, que
    roda na thread principal); `mun_geom` pode vir `None` (geometria
    municipal inválida) — a checagem só é feita DEPOIS de confirmar que há
    vias no bbox (mesma ordem de sempre, ver abaixo). Faz a consulta/cache
    do Overpass, `constroi_arcos`, `diagnostica` (de UMA rede — verificar as
    duas redes sempre custava o dobro da etapa mais cara do carregamento
    sem uso para quem só quer roteirização de veículos), o filtro pelo
    polígono municipal (`_filtra_arcos` — lista de arcos, nunca uma camada)
    e a verificação geométrica/topológica (`_monta_problemas`).
    `QgsGeometry`, `QgsSpatialIndex`, `QgsDistanceArea` (usados pelas duas
    últimas etapas) são seguros numa tarefa de fundo; só `QgsVectorLayer`/
    `QgsProject` não são — por isso as camadas são montadas depois, por
    `montar_camadas(dados)`, sempre na thread principal.

    `rede` (`"veicular"` ou `"pedestre"`, default `"veicular"`) escolhe qual
    rede roda — `diagnostica`, o filtro dos arcos usados na verificação e
    `_monta_problemas` usam a mesma; `rede` fora desses dois valores levanta
    `ValueError`. `metadata["rede"]` registra qual rodou (inclusive nos
    caminhos de erro/cancelamento). `incluir_pontas_soltas` (default
    `False`, beco sem saída é o normal da malha, não erro) repassa para
    `_monta_problemas`.

    Devolve um dict de dados puros:
    `{"raw_cache", "arcos_todos", "arcos", "diag", "nodes_dict", "problemas",
      "metadata"}`.

    - Falha no Overpass, ou nenhum way com highway no bbox (`sem_vias`):
      `arcos_todos`/`arcos`/`diag`/`problemas` vêm `None`, e
      `metadata["erro"]` explica a causa (`metadata["sem_vias"] = True` no
      segundo caso).
    - Geometria municipal inválida (`mun_geom is None`), **só reportado
      depois do `sem_vias` acima** — mesma ordem do pipeline de sempre:
      idem (todos os dados `None`, `metadata["erro"] = "municipio sem
      geometria valida"`).
    - Nenhum arco intersecta o polígono municipal: `arcos_todos` vem
      preenchido (para `osm_links_raw`), `arcos` vem `[]`.
    - `feedback.isCanceled()` interrompe a verificação geométrica:
      `metadata["cancelado"] = True`, `arcos_todos`/`arcos`/`diag`
      ficam prontos, só `problemas` vem `None`.
    - Caminho feliz: todas as chaves preenchidas.
    """
    if rede not in ("veicular", "pedestre"):
        raise ValueError("rede invalida: {!r} (use 'veicular' ou 'pedestre')".format(rede))

    def log(msg):
        if feedback is not None:
            feedback.pushInfo(msg)

    base_meta = {"code_muni": str(code_muni), "nome_muni": nome_muni, "bbox": bbox, "rede": rede}

    def dados_vazios(raw_cache, metadata):
        return {"raw_cache": raw_cache, "arcos_todos": None, "arcos": None,
                "diag": None, "nodes_dict": None,
                "problemas": None, "metadata": metadata}

    if cache_dir is None:
        cache_dir = _CACHE_DIR_PADRAO
    else:
        cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "osm_overpass_{}.json".format(code_muni)
    payload = None
    if cache_path.exists() and not force:
        payload = osm.load_overpass_cache(cache_path)
        if payload is not None:
            log(f"OSM: cache reutilizado ({cache_path})")
        else:
            log(f"OSM: cache invalido ou corrompido em {cache_path}, consultando Overpass")
    if payload is None:
        _reporta_progresso(feedback, 5, "Consultando Overpass")
        log("OSM: consultando Overpass")
        try:
            payload = osm.fetch_overpass_json(bbox, timeout=180, cache_path=cache_path, feedback=feedback)
            osm.save_overpass_cache(payload, cache_path)
        except osm.OverpassError as e:
            log(f"Erro no Overpass: {e}")
            return dados_vazios(None, dict(base_meta, erro=str(e)))
    _reporta_progresso(feedback, 25)

    # Extrair ways e nós, e quebrar em arcos pela topologia real do OSM
    ways = _parse_osm_ways(payload)
    nodes_dict = _build_nodes_dict(payload)
    log(f"OSM: {len(ways)} ways encontrados, {len(nodes_dict)} nós")

    _reporta_progresso(feedback, 25, "Construindo topologia")
    arcos_todos, n_orfaos, descartados = constroi_arcos(ways, nodes_dict)
    if n_orfaos:
        log(f"OSM: {n_orfaos} refs de nó órfãs descartadas")
    if descartados:
        log("OSM: descartados " + ", ".join(
            "{}: {}".format(hw or "(vazio)", n) for hw, n in sorted(descartados.items())
        ))

    if not arcos_todos:
        log("OSM: nenhum way com highway encontrado no bbox")
        return dados_vazios(str(cache_path), dict(
            base_meta, erro="nenhum way com highway encontrado no bbox", sem_vias=True))

    diag = diagnostica(arcos_todos, rede)
    log(f"OSM: {len(arcos_todos)} arcos — {rede}: {len(diag['comp_tam'])} componentes")
    _reporta_progresso(feedback, 35)

    # Geometria municipal inválida: checado SÓ AQUI (depois do `sem_vias`
    # acima) — condição do Diego: "sem vias no bbox" tem prioridade sobre
    # "geometria do município inválida", mesmo com a geometria calculada
    # cedo em `resolve_municipio`.
    if mun_geom is None:
        log("OSM: municipio sem geometria valida")
        return dados_vazios(str(cache_path), dict(base_meta, erro="municipio sem geometria valida"))

    engine = QgsGeometry.createGeometryEngine(mun_geom.constGet())
    engine.prepareGeometry()

    _reporta_progresso(feedback, 35, "Filtrando arcos pelo município")
    log(f"OSM: {len(arcos_todos)} arcos no bbox")

    # RECORTE — mudança deliberada: NÃO native:clip (cortaria o arco e
    # deixaria from/to apontando para nó fora da geometria). Mantém o arco
    # inteiro se intersecta o polígono municipal.
    arcos = _filtra_arcos(arcos_todos, engine)
    if not arcos:
        log("OSM: nenhum arco intersecta o polígono municipal")
        return {"raw_cache": str(cache_path), "arcos_todos": arcos_todos, "arcos": [],
                "diag": diag,
                "nodes_dict": nodes_dict, "problemas": None,
                "metadata": dict(base_meta, erro="nenhum arco intersecta o poligono municipal")}

    log(f"OSM: {len(arcos)} arcos dentro do município (arco inteiro, sem clip)")
    _reporta_progresso(feedback, 55)

    # Verificação geométrica/topológica roda UMA VEZ, só sobre os arcos da
    # rede escolhida (antes rodava duas vezes, veicular e pedestre, a cada
    # carregamento — o dobro do custo da etapa mais cara do carregamento,
    # sem uso pra quem só quer a rede veicular) — sobre TODOS os arcos
    # (antes do filtro por município); só entram problemas com o ponto
    # dentro do polígono. `_monta_problemas` subdivide a faixa 55-90 entre os
    # dois laços longos (ver docstring dela).
    _reporta_progresso(feedback, 55, "Verificação geométrica")
    arcos_rede = [a for a in arcos_todos if a.get(rede)]
    problemas, ponta_solta_nao_listadas = _monta_problemas(
        arcos_rede, diag, nodes_dict, engine, rede,
        incluir_pontas_soltas=incluir_pontas_soltas, feedback=feedback, faixa=(55, 90))
    if feedback is not None and feedback.isCanceled():
        return {"raw_cache": str(cache_path), "arcos_todos": arcos_todos, "arcos": arcos,
                "diag": diag,
                "nodes_dict": nodes_dict, "problemas": None,
                "metadata": dict(base_meta, cancelado=True)}

    _reporta_progresso(feedback, 90, "Verificação concluída")

    contagem_tipos = {}
    for p in problemas:
        contagem_tipos[p["tipo"]] = contagem_tipos.get(p["tipo"], 0) + 1
    if contagem_tipos:
        log("OSM: verificação ({}) — ".format(rede) + ", ".join(
            "{}: {}".format(k, v) for k, v in sorted(contagem_tipos.items())
        ))
    else:
        log("OSM: verificação ({}) — nenhum problema encontrado".format(rede))
    if ponta_solta_nao_listadas:
        log("OSM: {} becos sem saida (ponta_solta) nao listados (use INCLUIR_PONTAS_SOLTAS)".format(
            ponta_solta_nao_listadas))

    metadata = dict(base_meta,
        arcos=len(arcos_todos), orfaos=n_orfaos, descartados=descartados,
        componentes={rede: len(diag["comp_tam"])},
        verificacao={rede: contagem_tipos, "ponta_solta_nao_listadas": ponta_solta_nao_listadas},
    )

    return {
        "raw_cache": str(cache_path),
        "arcos_todos": arcos_todos, "arcos": arcos,
        "diag": diag,
        "nodes_dict": nodes_dict, "problemas": problemas,
        "metadata": metadata,
    }


def montar_camadas(dados):
    """Thread principal: monta as quatro `QgsVectorLayer` a partir do dict
    de dados puros devolvido por `compute_osm_network`. Nunca chamar fora
    da thread principal.

    Devolve `{"osm_links_raw", "osm_links", "osm_nodes", "osm_problemas"}`,
    cada uma `None` quando os dados correspondentes não existem — mesma
    regra de sempre: sem `arcos_todos`, as quatro vêm `None`; com
    `arcos_todos` mas sem `arcos` (nenhum arco no polígono, ou geometria
    municipal inválida), só `osm_links_raw` é construída; sem `problemas`
    (cancelado), as três primeiras saem e `osm_problemas` fica `None`.

    `rede` sai de `metadata["rede"]` (default `"veicular"`, para dicts
    antigos/sintéticos de teste sem essa chave) e é repassada a
    `_cria_links_raw` (campos `componente`/`componente_tam` genéricos).
    """
    metadata = dados.get("metadata") or {}
    arcos_todos = dados.get("arcos_todos")
    if not arcos_todos:
        return _vazio(metadata.get("code_muni"), metadata.get("nome_muni"))

    diag = dados["diag"]
    nodes_dict = dados["nodes_dict"]
    rede = metadata.get("rede", "veicular")

    osm_links_raw = _cria_links_raw(arcos_todos, diag, rede)

    arcos = dados.get("arcos")
    if not arcos:
        return {"osm_links_raw": osm_links_raw, "osm_links": None, "osm_nodes": None, "osm_problemas": None}

    osm_links = _cria_links_raw(arcos, diag, rede, layer_name="osm_links")
    osm_nodes = _cria_nodes_layer(arcos, diag, nodes_dict)

    problemas = dados.get("problemas")
    osm_problemas = _cria_problemas_layer(problemas) if problemas is not None else None

    return {"osm_links_raw": osm_links_raw, "osm_links": osm_links, "osm_nodes": osm_nodes, "osm_problemas": osm_problemas}


def osm_vias_ja_existe(existentes, code_muni):
    """`True` se `osm_links_<code_muni>` E `osm_nodes_<code_muni>` já estão
    em `existentes` (ver `diagnostico._layers_existentes(gpkg_path)`).

    Extraído de `carregar_fontes` para o painel (`gui/diagnostico_dock.py`,
    caminho `OsmNetworkTask`) e o motor (`core/diagnostico.py::carregar_fontes`,
    caminho síncrono) checarem a mesma regra de "já existe no GeoPackage"
    sem duplicar a lógica.
    """
    return ("osm_links_{}".format(code_muni) in existentes
            and "osm_nodes_{}".format(code_muni) in existentes)


def build_osm_network_layers(code_muni, nome_muni=None, cache_dir=None, force=False, feedback=None,
                              rede="veicular", incluir_pontas_soltas=False):
    """Monta as camadas OSM (links/nós/problemas) do município EM MEMÓRIA.

    Composição, na thread principal, de `resolve_municipio` (resolve
    município/bbox/geometria) + `compute_osm_network` (dados puros — o
    mesmo núcleo que `OsmNetworkTask` roda em segundo plano) +
    `montar_camadas` (materializa as `QgsVectorLayer`). Faz tudo, inclusive
    o cache do Overpass em `cache_dir` (default `~/.cache/gisbr-diagnostico`,
    criado se não existir), mas NÃO grava GeoPackage. Devolve o MESMO
    formato de dict de sempre (`raw_cache`, `layers`, `metadata`), sem
    `gpkg_ok`.

    `rede`/`incluir_pontas_soltas` (ambos com default que preserva o
    comportamento normal — veicular, sem pontas soltas) são só repassados a
    `compute_osm_network`. É o algoritmo `gisbr:osm_network` quem expõe os
    dois como parâmetro (`REDE`/`PONTAS_SOLTAS`); o painel e
    `build_osm_municipal_network` continuam usando o default.

    `feedback` (um `QgsProcessingFeedback`, sempre opcional) reporta
    progresso via `setProgressText`/`setProgress` em faixas fixas:

    | Faixa  | Etapa                                            |
    |--------|---------------------------------------------------|
    | 0–5    | resolver município                                |
    | 5–25   | consulta ao Overpass (ou cache)                   |
    | 25–35  | `constroi_arcos` + `diagnostica` (rede escolhida) |
    | 35–55  | filtro dos arcos pelo polígono municipal          |
    | 55–90  | verificação geométrica (pontas/cruzamentos)       |
    | 90–100 | montar as camadas (`montar_camadas`)              |

    Dentro da verificação geométrica, `feedback.isCanceled()` é checado a
    cada ~200 itens (ver `ponta_quase_conectada`/`cruzamento_sem_no`); se
    cancelado, esta função aborta SEM exceção, devolvendo
    `metadata["cancelado"] = True` com as camadas já prontas até ali
    (`osm_links_raw`/`osm_links`/`osm_nodes`; `osm_problemas` fica `None`).
    """
    _reporta_progresso(feedback, 0, "Resolvendo município")
    municipio, bbox, mun_geom = resolve_municipio(code_muni, nome_muni)
    if municipio is None:
        return {"raw_cache": None, "layers": _vazio(code_muni, nome_muni),
                "metadata": {"code_muni": str(code_muni), "nome_muni": nome_muni, "erro": "nao foi possivel resolver o municipio"}}
    _reporta_progresso(feedback, 5)

    dados = compute_osm_network(code_muni, nome_muni, bbox, mun_geom,
                                 cache_dir=cache_dir, force=force, feedback=feedback,
                                 rede=rede, incluir_pontas_soltas=incluir_pontas_soltas)

    _reporta_progresso(feedback, 90, "Montando camadas")
    layers = montar_camadas(dados)
    _reporta_progresso(feedback, 100)

    metadata = dict(dados["metadata"])
    metadata["municipio_layer"] = municipio.name()
    if layers.get("osm_links_raw") is not None:
        metadata["links_raw"] = layers["osm_links_raw"].featureCount()
    if layers.get("osm_links") is not None:
        metadata["links_clipped"] = layers["osm_links"].featureCount()
    if layers.get("osm_nodes") is not None:
        metadata["nodes"] = layers["osm_nodes"].featureCount()

    return {"raw_cache": dados["raw_cache"], "layers": layers, "metadata": metadata}


def build_osm_municipal_network(code_muni, nome_muni, gpkg_path, force=False, feedback=None,
                                 rede="veicular"):
    """Constrói as camadas de topologia OSM (links/nós/problemas) do município
    e grava no GeoPackage.

    Casca fina: monta as camadas via `build_osm_network_layers` (cache em
    `Path(os.path.dirname(gpkg_path))`, mesma pasta do GPKG — igual ao
    comportamento de antes) e grava as três no GeoPackage. **Assinatura e
    retorno inalterados** em relação à versão anterior à divisão —
    `gisbr/core/diagnostico.py` não muda, salvo o novo `rede` (default
    `"veicular"` — quem chama esta casca, motor e painel, não passa esse
    parâmetro hoje).
    """
    def log(msg):
        if feedback is not None:
            feedback.pushInfo(msg)

    cache_dir = Path(os.path.dirname(gpkg_path) or ".")
    resultado = build_osm_network_layers(code_muni, nome_muni, cache_dir=cache_dir, force=force,
                                          feedback=feedback, rede=rede)
    layers = resultado["layers"]
    metadata = dict(resultado["metadata"])

    osm_links = layers.get("osm_links")
    osm_nodes = layers.get("osm_nodes")
    osm_problemas = layers.get("osm_problemas")
    if osm_links is None or osm_nodes is None or osm_problemas is None:
        # erro / sem_vias / cancelado: nada (ou camadas incompletas) para
        # gravar — devolve tal como veio do núcleo, sem `gpkg_ok`.
        return {"raw_cache": resultado["raw_cache"], "layers": layers, "metadata": metadata}

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

    metadata["gpkg_ok"] = ok_links and ok_nodes and ok_problemas
    return {"raw_cache": resultado["raw_cache"], "layers": layers, "metadata": metadata}
