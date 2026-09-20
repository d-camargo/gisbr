# -*- coding: utf-8 -*-
"""Pipeline Agropecuário: Tabela IBGE (Agregados/PAM/Censo) × Malha Municipal → Camada Espacial (D5).

Converte dados tabulares de agregados agropecuários em camada vetorial em formato largo (1 feição por município,
1 campo por variável × produto). Produtos sem valor numérico em nenhuma variável são descartados (D5).
Nomes de campos são normalizados (unicodedata, minúsculas), truncados ao limite do GeoPackage (63 caracteres),
com desempate determinístico em caso de colisão.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple, Union

from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsVectorLayer,
    QgsWkbTypes,
)

from .osm_pipeline import _municipio_poligono
from .qgis_compat import field_type

MAX_GEOPACKAGE_FIELD_LEN = 63


def _invalid_layer(layer_name: str, msg: str) -> QgsVectorLayer:
    """Cria uma QgsVectorLayer inválida com a mensagem de erro fornecida."""
    inv = QgsVectorLayer("", layer_name, "memory")
    inv.error_msg = msg
    return inv


def _parse_val(raw_val: Any) -> Optional[Union[int, float]]:
    """Converte valor bruto para numérico (int/float) ou None se for nulo/código especial.

    Regra D4/D15: '-', '..', '...', 'X', 'x', '', 'None', 'NULL' -> None (JAMAIS 0).
    """
    if raw_val is None:
        return None
    if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool):
        return raw_val

    s_val = str(raw_val).strip()
    if s_val in {"", "None", "NULL", "-", "..", "...", "X", "x"}:
        return None

    cleaned = s_val.rstrip("*").strip()
    if not cleaned or cleaned in {"-", "..", "...", "X", "x"}:
        return None

    try:
        return int(cleaned)
    except ValueError:
        try:
            return float(cleaned)
        except ValueError:
            return None


def normalizar_texto(texto: str) -> str:
    """Remove acentos (unicodedata NFKD), converte para minúsculas e limpa não-alfanuméricos."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    minusc = sem_acento.lower()
    limpo = re.sub(r"[^a-z0-9_]+", "_", minusc)
    limpo = re.sub(r"_+", "_", limpo).strip("_")
    return limpo


def _extract_records(tabela: Any) -> List[Dict[str, Any]]:
    """Extrai registros tabulares padronizados em lista de dicionários."""
    records = []
    if hasattr(tabela, "getFeatures"):
        if not tabela.isValid():
            return []
        fields = [f.name() for f in tabela.fields()]
        for feat in tabela.getFeatures():
            code_muni = (
                str(feat["code_muni"])
                if "code_muni" in fields and feat["code_muni"] is not None
                else ""
            )
            var_id = (
                str(feat["var_id"])
                if "var_id" in fields and feat["var_id"] is not None
                else ""
            )
            var_nome = (
                str(feat["var_nome"])
                if "var_nome" in fields and feat["var_nome"] is not None
                else ""
            )
            produto = (
                str(feat["produto"])
                if "produto" in fields and feat["produto"] is not None
                else ""
            )
            valor_raw = feat["valor"] if "valor" in fields else None
            records.append({
                "code_muni": code_muni,
                "var_id": var_id,
                "var_nome": var_nome,
                "produto": produto,
                "valor": _parse_val(valor_raw),
            })
    elif isinstance(tabela, (list, tuple)):
        for item in tabela:
            if isinstance(item, dict):
                code_muni = str(item.get("code_muni", ""))
                var_id = str(item.get("var_id", ""))
                var_nome = str(item.get("var_nome", item.get("var", "")))
                produto = str(item.get("produto", ""))
                valor_raw = item.get("valor")
                records.append({
                    "code_muni": code_muni,
                    "var_id": var_id,
                    "var_nome": var_nome,
                    "produto": produto,
                    "valor": _parse_val(valor_raw),
                })
            elif isinstance(item, (list, tuple)):
                code_muni = ""
                if len(item) == 7:
                    var_id, var_nome, _unidade, produto, _periodo, valor_raw, code_muni = item
                elif len(item) == 6:
                    var_id, var_nome, _unidade, produto, _periodo, valor_raw = item
                elif len(item) == 4:
                    var_id, var_nome, produto, valor_raw = item
                elif len(item) == 3:
                    var_id, produto, valor_raw = item
                    var_nome = ""
                elif len(item) == 2:
                    produto, valor_raw = item
                    var_id, var_nome = "", ""
                else:
                    continue
                records.append({
                    "code_muni": str(code_muni or ""),
                    "var_id": str(var_id or ""),
                    "var_nome": str(var_nome or ""),
                    "produto": str(produto or ""),
                    "valor": _parse_val(valor_raw),
                })
    return records


def _gerar_nomes_campos(
    produtos: List[str],
    variaveis: List[str],
) -> Tuple[List[Tuple[str, str, str]], Dict[Tuple[str, str], str]]:
    """Gera nomes de campos normalizados, truncados e desempatados deterministicamente.

    Retorna:
        - lista de tuplas (var_key, prod_key, col_name)
        - mapa (var_key, prod_key) -> col_name
    """
    field_tuples = []
    allocated_names = set()
    col_map = {}

    multi_var = len(variaveis) > 1

    for prod in produtos:
        prod_norm = normalizar_texto(prod) or "produto"
        var_list = variaveis if variaveis else [""]
        for var in var_list:
            var_norm = normalizar_texto(var) if var else ""
            if multi_var and var_norm:
                base_name = f"{var_norm}_{prod_norm}"
            else:
                base_name = prod_norm

            base_name = normalizar_texto(base_name) or "campo"
            candidate = base_name[:MAX_GEOPACKAGE_FIELD_LEN]

            if candidate not in allocated_names:
                final_name = candidate
            else:
                idx = 2
                while True:
                    suffix = f"_{idx}"
                    prefix_len = MAX_GEOPACKAGE_FIELD_LEN - len(suffix)
                    candidate = f"{base_name[:prefix_len]}{suffix}"
                    if candidate not in allocated_names:
                        final_name = candidate
                        break
                    idx += 1

            allocated_names.add(final_name)
            field_tuples.append((var, prod, final_name))
            col_map[(var, prod)] = final_name

    return field_tuples, col_map


def tabela_para_camada(
    tabela: Any,
    code_muni: Union[int, str, List[Union[int, str]], Tuple[Union[int, str], ...], set],
    nome_muni: Optional[Union[str, List[Optional[str]], Tuple[Optional[str], ...]]] = None,
    layer_name: str = "agro_municipal",
    feedback: Any = None,
) -> Tuple[QgsVectorLayer, Dict[str, Any]]:
    """Converte tabela agropecuária IBGE + malha municipal em camada espacial (D5/D9).

    Suporta 1 ou N municípios (modo RM). Produz 1 feição por município com a sua geometria.
    Produtos sem valor numérico em nenhuma variável/município são descartados.

    Args:
        tabela: QgsVectorLayer sem geometria ou lista de registros/tuplas/dicts.
        code_muni: Código IBGE ou lista/tupla de códigos (ex: "3106200" ou ["3106200", "3170404"]).
        nome_muni: Nome ou lista de nomes de municípios (opcional).
        layer_name: Nome da camada de saída.
        feedback: QgsProcessingFeedback / QgsFeedback para progresso e logs.

    Returns:
        (layer, relatorio): Camada QgsVectorLayer (N feições, polígonos municipais formato largo)
        e dicionário relatório com contagem de produtos aproveitados/descartados.
    """
    def log(msg: str):
        if feedback is not None:
            feedback.pushInfo(msg)

    # 1. Normaliza lista de municípios (códigos e nomes)
    if isinstance(code_muni, (list, tuple, set)):
        code_list = [str(c).strip() for c in code_muni]
    else:
        code_list = [str(code_muni).strip()]

    if isinstance(nome_muni, (list, tuple)):
        nome_list = [str(n) if n is not None else None for n in nome_muni]
    elif nome_muni is not None:
        nome_list = [str(nome_muni)] * len(code_list)
    else:
        nome_list = [None] * len(code_list)

    # 2. Obtém polígono de cada município
    muni_geoms = {}
    crs_auth = "EPSG:4674"
    wkb_type = "MultiPolygon"

    for c_code, c_nome in zip(code_list, nome_list):
        poligono = _municipio_poligono(c_code, c_nome)
        if poligono is not None and poligono.isValid():
            muni_feats = list(poligono.getFeatures())
            if muni_feats:
                crs_auth = poligono.crs().authid() or "EPSG:4674"
                wkb_type = QgsWkbTypes.displayString(poligono.wkbType()) or "MultiPolygon"
                if len(muni_feats) == 1:
                    muni_geoms[c_code] = muni_feats[0].geometry()
                else:
                    muni_geoms[c_code] = QgsGeometry.unaryUnion([f.geometry() for f in muni_feats])

    if not muni_geoms:
        if len(code_list) == 1:
            err_msg = f"Nao foi possivel obter o poligono do municipio '{code_list[0]}'"
        else:
            err_msg = f"Nao foi possivel obter poligonos para os municipios: {code_list}"
        log(f"AgroPipeline: {err_msg}")
        inv = _invalid_layer(layer_name, err_msg)
        relatorio = {
            "produtos_aproveitados": 0,
            "produtos_descartados": 0,
            "produtos_aproveitados_lista": [],
            "produtos_descartados_lista": [],
            "infos": [],
            "avisos": [err_msg],
        }
        return inv, relatorio

    # 3. Extrai registros e atribui code_muni padrão se houver apenas 1 município no filtro
    records = _extract_records(tabela)
    if len(code_list) == 1:
        single_code = code_list[0]
        for r in records:
            if not r["code_muni"]:
                r["code_muni"] = single_code

    # Coleta produtos na ordem de aparecimento
    unique_products = []
    for rec in records:
        prod = rec["produto"]
        if prod and prod not in unique_products:
            unique_products.append(prod)

    # Classifica produtos em aproveitados vs descartados (D5)
    produtos_aproveitados = []
    produtos_descartados = []

    # Mapa (code_muni, var_key, prod_key) -> valor
    values_map = {}

    for rec in records:
        c_code = rec["code_muni"]
        var_key = rec["var_nome"] or rec["var_id"]
        prod = rec["produto"]
        if c_code and prod:
            values_map[(c_code, var_key, prod)] = rec["valor"]

    for prod in unique_products:
        prod_recs = [r for r in records if r["produto"] == prod]
        has_value = any(r["valor"] is not None for r in prod_recs)
        if has_value:
            produtos_aproveitados.append(prod)
        else:
            produtos_descartados.append(prod)

    # Identifica variáveis únicas entre os produtos aproveitados
    unique_vars = []
    for rec in records:
        if rec["produto"] in produtos_aproveitados:
            var_key = rec["var_nome"] or rec["var_id"]
            if var_key and var_key not in unique_vars:
                unique_vars.append(var_key)

    # 4. Monta definição dos campos
    field_tuples, col_map = _gerar_nomes_campos(produtos_aproveitados, unique_vars)

    # 5. Cria a camada de memória formato largo
    out_layer = QgsVectorLayer(
        f"{wkb_type}?crs={crs_auth}", layer_name, "memory"
    )
    dp = out_layer.dataProvider()

    qfields = [QgsField("code_muni", field_type("string"))]
    for _var_key, _prod_key, col_name in field_tuples:
        qfields.append(QgsField(col_name, field_type("double")))

    dp.addAttributes(qfields)
    out_layer.updateFields()

    # 6. Adiciona feições: 1 por município em code_list
    out_features = []
    for c_code in code_list:
        muni_geom = muni_geoms.get(c_code)
        feat = QgsFeature(out_layer.fields())
        if muni_geom is not None:
            feat.setGeometry(muni_geom)

        attrs = [c_code]
        for var_key, prod_key, _col_name in field_tuples:
            val = values_map.get((c_code, var_key, prod_key))
            attrs.append(val)

        feat.setAttributes(attrs)
        out_features.append(feat)

        # Log por município
        muni_val_count = sum(
            1 for var_key, prod_key, _ in field_tuples if values_map.get((c_code, var_key, prod_key)) is not None
        )
        log(
            f"AgroPipeline [{c_code}]: {muni_val_count} valores preenchidos de "
            f"{len(field_tuples)} campos em {len(produtos_aproveitados)} produtos aproveitados."
        )

    dp.addFeatures(out_features)
    out_layer.updateExtents()

    # 7. Monta relatório
    relatorio = {
        "produtos_aproveitados": len(produtos_aproveitados),
        "produtos_descartados": len(produtos_descartados),
        "produtos_aproveitados_lista": produtos_aproveitados,
        "produtos_descartados_lista": produtos_descartados,
        "infos": [
            f"AgroPipeline: {len(produtos_aproveitados)} produtos aproveitados, "
            f"{len(produtos_descartados)} produtos descartados em {len(code_list)} municipios."
        ],
        "avisos": [],
    }

    if produtos_descartados:
        relatorio["avisos"].append(
            f"AgroPipeline: descartados {len(produtos_descartados)} produtos sem valor numerico "
            f"em nenhuma variavel/municipio: {', '.join(produtos_descartados)}"
        )

    log(
        f"AgroPipeline: camada '{layer_name}' criada com {len(out_features)} feicoes (municipios), "
        f"{len(produtos_aproveitados)} produtos e {len(qfields)} campos."
    )

    return out_layer, relatorio
