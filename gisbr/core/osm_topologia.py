# -*- coding: utf-8 -*-
"""Topologia de rede viária OSM (stdlib pura, sem QGIS).

A topologia "verdadeira" do OSM não é 1 way = 1 link: dois ways estão
conectados sse compartilham um `node_id`. Ruas que se encontram no MEIO de
outro way (mesmo `node_id`) ficam sem ligação se o link for gerado só pelas
pontas geométricas do way — este módulo quebra cada way nos pontos onde há
de fato um `node_id` compartilhado (ou nas próprias pontas), produzindo
"arcos" (segmentos de via) com a topologia real.

Este módulo NÃO importa nada de `qgis`/`PyQt` (mesma disciplina de
`poi_parser.py`, D7 da Rodada 10): é lógica pura, testável sem QGIS
instalado. A borda QGIS (camadas, geometria, recorte) fica em
`osm_pipeline.py`.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

# oneway -> sentido explícito
_ONEWAY_DIRETO = {"yes", "true", "1"}
_ONEWAY_INVERSO = {"-1", "reverse"}
_ONEWAY_AMBOS = {"no", "false", "0"}

# junction que implica sentido único quando oneway está ausente/vazio
_JUNCTION_ONEWAY_IMPLICITA = {"roundabout", "circular"}


def constroi_arcos(ways: Sequence[Dict[str, Any]],
                    nodes_dict: Dict[int, Tuple[float, float]]
                    ) -> Tuple[List[Dict[str, Any]], int]:
    """Quebra cada way OSM em arcos pela topologia real (node_id compartilhado).

    `ways`: lista de dicts do Overpass (`id`, `nodes`, `tags`).
    `nodes_dict`: `{node_id: (lon, lat)}`.

    Refs de nó ausentes em `nodes_dict` são descartadas e CONTADAS
    (`n_orfaos`) — nunca descarte mudo. Ponto de quebra de um way = seu
    primeiro/último nó OU qualquer nó cuja contagem de aparições em TODOS os
    ways (após descartar órfãos) seja >= 2. Arco com < 2 nós é descartado.

    Devolve `(arcos, n_orfaos)`; cada arco é um dict com `arc_id` (inteiro
    sequencial a partir de 1), `way_id`, `seq` (ordem dentro do way, 0..),
    `from_node`, `to_node`, `nodes` (lista de node_ids), `coords` (lista de
    (lon, lat)), `highway`, `name`, `oneway`, `junction`, `bridge`, `tunnel`,
    `layer` (strings, "" se ausente).
    """
    n_orfaos = 0
    ways_filtrados = []  # [(way, [node_id, ...])]
    contagem: Dict[int, int] = {}

    for way in ways:
        nos_brutos = way.get("nodes") or []
        nos = []
        for node_id in nos_brutos:
            if node_id in nodes_dict:
                nos.append(node_id)
            else:
                n_orfaos += 1
        ways_filtrados.append((way, nos))
        for node_id in nos:
            contagem[node_id] = contagem.get(node_id, 0) + 1

    arcos: List[Dict[str, Any]] = []
    arc_id = 1
    for way, nos in ways_filtrados:
        if len(nos) < 2:
            continue

        pontos_quebra = {0, len(nos) - 1}
        for i, node_id in enumerate(nos):
            if contagem.get(node_id, 0) >= 2:
                pontos_quebra.add(i)
        pontos_quebra_ordenados = sorted(pontos_quebra)

        tags = way.get("tags") or {}
        way_id = way.get("id")

        seq = 0
        for idx in range(len(pontos_quebra_ordenados) - 1):
            i0 = pontos_quebra_ordenados[idx]
            i1 = pontos_quebra_ordenados[idx + 1]
            segmento = nos[i0:i1 + 1]
            if len(segmento) < 2:
                continue
            arcos.append({
                "arc_id": arc_id,
                "way_id": way_id,
                "seq": seq,
                "from_node": segmento[0],
                "to_node": segmento[-1],
                "nodes": segmento,
                "coords": [nodes_dict[n] for n in segmento],
                "highway": str(tags.get("highway") or ""),
                "name": str(tags.get("name") or ""),
                "oneway": str(tags.get("oneway") or ""),
                "junction": str(tags.get("junction") or ""),
                "bridge": str(tags.get("bridge") or ""),
                "tunnel": str(tags.get("tunnel") or ""),
                "layer": str(tags.get("layer") or ""),
            })
            arc_id += 1
            seq += 1

    return arcos, n_orfaos


def sentido(arco: Dict[str, Any]) -> str:
    """`"ambos" | "direto" | "inverso"` a partir de `oneway`/`junction`/`highway`."""
    oneway = (arco.get("oneway") or "").strip().lower()
    if oneway in _ONEWAY_DIRETO:
        return "direto"
    if oneway in _ONEWAY_INVERSO:
        return "inverso"
    if oneway in _ONEWAY_AMBOS:
        return "ambos"

    # ausente/vazio (ou valor não reconhecido): direto se rotatória
    # implícita ou motorway, senão ambos.
    junction = (arco.get("junction") or "").strip().lower()
    highway = (arco.get("highway") or "").strip().lower()
    if junction in _JUNCTION_ONEWAY_IMPLICITA or highway == "motorway":
        return "direto"
    return "ambos"


def grau(arcos: Sequence[Dict[str, Any]]) -> Dict[int, int]:
    """Grau não dirigido por `node_id`; laço (from == to) soma 2."""
    g: Dict[int, int] = {}
    for arco in arcos:
        f, t = arco["from_node"], arco["to_node"]
        if f == t:
            g[f] = g.get(f, 0) + 2
        else:
            g[f] = g.get(f, 0) + 1
            g[t] = g.get(t, 0) + 1
    return g


def componentes(arcos: Sequence[Dict[str, Any]]
                ) -> Tuple[Dict[int, int], Dict[int, int]]:
    """Componentes conexas não dirigidas (union-find).

    Devolve `(node_comp, comp_tam)`; `comp_tam[c]` é o número de ARCOS da
    componente `c`. Ids renumerados por tamanho decrescente (0 = maior
    componente); desempate estável pelo menor `node_id` da componente.
    """
    parent: Dict[int, int] = {}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for arco in arcos:
        f, t = arco["from_node"], arco["to_node"]
        if f not in parent:
            parent[f] = f
        if t not in parent:
            parent[t] = t
        union(f, t)

    arcos_por_raiz: Dict[int, int] = {}
    for arco in arcos:
        raiz = find(arco["from_node"])
        arcos_por_raiz[raiz] = arcos_por_raiz.get(raiz, 0) + 1

    nos_por_raiz: Dict[int, List[int]] = {}
    for node_id in parent:
        nos_por_raiz.setdefault(find(node_id), []).append(node_id)

    def chave_ordenacao(raiz: int):
        return (-arcos_por_raiz.get(raiz, 0), min(nos_por_raiz[raiz]))

    raizes_ordenadas = sorted(arcos_por_raiz.keys(), key=chave_ordenacao)
    comp_id_por_raiz = {raiz: i for i, raiz in enumerate(raizes_ordenadas)}

    node_comp = {node_id: comp_id_por_raiz[find(node_id)] for node_id in parent}
    comp_tam = {comp_id_por_raiz[raiz]: tam for raiz, tam in arcos_por_raiz.items()}

    return node_comp, comp_tam


def componentes_fortes(arcos: Sequence[Dict[str, Any]]) -> Dict[int, int]:
    """SCC (Tarjan ITERATIVO) do grafo dirigido por `sentido(arco)`.

    Sem recursão — redes municipais estouram o limite de recursão do Python.
    scc 0 = maior componente fortemente conexa (desempate estável pelo menor
    `node_id`).
    """
    adj: Dict[int, List[int]] = {}
    nos: List[int] = []
    vistos_nos = set()

    for arco in arcos:
        f, t = arco["from_node"], arco["to_node"]
        for n in (f, t):
            if n not in vistos_nos:
                vistos_nos.add(n)
                nos.append(n)
                adj.setdefault(n, [])
        s = sentido(arco)
        if s == "direto":
            adj[f].append(t)
        elif s == "inverso":
            adj[t].append(f)
        else:  # ambos
            adj[f].append(t)
            adj[t].append(f)

    index_atual = 0
    index: Dict[int, int] = {}
    lowlink: Dict[int, int] = {}
    on_stack: Dict[int, bool] = {}
    pilha_tarjan: List[int] = []
    sccs: List[List[int]] = []

    for inicio in nos:
        if inicio in index:
            continue

        index[inicio] = index_atual
        lowlink[inicio] = index_atual
        index_atual += 1
        pilha_tarjan.append(inicio)
        on_stack[inicio] = True
        pilha_chamadas = [(inicio, iter(adj.get(inicio, ())))]

        while pilha_chamadas:
            v, vizinhos = pilha_chamadas[-1]
            avancou = False
            for w in vizinhos:
                if w not in index:
                    index[w] = index_atual
                    lowlink[w] = index_atual
                    index_atual += 1
                    pilha_tarjan.append(w)
                    on_stack[w] = True
                    pilha_chamadas.append((w, iter(adj.get(w, ()))))
                    avancou = True
                    break
                elif on_stack.get(w):
                    lowlink[v] = min(lowlink[v], index[w])
            if avancou:
                continue

            pilha_chamadas.pop()
            if pilha_chamadas:
                pai = pilha_chamadas[-1][0]
                lowlink[pai] = min(lowlink[pai], lowlink[v])

            if lowlink[v] == index[v]:
                comp = []
                while True:
                    w = pilha_tarjan.pop()
                    on_stack[w] = False
                    comp.append(w)
                    if w == v:
                        break
                sccs.append(comp)

    sccs_ordenadas = sorted(sccs, key=lambda comp: (-len(comp), min(comp)))
    node_scc: Dict[int, int] = {}
    for scc_id, comp in enumerate(sccs_ordenadas):
        for n in comp:
            node_scc[n] = scc_id
    return node_scc


def diagnostica(arcos: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Consolida grau/componentes/SCC em diagnóstico da rede.

    Devolve dict com `grau`, `node_comp`, `comp_tam`, `scc`, e as listas
    `pontas_soltas` (nós de grau 1), `mao_unica_sem_saida` (nós da
    componente fraca 0 que NÃO estão na SCC 0) e `ilhas` (lista de
    `(comp_id, n_arcos, node_id_representante)` para comp_id != 0,
    representante = menor node_id da componente).
    """
    g = grau(arcos)
    node_comp, comp_tam = componentes(arcos)
    scc = componentes_fortes(arcos)

    pontas_soltas = [n for n, d in g.items() if d == 1]

    mao_unica_sem_saida = [
        n for n, c in node_comp.items() if c == 0 and scc.get(n) != 0
    ]

    nos_por_comp: Dict[int, List[int]] = {}
    for node_id, comp_id in node_comp.items():
        nos_por_comp.setdefault(comp_id, []).append(node_id)

    ilhas = []
    for comp_id, tam in comp_tam.items():
        if comp_id == 0:
            continue
        representante = min(nos_por_comp.get(comp_id, [comp_id]))
        ilhas.append((comp_id, tam, representante))
    ilhas.sort(key=lambda item: item[0])

    return {
        "grau": g,
        "node_comp": node_comp,
        "comp_tam": comp_tam,
        "scc": scc,
        "pontas_soltas": pontas_soltas,
        "mao_unica_sem_saida": mao_unica_sem_saida,
        "ilhas": ilhas,
    }
