# -*- coding: utf-8 -*-
"""Montagem de rede de linhas a partir de geometrias vetoriais (stdlib pura).

Reconstrói a topologia (nós e arcos conectados) de redes lineares
(rodoviárias e ferroviárias) que não possuem IDs de nós compartilhados nativos,
trabalhando em coordenadas SIRGAS 2000 (EPSG:4674, graus lon/lat) com
aproximação equiretangular local para distâncias e tolerâncias métricas.

Este módulo NÃO importa nada de `qgis`/`PyQt` (mesma disciplina de
`osm_topologia.py`). A borda QGIS (camadas, atributos, recorte) fica em
`rede_pipeline.py`.
"""

import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# Tolerâncias do D10 em metros
TOL_NO_M: float = 1.0
TOL_SNAP_M: float = 10.0

# Raio médio da Terra em metros (WGS84 / SIRGAS 2000)
_RAIO_TERRA_M: float = 6371000.0


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Distância haversine em metros entre (lon1, lat1) e (lon2, lat2) em graus."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return _RAIO_TERRA_M * c


def _comprimento_linha_m(coords: Sequence[Tuple[float, float]]) -> float:
    """Comprimento haversine acumulado de uma sequência de coordenadas em metros."""
    total = 0.0
    for i in range(len(coords) - 1):
        total += _haversine_m(coords[i][0], coords[i][1],
                              coords[i + 1][0], coords[i + 1][1])
    return total


def _lonlat_para_xy(lon: float, lat: float, lon0: float, lat0: float) -> Tuple[float, float]:
    """Projeção equiretangular local centrada em (lon0, lat0), retornando (x, y) em metros."""
    phi0 = math.radians(lat0)
    x = math.radians(lon - lon0) * _RAIO_TERRA_M * math.cos(phi0)
    y = math.radians(lat - lat0) * _RAIO_TERRA_M
    return x, y


def _xy_para_lonlat(x: float, y: float, lon0: float, lat0: float) -> Tuple[float, float]:
    """Converte (x, y) em metros para (lon, lat) em graus a partir do centro (lon0, lat0)."""
    phi0 = math.radians(lat0)
    cos_phi0 = max(math.cos(phi0), 1e-6)
    lon = lon0 + math.degrees(x / (_RAIO_TERRA_M * cos_phi0))
    lat = lat0 + math.degrees(y / _RAIO_TERRA_M)
    return lon, lat


def _quebra_linha_em_snaps(
    coords: List[Tuple[float, float]],
    from_node: int,
    to_node: int,
    snaps: List[Dict[str, Any]],
    linha_fid: Any,
    attrs: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Quebra uma linha em sub-linhas nos pontos de snap ordenados por (seg_idx, t)."""
    if not snaps:
        return [{
            "fid": linha_fid,
            "attrs": attrs.copy(),
            "from_node": from_node,
            "to_node": to_node,
            "coords": coords,
        }]

    # Funde snaps muito próximos entre si (< TOL_NO_M) ao longo da linha
    snaps_filtrados: List[Dict[str, Any]] = []
    for s in snaps:
        if snaps_filtrados:
            ult = snaps_filtrados[-1]
            d = _haversine_m(s["coords"][0], s["coords"][1],
                             ult["coords"][0], ult["coords"][1])
            if d <= TOL_NO_M:
                # Reutiliza nó do snap anterior
                s["node_id"] = ult["node_id"]
                s["coords"] = ult["coords"]
                continue
        snaps_filtrados.append(s)

    sub_linhas: List[Dict[str, Any]] = []
    curr_node = from_node
    curr_pts = [coords[0]]
    curr_v_idx = 0

    for snap in snaps_filtrados:
        seg_idx = snap["seg_idx"]
        while curr_v_idx < seg_idx:
            curr_v_idx += 1
            curr_pts.append(coords[curr_v_idx])

        curr_pts.append(snap["coords"])

        pts_limpos: List[Tuple[float, float]] = []
        for p in curr_pts:
            if not pts_limpos or p != pts_limpos[-1]:
                pts_limpos.append(p)

        sub_linhas.append({
            "fid": linha_fid,
            "attrs": attrs.copy(),
            "from_node": curr_node,
            "to_node": snap["node_id"],
            "coords": pts_limpos,
        })

        curr_node = snap["node_id"]
        curr_pts = [snap["coords"]]

    while curr_v_idx < len(coords) - 1:
        curr_v_idx += 1
        curr_pts.append(coords[curr_v_idx])

    pts_limpos = []
    for p in curr_pts:
        if not pts_limpos or p != pts_limpos[-1]:
            pts_limpos.append(p)

    sub_linhas.append({
        "fid": linha_fid,
        "attrs": attrs.copy(),
        "from_node": curr_node,
        "to_node": to_node,
        "coords": pts_limpos,
    })

    return sub_linhas


def monta_rede(
    linhas: Sequence[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[int, Tuple[float, float]], List[Dict[str, Any]], Dict[str, int]]:
    """Reconstrói a topologia de rede linear a partir de geometrias de linhas.

    Segue as etapas 1 a 6 do D10:
    1. Geometria inválida/degenerada: descarta partes com < 2 pontos distintos
       ou comprimento zero (correção `geometria_degenerada`). Vértices repetidos
       consecutivos são removidos.
    2. Explodir multipartes: cada parte vira uma linha que herda os `attrs`.
    3. Nós por coincidência: pontas a até TOL_NO_M (1.0 m) viram o mesmo nó
       (correção `ponta_unificada` quando não idênticas).
    4. Junção em T: ponta a até TOL_SNAP_M (10.0 m) do interior de outra linha
       (e longe de nó existente) quebra a linha alvo no pé da perpendicular
       (correção `ponta_conectada`).
    5. Arcos: cada linha é quebrada nos seus nós no formato do `osm_topologia`.
    6. Coincidentes: arcos com o mesmo par não ordenado de nós e comprimento
       igual dentro de max(1 m, 1%) colapsam em um só (correção `coincidente_colapsado`).

    Retorna:
        (arcos, nos, correcoes, contagens)
    """
    correcoes: List[Dict[str, Any]] = []
    contagens: Dict[str, int] = {
        "geometria_degenerada": 0,
        "multipartes_explodidas": 0,
        "ponta_unificada": 0,
        "ponta_conectada": 0,
        "coincidente_colapsado": 0,
        "arcos": 0,
        "nos": 0,
    }

    # -------------------------------------------------------------------------
    # Etapas 1 e 2: Validação geométrica e explosão de multipartes
    # -------------------------------------------------------------------------
    linhas_explodidas: List[Dict[str, Any]] = []

    for linha in linhas:
        fid = linha.get("fid")
        attrs = dict(linha.get("attrs") or {})
        partes = linha.get("partes")
        if partes is None:
            c = linha.get("coords")
            partes = [c] if c else []

        partes_validas: List[List[Tuple[float, float]]] = []
        for parte in partes:
            if not parte:
                correcoes.append({
                    "tipo": "geometria_degenerada",
                    "x": 0.0,
                    "y": 0.0,
                    "detalhe": "geometria vazia",
                    "fid": fid,
                })
                contagens["geometria_degenerada"] += 1
                continue

            limpos: List[Tuple[float, float]] = []
            for pt in parte:
                coord = (float(pt[0]), float(pt[1]))
                if not limpos or coord != limpos[-1]:
                    limpos.append(coord)

            if len(limpos) < 2:
                x, y = limpos[0] if limpos else (0.0, 0.0)
                correcoes.append({
                    "tipo": "geometria_degenerada",
                    "x": x,
                    "y": y,
                    "detalhe": "menos de 2 pontos distintos",
                    "fid": fid,
                })
                contagens["geometria_degenerada"] += 1
                continue

            comp = _comprimento_linha_m(limpos)
            if comp <= 1e-6:
                correcoes.append({
                    "tipo": "geometria_degenerada",
                    "x": limpos[0][0],
                    "y": limpos[0][1],
                    "detalhe": "comprimento zero",
                    "fid": fid,
                })
                contagens["geometria_degenerada"] += 1
                continue

            partes_validas.append(limpos)

        if len(partes_validas) > 1:
            contagens["multipartes_explodidas"] += len(partes_validas)

        for p_val in partes_validas:
            linhas_explodidas.append({
                "fid": fid,
                "coords": p_val,
                "attrs": attrs.copy(),
            })

    if not linhas_explodidas:
        return [], {}, correcoes, contagens

    # -------------------------------------------------------------------------
    # Etapa 3: Nós por coincidência (TOL_NO_M = 1.0 m)
    # -------------------------------------------------------------------------
    nos: Dict[int, Tuple[float, float]] = {}
    next_node_id = 1

    tam_celula_no_m = 2.0
    grade_nos: Dict[Tuple[int, int], List[int]] = {}

    def _celula_no(lon: float, lat: float) -> Tuple[int, int]:
        m_lat = 111320.0
        m_lon = 111320.0 * max(math.cos(math.radians(lat)), 0.01)
        gx = int(math.floor(lon * m_lon / tam_celula_no_m))
        gy = int(math.floor(lat * m_lat / tam_celula_no_m))
        return gx, gy

    def _obter_ou_criar_no(ponta: Tuple[float, float], linha_fid: Any) -> int:
        nonlocal next_node_id
        cx, cy = _celula_no(ponta[0], ponta[1])
        melhor_no = None
        menor_dist = float("inf")

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for nid in grade_nos.get((cx + dx, cy + dy), []):
                    nx, ny = nos[nid]
                    d = _haversine_m(ponta[0], ponta[1], nx, ny)
                    if d <= TOL_NO_M and d < menor_dist:
                        menor_dist = d
                        melhor_no = nid

        if melhor_no is not None:
            if menor_dist > 1e-9:
                correcoes.append({
                    "tipo": "ponta_unificada",
                    "x": ponta[0],
                    "y": ponta[1],
                    "detalhe": f"distancia {menor_dist:.2f} m",
                    "fid": linha_fid,
                })
                contagens["ponta_unificada"] += 1
            return melhor_no

        novo_id = next_node_id
        next_node_id += 1
        nos[novo_id] = ponta
        grade_nos.setdefault((cx, cy), []).append(novo_id)
        return novo_id

    for item in linhas_explodidas:
        c = item["coords"]
        start_node = _obter_ou_criar_no(c[0], item["fid"])
        c[0] = nos[start_node]
        item["from_node"] = start_node

        end_node = _obter_ou_criar_no(c[-1], item["fid"])
        c[-1] = nos[end_node]
        item["to_node"] = end_node

    # -------------------------------------------------------------------------
    # Etapa 4: Junção em T (TOL_SNAP_M = 10.0 m)
    # -------------------------------------------------------------------------
    # Indexa segmentos em grade espacial
    tam_celula_seg_m = 25.0
    grade_segs: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

    def _celula_seg(lon: float, lat: float) -> Tuple[int, int]:
        m_lat = 111320.0
        m_lon = 111320.0 * max(math.cos(math.radians(lat)), 0.01)
        gx = int(math.floor(lon * m_lon / tam_celula_seg_m))
        gy = int(math.floor(lat * m_lat / tam_celula_seg_m))
        return gx, gy

    for l_idx, item in enumerate(linhas_explodidas):
        c = item["coords"]
        for s_idx in range(len(c) - 1):
            p1, p2 = c[s_idx], c[s_idx + 1]
            # Percorre o segmento em passos de no máximo meia célula (metros);
            # o custo é proporcional ao comprimento, não à área da bbox.
            comp_m = _haversine_m(p1[0], p1[1], p2[0], p2[1])
            n_passos = max(1, int(math.ceil(comp_m / (tam_celula_seg_m / 2.0))))

            # Célula de cada amostra + vizinhas (anel ±1 cobre TOL_SNAP_M < célula)
            celulas_seg: Set[Tuple[int, int]] = set()
            for i in range(n_passos + 1):
                f = i / n_passos
                lon = p1[0] + (p2[0] - p1[0]) * f
                lat = p1[1] + (p2[1] - p1[1]) * f
                gx, gy = _celula_seg(lon, lat)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        celulas_seg.add((gx + dx, gy + dy))

            for cel in celulas_seg:
                grade_segs.setdefault(cel, []).append((l_idx, s_idx))

    # Identifica snaps para cada ponta de cada linha
    snaps_por_linha: Dict[int, List[Dict[str, Any]]] = {}

    for l_idx, item in enumerate(linhas_explodidas):
        c = item["coords"]
        pontas = [
            (c[0], True, item["from_node"]),
            (c[-1], False, item["to_node"]),
        ]

        for p_coord, is_start, p_node in pontas:
            px, py = p_coord
            cgx, cgy = _celula_seg(px, py)

            candidatos_vistos = set()
            melhor_snap = None
            menor_dist_snap = float("inf")

            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for cand in grade_segs.get((cgx + dx, cgy + dy), []):
                        if cand in candidatos_vistos:
                            continue
                        candidatos_vistos.add(cand)

                        alvo_l_idx, alvo_s_idx = cand
                        if alvo_l_idx == l_idx:
                            # Não conecta na própria linha
                            continue

                        alvo_c = linhas_explodidas[alvo_l_idx]["coords"]
                        a_coord = alvo_c[alvo_s_idx]
                        b_coord = alvo_c[alvo_s_idx + 1]

                        # Projeção equiretangular local centrada na ponta P
                        ax, ay = _lonlat_para_xy(a_coord[0], a_coord[1], px, py)
                        bx, by = _lonlat_para_xy(b_coord[0], b_coord[1], px, py)

                        vx, vy = bx - ax, by - ay
                        l2 = vx * vx + vy * vy
                        if l2 < 1e-12:
                            continue

                        comp_seg = math.sqrt(l2)
                        # P na origem (0, 0), vetor W = P - A = (-ax, -ay)
                        t = (-ax * vx - ay * vy) / l2

                        if t <= 0.0 or t >= 1.0:
                            # Fora do interior do segmento
                            continue

                        # Distância ao longo do segmento até os vértices A e B
                        dist_a = t * comp_seg
                        dist_b = (1.0 - t) * comp_seg
                        if dist_a <= TOL_NO_M or dist_b <= TOL_NO_M:
                            # Próximo demais dos nós das pontas do segmento
                            continue

                        # Pé da perpendicular F
                        fx = ax + t * vx
                        fy = ay + t * vy
                        dist_perp = math.sqrt(fx * fx + fy * fy)

                        if dist_perp > TOL_SNAP_M:
                            continue

                        f_lon, f_lat = _xy_para_lonlat(fx, fy, px, py)

                        # Verifica se F está longe de nós existentes da linha alvo
                        nos_alvo = (
                            linhas_explodidas[alvo_l_idx]["from_node"],
                            linhas_explodidas[alvo_l_idx]["to_node"],
                        )
                        perto_no_alvo = False
                        for nid in nos_alvo:
                            if nid in nos:
                                if _haversine_m(f_lon, f_lat, nos[nid][0], nos[nid][1]) <= TOL_NO_M:
                                    perto_no_alvo = True
                                    break
                        if perto_no_alvo:
                            continue

                        if dist_perp < menor_dist_snap:
                            menor_dist_snap = dist_perp
                            melhor_snap = {
                                "alvo_line_idx": alvo_l_idx,
                                "ponta_line_idx": l_idx,
                                "is_start": is_start,
                                "seg_idx": alvo_s_idx,
                                "t": t,
                                "coords": (f_lon, f_lat),
                                "distancia_m": dist_perp,
                                "fid": item["fid"],
                            }

            if melhor_snap is not None:
                snaps_por_linha.setdefault(melhor_snap["alvo_line_idx"], []).append(melhor_snap)

    # Aplica as quebras nas linhas alvo e conecta as pontas
    novas_linhas: List[Dict[str, Any]] = []

    for l_idx, item in enumerate(linhas_explodidas):
        snaps = snaps_por_linha.get(l_idx)
        if not snaps:
            novas_linhas.append(item)
            continue

        # Ordena snaps por (seg_idx, t)
        snaps.sort(key=lambda s: (s["seg_idx"], s["t"]))

        for s in snaps:
            # Cria nó para o pé da perpendicular
            f_coord = s["coords"]
            novo_id = next_node_id
            next_node_id += 1
            nos[novo_id] = f_coord
            s["node_id"] = novo_id

            # Conecta a ponta da linha incidente ao novo nó
            p_line = linhas_explodidas[s["ponta_line_idx"]]
            if s["is_start"]:
                p_line["coords"][0] = f_coord
                p_line["from_node"] = novo_id
            else:
                p_line["coords"][-1] = f_coord
                p_line["to_node"] = novo_id

            correcoes.append({
                "tipo": "ponta_conectada",
                "x": f_coord[0],
                "y": f_coord[1],
                "detalhe": f"distancia {s['distancia_m']:.2f} m",
                "fid": s["fid"],
            })
            contagens["ponta_conectada"] += 1

        # Quebra a linha alvo nos pontos de snap
        sub_partes = _quebra_linha_em_snaps(
            item["coords"],
            item["from_node"],
            item["to_node"],
            snaps,
            item["fid"],
            item["attrs"],
        )
        novas_linhas.extend(sub_partes)

    # -------------------------------------------------------------------------
    # Etapa 5: Construção dos arcos
    # -------------------------------------------------------------------------
    todos_arcos: List[Dict[str, Any]] = []
    for l in novas_linhas:
        c = l["coords"]
        if len(c) < 2:
            continue
        comp = _comprimento_linha_m(c)
        todos_arcos.append({
            "from_node": l["from_node"],
            "to_node": l["to_node"],
            "coords": c,
            "fid": l["fid"],
            "comprimento_m": comp,
            "oneway": "",
            "junction": "",
            "highway": "",
            "bridge": "",
            "tunnel": "",
            "layer": "",
            "veicular": True,
            "pedestre": False,
            "coincidentes": "",
            "attrs": l["attrs"],
        })

    # -------------------------------------------------------------------------
    # Etapa 6: Coincidentes (mesmo par não ordenado de nós e comprimento similar)
    # -------------------------------------------------------------------------
    grupos_por_par: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for arco in todos_arcos:
        par = tuple(sorted([arco["from_node"], arco["to_node"]]))
        grupos_por_par.setdefault(par, []).append(arco)

    arcos_mantidos: List[Dict[str, Any]] = []

    for par, grupo in grupos_por_par.items():
        if len(grupo) == 1:
            arcos_mantidos.append(grupo[0])
            continue

        representantes: List[Dict[str, Any]] = []
        fids_colapsados: Dict[int, List[Any]] = {}

        for a in grupo:
            comp_a = a["comprimento_m"]
            casou = False
            for idx_rep, rep in enumerate(representantes):
                comp_rep = rep["comprimento_m"]
                tol = max(1.0, 0.01 * max(comp_a, comp_rep))
                if abs(comp_a - comp_rep) <= tol:
                    fids_colapsados[idx_rep].append(a["fid"])
                    casou = True
                    break
            if not casou:
                idx_rep = len(representantes)
                representantes.append(a)
                fids_colapsados[idx_rep] = [a["fid"]]

        for idx_rep, rep in enumerate(representantes):
            fids = fids_colapsados[idx_rep]
            if len(fids) > 1:
                coinc_str = ";".join(str(f) for f in fids)
                rep["coincidentes"] = coinc_str
                correcoes.append({
                    "tipo": "coincidente_colapsado",
                    "x": rep["coords"][0][0],
                    "y": rep["coords"][0][1],
                    "detalhe": f"fids {coinc_str}",
                    "fid": rep["fid"],
                })
                contagens["coincidente_colapsado"] += len(fids) - 1
            arcos_mantidos.append(rep)

    # Numeração contínua de arc_id
    for idx, arco in enumerate(arcos_mantidos, start=1):
        arco["arc_id"] = idx

    # Coleta os nós ativos que realmente participam dos arcos mantidos
    nos_ativos: Dict[int, Tuple[float, float]] = {}
    for arco in arcos_mantidos:
        fn = arco["from_node"]
        tn = arco["to_node"]
        if fn in nos:
            nos_ativos[fn] = nos[fn]
        if tn in nos:
            nos_ativos[tn] = nos[tn]

    contagens["arcos"] = len(arcos_mantidos)
    contagens["nos"] = len(nos_ativos)

    return arcos_mantidos, nos_ativos, correcoes, contagens


def filtra_existentes(
    feicoes: Sequence[Dict[str, Any]],
    excluir: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separa feições mantidas e removidas pelo critério de existência (D12).

    Compara ``str(v).strip()`` do atributo indicado em ``excluir['campo']``
    com os valores em ``excluir['valores']`` por igualdade exata.

    Regras:
    - Se ``excluir`` for ``None`` ou vazio, todas as feições são mantidas.
    - Se o campo não existir na feição, ela é mantida.
    - Se o valor do campo for nulo (``None``), ela é mantida.
    - Suporta feições onde os atributos são o próprio dict ou estão sob a chave ``"attrs"``.

    Retorna:
        Tuple[mantidas, removidas]
    """
    if not excluir:
        return list(feicoes), []

    campo = excluir.get("campo")
    if not campo:
        return list(feicoes), []

    valores_raw = excluir.get("valores") or []
    if isinstance(valores_raw, str):
        valores_raw = [valores_raw]
    valores_excluir = {str(val).strip() for val in valores_raw}
    if not valores_excluir:
        return list(feicoes), []

    mantidas: List[Dict[str, Any]] = []
    removidas: List[Dict[str, Any]] = []

    for f in feicoes:
        attrs = f.get("attrs") if (isinstance(f, dict) and "attrs" in f and isinstance(f["attrs"], dict)) else f
        if not isinstance(attrs, dict) or campo not in attrs:
            mantidas.append(f)
            continue

        val = attrs[campo]
        if val is None:
            mantidas.append(f)
            continue

        val_str = str(val).strip()
        if val_str in valores_excluir:
            removidas.append(f)
        else:
            mantidas.append(f)

    return mantidas, removidas
