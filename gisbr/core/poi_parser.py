# -*- coding: utf-8 -*-
"""Parser de POIs do OpenStreetMap no predicado do osm2gmns (stdlib pura).

Este módulo NÃO importa nada do QGIS/Qt (decisão D7 da Rodada 10): conjuntos
de tags, montagem da query Overpass QL, classificação e parse do JSON são
lógica pura, testável sem QGIS instalado.

Os conjuntos de tags e a ordem das colunas do CSV são cópias verbatim do
osm2gmns (https://github.com/xyluo25/osm2gmns):

- `osmnet/wayfilters.py:9-11` — HIGHWAY_POI_SET, RAILWAY_POI_SET, AEROWAY_POI_SET
- `io/writefile.py:122` — POI_CSV_COLUNAS (cabeçalho do poi.csv)

Copiar o predicado é o que torna a saída drop-in para o grid2demand, que lê o
`poi.csv` produzido pelo osm2gmns (decisão D2 da Rodada 10).
"""

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Copiado verbatim de osm2gmns/osmnet/wayfilters.py:9-11
HIGHWAY_POI_SET = {"bus_stop", "platform"}
RAILWAY_POI_SET = {"depot", "station", "workshop", "halt", "interlocking",
                   "junction", "spur_junction", "terminal", "platform"}
AEROWAY_POI_SET = set()

# Fator de conversão m² -> ft² literal do upstream (io/writefile.py:130)
AREA_M2_TO_FT2 = 10.7639

# Ordem das colunas do poi.csv (osm2gmns/io/writefile.py:122)
POI_CSV_COLUNAS = ("name", "poi_id", "osm_way_id", "osm_relation_id",
                   "building", "amenity", "way", "geometry", "centroid",
                   "area", "area_ft2")


def linha_poi_csv(attrs, geometry_wkt):
    """Monta a linha do poi.csv a partir dos atributos da feição (função pura).

    `attrs` é um dict chaveado pelo nome do campo da camada osm_pois_*;
    `geometry_wkt` é o WKT da geometria da feição. `osm_way_id`/
    `osm_relation_id` derivam de `osm_type`/`osm_id` (vazio quando não se
    aplica, como no upstream); `area`/`area_ft2` saem com 1 casa decimal
    (igual a writefile.py:130).
    """
    osm_type = str(attrs.get("osm_type") or "")
    osm_id = attrs.get("osm_id")
    osm_id = "" if osm_id is None else str(osm_id)
    area = attrs.get("area")
    area = 0.0 if area is None else float(area)
    area_ft2 = attrs.get("area_ft2")
    area_ft2 = 0.0 if area_ft2 is None else float(area_ft2)
    centroid = ""
    if attrs.get("centroid_lon") is not None and attrs.get("centroid_lat") is not None:
        centroid = "POINT ({:.7f} {:.7f})".format(
            float(attrs["centroid_lon"]), float(attrs["centroid_lat"]))
    return {
        "name": attrs.get("name") or "",
        "poi_id": attrs.get("poi_id") if attrs.get("poi_id") is not None else "",
        "osm_way_id": osm_id if osm_type == "way" else "",
        "osm_relation_id": osm_id if osm_type == "relation" else "",
        "building": attrs.get("building") or "",
        "amenity": attrs.get("amenity") or "",
        "way": attrs.get("way") or "",
        "geometry": geometry_wkt,
        "centroid": centroid,
        "area": round(area, 1),
        "area_ft2": round(area_ft2, 1),
    }

# Regex na mesma ordem do upstream para a query ficar determinística
_RAILWAY_POI_REGEX = "depot|station|workshop|halt|interlocking|junction|spur_junction|terminal|platform"
_HIGHWAY_POI_REGEX = "bus_stop|platform"


def classifica_way(tags: Optional[Dict[str, Any]]) -> str:
    """Valor da coluna `way`: `highway`/`railway` do conjunto POI, senão "".

    Espelha o osmnet/build_net.py:239/286/311 — a tag de via que classifica o
    elemento como POI vai para a coluna `way` (aeroway_poi_set é vazio no
    upstream e continua vazio aqui).
    """
    if not isinstance(tags, dict):
        return ""
    if tags.get("highway") in HIGHWAY_POI_SET:
        return tags["highway"]
    if tags.get("railway") in RAILWAY_POI_SET:
        return tags["railway"]
    return ""


def is_poi(tags: Optional[Dict[str, Any]]) -> bool:
    """Predicado de POI do osm2gmns (D2): tag `building` OU `amenity`, mais
    `highway`/`railway` nos conjuntos POI."""
    if not isinstance(tags, dict):
        return False
    if tags.get("building") or tags.get("amenity"):
        return True
    return classifica_way(tags) != ""


def poi_type(tags: Optional[Dict[str, Any]]) -> str:
    """Chave prática de classificação (D8): `amenity`, senão `building`,
    senão o valor da coluna `way`."""
    if not isinstance(tags, dict):
        return ""
    if tags.get("amenity"):
        return tags["amenity"]
    if tags.get("building"):
        return tags["building"]
    return classifica_way(tags)


def build_poi_query(bbox: Sequence[float], timeout: int = 180) -> str:
    """Monta a query Overpass QL de POIs (predicado D2) para uma bbox.

    `bbox` é (minx, miny, maxx, maxy) em EPSG:4674/WGS84; o Overpass espera
    (sul, oeste, norte, leste). `out geom` (e não `out body;>;`) devolve as
    coordenadas inline, sem baixar o dicionário de nós à parte.
    """
    minx, miny, maxx, maxy = bbox
    bbox_str = "{},{},{},{}".format(miny, minx, maxy, maxx)
    return (
        "[out:json][timeout:{t}];"
        "("
        'nwr["building"]({b});'
        'nwr["amenity"]({b});'
        'nwr["highway"~"^({h})$"]({b});'
        'nwr["railway"~"^({r})$"]({b});'
        ");"
        "out geom;"
    ).format(t=int(timeout), b=bbox_str, h=_HIGHWAY_POI_REGEX, r=_RAILWAY_POI_REGEX)


def _anel_fechado(geometry: Sequence[Dict[str, float]]) -> List[Tuple[float, float]]:
    """Converte a geometria `out geom` de um way em anel [(lon, lat), ...].

    Devolve [] se o way não for fechado (primeiro ponto != último).
    """
    anel = [(p["lon"], p["lat"]) for p in geometry]
    if len(anel) < 4 or anel[0] != anel[-1]:
        return []
    return anel


def _registros_brutos(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Percorre `elements` e devolve (registros, descartadas).

    Regras (Rodada 10, passos 1–2):
    - node com POI → sem anéis, lon/lat do próprio elemento (D3);
    - way com geometry fechada → um anel; way aberto → descartado
      (`way_aberto`);
    - relation → anéis dos membros `role == "outer"` que JÁ vêm fechados
      (D5); sem nenhum anel fechado → descartada
      (`relacao_sem_anel_fechado`).
    """
    registros: List[Dict[str, Any]] = []
    descartadas: Dict[str, int] = {"way_aberto": 0, "relacao_sem_anel_fechado": 0}

    for el in payload.get("elements", []):
        if not isinstance(el, dict):
            continue
        tags = el.get("tags") or {}
        if not is_poi(tags):
            continue

        tipo = el.get("type")
        base = {
            "osm_type": tipo,
            "osm_id": el.get("id"),
            "name": str(tags.get("name", "") or ""),
            "building": str(tags.get("building", "") or ""),
            "amenity": str(tags.get("amenity", "") or ""),
            "way": classifica_way(tags),
            "poi_type": poi_type(tags),
        }

        if tipo == "node":
            base["aneis"] = []
            base["lon"] = el.get("lon")
            base["lat"] = el.get("lat")
            if base["lon"] is None or base["lat"] is None:
                continue
            registros.append(base)
        elif tipo == "way":
            anel = _anel_fechado(el.get("geometry") or [])
            if not anel:
                descartadas["way_aberto"] += 1
                continue
            base["aneis"] = [anel]
            base["lon"] = None
            base["lat"] = None
            registros.append(base)
        elif tipo == "relation":
            aneis = []
            for membro in el.get("members", []):
                if not isinstance(membro, dict) or membro.get("role") != "outer":
                    continue
                anel = _anel_fechado(membro.get("geometry") or [])
                if anel:
                    aneis.append(anel)
            if not aneis:
                descartadas["relacao_sem_anel_fechado"] += 1
                continue
            base["aneis"] = aneis
            base["lon"] = None
            base["lat"] = None
            registros.append(base)

    return registros, descartadas


def parse_pois(payload) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Parseia a resposta Overpass em (registros, descartadas).

    Cada registro é um dict com `osm_type, osm_id, name, building, amenity,
    way, poi_type, aneis, lon, lat` (+ `poi_id`, atribuído aqui). `poi_id` é
    sequencial e estável: os registros são ordenados por `(osm_type, osm_id)`
    antes de numerar, então duas rodadas com o mesmo payload dão o mesmo id.
    `descartadas` é um dict de contagem por motivo — nunca descarte mudo.
    """
    if isinstance(payload, (str, bytes)):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        return [], {"way_aberto": 0, "relacao_sem_anel_fechado": 0}

    registros, descartadas = _registros_brutos(payload)
    registros.sort(key=lambda r: (r["osm_type"], r["osm_id"]))
    for i, registro in enumerate(registros, start=1):
        registro["poi_id"] = i
    return registros, descartadas
