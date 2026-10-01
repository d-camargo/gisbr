# -*- coding: utf-8 -*-
"""Pipeline de redes lineares: geometrias vetoriais -> topologia real -> camadas QGIS.

Borda QGIS (D11 da rodada 23) sobre a stdlib pura de `rede_linhas.py`.
Reconstrói topologia de redes rodoviárias e ferroviárias, aplica exclusão
de trechos planejados/inexistentes (D12), detecta junções em T e coincidentes,
e gera até quatro camadas em memória (EPSG:4674):
  - links: arcos com atributos originais + atributos D11
  - nos: nós com grau e componente (mesmo esquema _NODE_FIELDS do osm_pipeline)
  - problemas: problemas apontados e correções aplicadas (severidade=corrigido)
  - removidos: trechos descartados (motivo=planejado ou duplicado_federal), criada apenas se houver remoções.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from qgis.core import (
    Qgis,
    QgsDistanceArea,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsLineString,
    QgsPoint,
    QgsRectangle,
    QgsSpatialIndex,
    QgsVectorLayer,
    QgsWkbTypes,
)

from . import qgis_compat
from .osm_pipeline import (
    _NODE_FIELDS,
    _cria_problemas_layer,
    _monta_problemas,
    diagnostica,
)
from .rede_linhas import filtra_existentes, monta_rede


# Tolerâncias e limiares de duplicidade federal x estadual (D13)
TOL_DUP_M: float = 50.0
LIMIAR_TOQUE_M: float = 100.0
LIMIAR_SOBREPOSICAO_SEM_ATRIBUTO_M: float = 200.0
LIMIAR_RESTO_M: float = 50.0

# Aliases descritivos
LIMIAR_ENTRONCAMENTO_M: float = LIMIAR_TOQUE_M
LIMIAR_MIN_SOBREPOSICAO_M: float = LIMIAR_TOQUE_M
LIMIAR_SEM_ATRIBUTO_M: float = LIMIAR_SOBREPOSICAO_SEM_ATRIBUTO_M
LIMIAR_RESIDUO_M: float = LIMIAR_RESTO_M


def _extrai_codigos_br(val: Any) -> Set[str]:
    """Extrai números de rodovia federal (3 dígitos, ex. '040', '135') de uma string."""
    if val is None:
        return set()
    s = str(val).strip()
    if not s:
        return set()
    nums = re.findall(r"\d+", s)
    res: Set[str] = set()
    for n in nums:
        try:
            res.add(str(int(n)).zfill(3))
        except ValueError:
            pass
    return res


def _filtra_apenas_linhas(geom: Optional[QgsGeometry]) -> Optional[QgsGeometry]:
    """Garante que a geometria contenha apenas partes lineares (LineString / MultiLineString)."""
    if geom is None or geom.isEmpty():
        return None
    if geom.type() == QgsWkbTypes.LineGeometry:
        return geom
    linhas: List[QgsGeometry] = []
    try:
        parts = geom.asGeometryCollection()
    except Exception:
        parts = []
    for part in parts:
        if part and not part.isEmpty() and part.type() == QgsWkbTypes.LineGeometry:
            linhas.append(part)
    if not linhas:
        return None
    if len(linhas) == 1:
        return linhas[0]
    return QgsGeometry.unaryUnion(linhas)


def _is_federal_planejado(feat: QgsFeature, cfg_rede_fed: Optional[Dict[str, Any]]) -> bool:
    """Verifica se uma feição federal é considerada planejada/inexistente (D12)."""
    excluir = cfg_rede_fed.get("excluir") if isinstance(cfg_rede_fed, dict) else None
    if excluir and isinstance(excluir, dict):
        campo = excluir.get("campo")
        valores = excluir.get("valores") or []
        if isinstance(valores, str):
            valores = [valores]
        vals_set = {str(v).strip().upper() for v in valores}
        if campo and campo in feat.fields().names():
            val = feat[campo]
            if val is not None and str(val).strip().upper() in vals_set:
                return True
            return False
    if "ds_superfi" in feat.fields().names():
        val = feat["ds_superfi"]
        if val is not None and str(val).strip().upper() == "PLA":
            return True
    return False


def _nomes_camadas(layer_name: str) -> Dict[str, str]:
    """Gera os nomes padrão das camadas a partir do layer_name base (<id>_<sufixo>)."""
    if "_" in layer_name:
        id_part, _, sufixo = layer_name.rpartition("_")
        return {
            "links": layer_name,
            "nos": f"{id_part}_nos_{sufixo}",
            "problemas": f"{id_part}_problemas_{sufixo}",
            "removidos": f"{id_part}_removidos_{sufixo}",
        }
    return {
        "links": layer_name,
        "nos": f"{layer_name}_nos",
        "problemas": f"{layer_name}_problemas",
        "removidos": f"{layer_name}_removidos",
    }


def montar_rede(
    layer: QgsVectorLayer,
    cfg_rede: Optional[Dict[str, Any]],
    poligono: Any,
    layer_name: str,
    feedback: Optional[Any] = None,
) -> Dict[str, Any]:
    """Constrói as camadas de topologia linear (links, nós, problemas, removidos) em memória.

    Args:
        layer: Camada vetorial de entrada (EPSG:4674).
        cfg_rede: Configuração declarativa da rede contendo "tipo" ('rodoviaria'|'ferroviaria')
            e "excluir" (critério de trechos planejados/inexistentes do D12).
        poligono: QgsGeometry ou QgsVectorLayer com o polígono do recorte, ou None.
        layer_name: Nome base da camada (ex.: 'dnit_snv_3118601').
        feedback: Objeto QgsProcessingFeedback opcional para log e cancelamento.

    Returns:
        Dict com "links", "nos", "problemas", "removidos" (ou None) e "relatorio" (contagens).
    """
    cfg = cfg_rede or {}
    tipo_rede = cfg.get("tipo", "rodoviaria")
    excluir = cfg.get("excluir")
    nomes = _nomes_camadas(layer_name)

    # -------------------------------------------------------------------------
    # 1. Extração de feições e aplicação do filtro de existentes (D12)
    # -------------------------------------------------------------------------
    feicoes_raw: List[Dict[str, Any]] = []
    nomes_campos_orig = layer.fields().names()

    for feat in layer.getFeatures():
        attrs = {fld.name(): feat[fld.name()] for fld in layer.fields()}
        geom = feat.geometry()
        partes: List[List[tuple]] = []
        if geom and not geom.isEmpty():
            if geom.isMultipart():
                for part in geom.asMultiPolyline():
                    partes.append([(float(pt.x()), float(pt.y())) for pt in part])
            else:
                partes.append([(float(pt.x()), float(pt.y())) for pt in geom.asPolyline()])

        fid_val = feat["fid"] if "fid" in nomes_campos_orig and feat["fid"] is not None else feat.id()
        feicoes_raw.append({
            "feat": feat,
            "fid": fid_val,
            "partes": partes,
            "attrs": attrs,
        })

    mantidas, removidas = filtra_existentes(feicoes_raw, excluir)

    # -------------------------------------------------------------------------
    # 2. Camada de removidos (apenas se houver feições removidas)
    # -------------------------------------------------------------------------
    layer_removidos: Optional[QgsVectorLayer] = None
    if removidas:
        # Multi: o recorte por polígono (native:clip) promove as geometrias a
        # multipartes e uma camada LineString recusaria o commit (§10).
        wkb_rem = QgsWkbTypes.displayString(QgsWkbTypes.multiType(layer.wkbType()))
        layer_removidos = QgsVectorLayer("{}?crs=EPSG:4674".format(wkb_rem), nomes["removidos"], "memory")
        dp_rem = layer_removidos.dataProvider()
        campos_rem_add = []
        campos_nomes_rem = set()
        for fld in layer.fields():
            campos_rem_add.append(QgsField(fld.name(), fld.type(), fld.typeName()))
            campos_nomes_rem.add(fld.name())
        if "motivo" not in campos_nomes_rem:
            campos_rem_add.append(QgsField("motivo", qgis_compat.field_type("string")))
        dp_rem.addAttributes(campos_rem_add)
        layer_removidos.updateFields()

        layer_removidos.startEditing()
        campos_rem = layer_removidos.fields()
        for item in removidas:
            f_orig = item["feat"]
            f_new = QgsFeature(campos_rem)
            f_new.setGeometry(f_orig.geometry())
            for fld in layer.fields():
                f_new[fld.name()] = f_orig[fld.name()]
            motivo_padrao = (excluir.get("motivo") if isinstance(excluir, dict) else None) or "planejado"
            f_new["motivo"] = item.get("motivo") or motivo_padrao
            layer_removidos.addFeature(f_new)
        layer_removidos.commitChanges()

    # -------------------------------------------------------------------------
    # 3. Montagem da rede (stdlib pura) e diagnóstico de componentes
    # -------------------------------------------------------------------------
    arcos, nos, correcoes, contagens = monta_rede(mantidas)
    diag = diagnostica(arcos, "veicular")

    # -------------------------------------------------------------------------
    # 4. Verificação geométrica e camada de problemas
    # -------------------------------------------------------------------------
    # Prepara a geometria do recorte para o GeometryEngine
    poly_geom: Optional[QgsGeometry] = None
    if poligono is not None:
        if hasattr(poligono, "getFeatures"):
            geoms = [f.geometry() for f in poligono.getFeatures()
                     if f.geometry() and not f.geometry().isEmpty()]
            if geoms:
                poly_geom = geoms[0] if len(geoms) == 1 else QgsGeometry.unaryUnion(geoms)
        elif isinstance(poligono, QgsGeometry) and not poligono.isEmpty():
            poly_geom = poligono

    if poly_geom is None or poly_geom.isEmpty():
        extent = layer.extent()
        if extent.isNull() or extent.isEmpty():
            extent = QgsRectangle(-180, -90, 180, 90)
        else:
            dx = max(extent.width() * 0.05, 0.01)
            dy = max(extent.height() * 0.05, 0.01)
            extent = QgsRectangle(extent.xMinimum() - dx, extent.yMinimum() - dy,
                                  extent.xMaximum() + dx, extent.yMaximum() + dy)
        poly_geom = QgsGeometry.fromRect(extent)

    engine = QgsGeometry.createGeometryEngine(poly_geom.constGet())
    engine.prepareGeometry()

    # Prepara arcos para osm_pipeline (_monta_problemas espera way_id e nodes)
    dummy_node_id = -1
    for arco in arcos:
        if "way_id" not in arco:
            arco["way_id"] = arco.get("fid", 0)
        if "nodes" not in arco:
            c_len = len(arco["coords"])
            if c_len <= 2:
                arco["nodes"] = [arco["from_node"], arco["to_node"]][:c_len]
            else:
                intermed = []
                for _ in range(c_len - 2):
                    intermed.append(dummy_node_id)
                    dummy_node_id -= 1
                arco["nodes"] = [arco["from_node"]] + intermed + [arco["to_node"]]

    problemas_osm, _ = _monta_problemas(arcos, diag, nos, engine, tipo_rede, feedback=feedback)

    # Junta problemas não resolvidos e correções com severidade="corrigido"
    problemas_todos = list(problemas_osm)
    for c in correcoes:
        problemas_todos.append({
            "tipo": c["tipo"],
            "severidade": "corrigido",
            "detalhe": c.get("detalhe", ""),
            "node_id": c.get("node_id"),
            "arc_id": c.get("arc_id"),
            "x": c["x"],
            "y": c["y"],
            "rede": tipo_rede,
        })

    layer_problemas = _cria_problemas_layer(problemas_todos, layer_name=nomes["problemas"])

    # -------------------------------------------------------------------------
    # 5. Camada de links (arcos com atributos originais + atributos D11)
    # -------------------------------------------------------------------------
    layer_links = QgsVectorLayer("LineString?crs=EPSG:4674", nomes["links"], "memory")
    dp_links = layer_links.dataProvider()
    campos_links_add = []
    campos_nomes_existentes = set()
    for fld in layer.fields():
        campos_links_add.append(QgsField(fld.name(), fld.type(), fld.typeName()))
        campos_nomes_existentes.add(fld.name())

    d11_campos = [
        ("arc_id", "int"),
        ("from_node", "int"),
        ("to_node", "int"),
        ("comprimento_m", "double"),
        ("componente", "int"),
        ("componente_tam", "int"),
        ("coincidentes", "string"),
    ]
    for nome_c, tipo_c in d11_campos:
        if nome_c not in campos_nomes_existentes:
            campos_links_add.append(QgsField(nome_c, qgis_compat.field_type(tipo_c)))
            campos_nomes_existentes.add(nome_c)

    dp_links.addAttributes(campos_links_add)
    layer_links.updateFields()

    layer_links.startEditing()
    campos_links = layer_links.fields()
    node_comp = diag.get("node_comp", {})
    comp_tam = diag.get("comp_tam", {})

    for arco in arcos:
        pts = [QgsPoint(coord[0], coord[1]) for coord in arco["coords"]]
        if len(pts) < 2:
            continue
        geom = QgsGeometry(QgsLineString(pts))
        feat = QgsFeature(campos_links)
        feat.setGeometry(geom)

        attrs = arco.get("attrs") or {}
        for fld in layer.fields():
            if fld.name() in attrs:
                feat[fld.name()] = attrs[fld.name()]

        comp = node_comp.get(arco["from_node"], -1)
        comp_tam_val = comp_tam.get(comp) if comp != -1 else None

        feat["arc_id"] = arco["arc_id"]
        feat["from_node"] = arco["from_node"]
        feat["to_node"] = arco["to_node"]
        feat["comprimento_m"] = arco.get("comprimento_m", 0.0)
        feat["componente"] = comp
        feat["componente_tam"] = comp_tam_val
        feat["coincidentes"] = arco.get("coincidentes", "")

        layer_links.addFeature(feat)
    layer_links.commitChanges()

    # -------------------------------------------------------------------------
    # 6. Camada de nós (_NODE_FIELDS do osm_pipeline)
    # -------------------------------------------------------------------------
    layer_nos = QgsVectorLayer("Point?crs=EPSG:4674", nomes["nos"], "memory")
    dp_nos = layer_nos.dataProvider()
    campos_nos_add = [QgsField(nome, qgis_compat.field_type(tipo)) for nome, tipo in _NODE_FIELDS]
    dp_nos.addAttributes(campos_nos_add)
    layer_nos.updateFields()

    layer_nos.startEditing()
    campos_nos = layer_nos.fields()
    grau_map = diag.get("grau", {})
    comp_map = diag.get("node_comp", {})

    for node_id in sorted(nos.keys()):
        coord = nos[node_id]
        feat = QgsFeature(campos_nos)
        feat.setGeometry(QgsGeometry(QgsPoint(coord[0], coord[1])))
        feat["node_id"] = node_id
        feat["x"] = coord[0]
        feat["y"] = coord[1]
        feat["grau"] = grau_map.get(node_id, 0)
        feat["componente"] = comp_map.get(node_id, -1)
        layer_nos.addFeature(feat)
    layer_nos.commitChanges()

    # -------------------------------------------------------------------------
    # 7. Relatório e mensagem de log
    # -------------------------------------------------------------------------
    relatorio = dict(contagens)
    relatorio["removidos"] = len(removidas)
    relatorio["problemas"] = len(problemas_todos)

    if feedback is not None:
        msg_resumo = (
            f"Rede ({tipo_rede}) '{layer_name}': "
            f"{contagens.get('arcos', len(arcos))} arcos, "
            f"{contagens.get('nos', len(nos))} nós, "
            f"{len(problemas_todos)} problemas/correções"
        )
        if removidas:
            msg_resumo += f", {len(removidas)} removidos"
        feedback.pushInfo(msg_resumo)

    return {
        "links": layer_links,
        "nos": layer_nos,
        "problemas": layer_problemas,
        "removidos": layer_removidos,
        "relatorio": relatorio,
    }


def remove_duplicidade_federal(
    layer_est: QgsVectorLayer,
    layer_fed: QgsVectorLayer,
    cfg_dup: Optional[Dict[str, Any]] = None,
    cfg_rede_fed: Optional[Dict[str, Any]] = None,
    feedback: Optional[Any] = None,
    layer_fed_pla: Optional[QgsVectorLayer] = None,
) -> Tuple[QgsVectorLayer, Optional[QgsVectorLayer], Optional[QgsVectorLayer], Dict[str, Any]]:
    """Remove trechos de rodovias federais duplicados na malha estadual (D13).

    Compara layer_est contra layer_fed e:
    - estadual 'Federal' sobre DNIT com mesma BR -> sai inteira (vai para removidos);
    - estadual 'Federal' com sobreposição parcial (resto >= 50m) -> sai só sobreposta, resto fica;
    - estadual 'Federal' sobre federal 'PLA' -> fica + problema 'federal_sem_par';
    - estadual 'Federal' sobre federal com BR divergente -> fica + problema 'federal_br_divergente';
    - estadual 'Estadual' sobreposta > 200 m -> fica + problema 'sobreposicao_sem_atributo';
    - toque em entroncamento (< 100 m) -> nada (mantido sem problema);
    - campo_br ausente -> decide só por jurisdição e sobreposição;
    - federal coincidente (ds_coinc) aceita qualquer uma das BRs listadas.

    Args:
        layer_est: Camada vetorial estadual (EPSG:4674).
        layer_fed: Camada vetorial federal (EPSG:4674).
        cfg_dup: Configuração declarativa da duplicidade.
        cfg_rede_fed: Configuração da rede federal (com critério excluir).
        feedback: Feedback opcional para log.

    Returns:
        (layer_est_limpa, removidos, problemas, relatorio)
    """
    if layer_est is None or not layer_est.isValid():
        return None, None, None, {}

    nomes = _nomes_camadas(layer_est.name())

    if layer_fed is None or not layer_fed.isValid() or layer_fed.featureCount() == 0:
        layer_est_limpa = QgsVectorLayer("MultiLineString?crs=EPSG:4674", layer_est.name(), "memory")
        dp = layer_est_limpa.dataProvider()
        dp.addAttributes([QgsField(f.name(), f.type(), f.typeName()) for f in layer_est.fields()])
        layer_est_limpa.updateFields()
        layer_est_limpa.startEditing()
        for f in layer_est.getFeatures():
            layer_est_limpa.addFeature(f)
        layer_est_limpa.commitChanges()
        return layer_est_limpa, None, None, {"mantidos": layer_est.featureCount(), "removidos": 0, "problemas": 0}

    cfg_d = cfg_dup or {}
    campo_jurisdicao = cfg_d.get("campo_jurisdicao") or "jurisdicao"
    valor_federal = str(cfg_d.get("valor_federal", "Federal")).strip().lower()
    campo_br = cfg_d.get("campo_br")

    nomes_campos_est = layer_est.fields().names()
    tem_campo_br = bool(campo_br and campo_br in nomes_campos_est)

    nomes_campos_fed = layer_fed.fields().names()
    campo_br_fed = cfg_d.get("campo_br_fed")
    if not campo_br_fed:
        for cand in ["vl_codigo", "codigo", "rodovia", "br", "cod_rodovia"]:
            if cand in nomes_campos_fed:
                campo_br_fed = cand
                break

    campo_coinc_fed = cfg_d.get("campo_coinc_fed")
    if not campo_coinc_fed:
        for cand in ["ds_coinc", "coincidentes", "vl_coinc"]:
            if cand in nomes_campos_fed:
                campo_coinc_fed = cand
                break

    medidor = QgsDistanceArea()
    medidor.setEllipsoid("GRS80")

    deg_buf = TOL_DUP_M / 111320.0
    cap_style = getattr(getattr(Qgis, "EndCapStyle", None), "Flat", 2)
    join_style = getattr(getattr(Qgis, "JoinStyle", None), "Round", 1)

    index_fed = QgsSpatialIndex()
    fed_dados: Dict[int, Dict[str, Any]] = {}

    for feat_f in layer_fed.getFeatures():
        geom_f = feat_f.geometry()
        if not geom_f or geom_f.isEmpty():
            continue

        is_pla = _is_federal_planejado(feat_f, cfg_rede_fed)

        cods_f: Set[str] = set()
        if campo_br_fed and campo_br_fed in nomes_campos_fed:
            cods_f |= _extrai_codigos_br(feat_f[campo_br_fed])
        if campo_coinc_fed and campo_coinc_fed in nomes_campos_fed:
            cods_f |= _extrai_codigos_br(feat_f[campo_coinc_fed])

        buf_f = geom_f.buffer(deg_buf, 8, cap_style, join_style, 2.0)
        fid_f = feat_f.id()
        index_fed.addFeature(feat_f)
        fed_dados[fid_f] = {
            "geom": geom_f,
            "buf": buf_f,
            "is_pla": is_pla,
            "codigos": cods_f,
        }

    # D13/critério 10: no esquema de 4 camadas os trechos PLA do DNIT saem da
    # links e vão para a removidos — eles são a referência "planejada" que
    # gera federal_sem_par no estadual (262BMG0550).
    if layer_fed_pla is not None and layer_fed_pla.isValid():
        campos_pla = layer_fed_pla.fields().names()
        # ids negativos: os fids da removidos recomeçam em 1 e colidiriam
        # com os da links em fed_dados/índice espacial.
        pla_prox_id = -1
        for feat_p in layer_fed_pla.getFeatures():
            geom_p = feat_p.geometry()
            if not geom_p or geom_p.isEmpty():
                continue
            if geom_p.type() != QgsWkbTypes.LineGeometry:
                continue
            buf_p = geom_p.buffer(deg_buf, 8, cap_style, join_style, 2.0)
            cods_p: Set[str] = set()
            if campo_br_fed and campo_br_fed in campos_pla:
                cods_p |= _extrai_codigos_br(feat_p[campo_br_fed])
            if campo_coinc_fed and campo_coinc_fed in campos_pla:
                cods_p |= _extrai_codigos_br(feat_p[campo_coinc_fed])
            fid_p = pla_prox_id
            pla_prox_id -= 1
            feat_p.setId(fid_p)
            index_fed.addFeature(feat_p)
            fed_dados[fid_p] = {
                "geom": geom_p,
                "buf": buf_p,
                "is_pla": True,
                "codigos": cods_p,
            }

    mantidos_feats: List[Tuple[QgsFeature, QgsGeometry]] = []
    removidos_feats: List[Tuple[QgsFeature, QgsGeometry]] = []
    problemas_lista: List[Dict[str, Any]] = []

    count_mantidos = 0
    count_removidos = 0
    count_cortados = 0
    count_federal_sem_par = 0
    count_federal_br_divergente = 0
    count_sobreposicao_sem_atributo = 0

    for feat_e in layer_est.getFeatures():
        geom_e = feat_e.geometry()
        if not geom_e or geom_e.isEmpty():
            continue

        comp_orig = medidor.measureLength(geom_e)
        if comp_orig <= 0.0:
            mantidos_feats.append((feat_e, geom_e))
            count_mantidos += 1
            continue

        is_federal = False
        if campo_jurisdicao in nomes_campos_est:
            v_j = feat_e[campo_jurisdicao]
            if v_j is not None and str(v_j).strip().lower() == valor_federal:
                is_federal = True

        cods_e: Set[str] = set()
        if tem_campo_br:
            cods_e = _extrai_codigos_br(feat_e[campo_br])

        bbox_e = geom_e.boundingBox()
        bbox_busca = QgsRectangle(
            bbox_e.xMinimum() - deg_buf,
            bbox_e.yMinimum() - deg_buf,
            bbox_e.xMaximum() + deg_buf,
            bbox_e.yMaximum() + deg_buf,
        )
        cand_ids = index_fed.intersects(bbox_busca)

        cands_ativas: List[Dict[str, Any]] = []
        cands_pla: List[Dict[str, Any]] = []
        for cid in cand_ids:
            cfed = fed_dados.get(cid)
            if not cfed:
                continue
            if geom_e.intersects(cfed["buf"]):
                if cfed["is_pla"]:
                    cands_pla.append(cfed)
                else:
                    cands_ativas.append(cfed)

        cands_ativas_match: List[Dict[str, Any]] = []
        cands_ativas_diverg: List[Dict[str, Any]] = []
        if tem_campo_br and cods_e:
            for ca in cands_ativas:
                if ca["codigos"] & cods_e:
                    cands_ativas_match.append(ca)
                else:
                    cands_ativas_diverg.append(ca)
        else:
            cands_ativas_match = list(cands_ativas)

        inter_match = None
        comp_over_match = 0.0
        buf_match_union = None
        if cands_ativas_match:
            bufs_m = [c["buf"] for c in cands_ativas_match]
            buf_match_union = bufs_m[0] if len(bufs_m) == 1 else QgsGeometry.unaryUnion(bufs_m)
            inter_match = _filtra_apenas_linhas(geom_e.intersection(buf_match_union))
            if inter_match:
                comp_over_match = medidor.measureLength(inter_match)

        if comp_over_match >= LIMIAR_TOQUE_M:
            if is_federal:
                diff = _filtra_apenas_linhas(geom_e.difference(buf_match_union))
                comp_resto = medidor.measureLength(diff) if diff else 0.0

                if comp_resto < LIMIAR_RESTO_M or (comp_over_match / comp_orig) >= 0.95:
                    removidos_feats.append((feat_e, geom_e))
                    count_removidos += 1
                else:
                    removidos_feats.append((feat_e, inter_match))
                    mantidos_feats.append((feat_e, diff))
                    count_removidos += 1
                    count_mantidos += 1
                    count_cortados += 1
                continue

        if is_federal:
            inter_div = None
            comp_over_div = 0.0
            if cands_ativas_diverg:
                bufs_d = [c["buf"] for c in cands_ativas_diverg]
                buf_d_union = bufs_d[0] if len(bufs_d) == 1 else QgsGeometry.unaryUnion(bufs_d)
                inter_div = _filtra_apenas_linhas(geom_e.intersection(buf_d_union))
                if inter_div:
                    comp_over_div = medidor.measureLength(inter_div)

            if comp_over_div >= LIMIAR_TOQUE_M:
                c_pt = inter_div.centroid().asPoint() if inter_div else geom_e.centroid().asPoint()
                problemas_lista.append({
                    "tipo": "federal_br_divergente",
                    "severidade": "media",
                    "detalhe": f"BR estadual {sorted(cods_e)} diverge da federal sobreposta ({comp_over_div:.1f} m)",
                    "node_id": None,
                    "arc_id": feat_e.id(),
                    "rede": "rodoviaria",
                    "x": c_pt.x(),
                    "y": c_pt.y(),
                })
                mantidos_feats.append((feat_e, geom_e))
                count_mantidos += 1
                count_federal_br_divergente += 1
                continue

            inter_pla = None
            comp_over_pla = 0.0
            if cands_pla:
                bufs_p = [c["buf"] for c in cands_pla]
                buf_p_union = bufs_p[0] if len(bufs_p) == 1 else QgsGeometry.unaryUnion(bufs_p)
                inter_pla = _filtra_apenas_linhas(geom_e.intersection(buf_p_union))
                if inter_pla:
                    comp_over_pla = medidor.measureLength(inter_pla)

            if comp_over_pla >= LIMIAR_TOQUE_M:
                c_pt = inter_pla.centroid().asPoint() if inter_pla else geom_e.centroid().asPoint()
                problemas_lista.append({
                    "tipo": "federal_sem_par",
                    "severidade": "baixa",
                    "detalhe": f"trecho federal estadual sobre federal planejado/inexistente ({comp_over_pla:.1f} m)",
                    "node_id": None,
                    "arc_id": feat_e.id(),
                    "rede": "rodoviaria",
                    "x": c_pt.x(),
                    "y": c_pt.y(),
                })
                mantidos_feats.append((feat_e, geom_e))
                count_mantidos += 1
                count_federal_sem_par += 1
                continue

            mantidos_feats.append((feat_e, geom_e))
            count_mantidos += 1
            continue

        else:
            inter_at = None
            comp_over_at = 0.0
            if cands_ativas:
                bufs_a = [c["buf"] for c in cands_ativas]
                buf_a_union = bufs_a[0] if len(bufs_a) == 1 else QgsGeometry.unaryUnion(bufs_a)
                inter_at = _filtra_apenas_linhas(geom_e.intersection(buf_a_union))
                if inter_at:
                    comp_over_at = medidor.measureLength(inter_at)

            if comp_over_at > LIMIAR_SOBREPOSICAO_SEM_ATRIBUTO_M:
                c_pt = inter_at.centroid().asPoint() if inter_at else geom_e.centroid().asPoint()
                problemas_lista.append({
                    "tipo": "sobreposicao_sem_atributo",
                    "severidade": "media",
                    "detalhe": f"trecho estadual sobreposto {comp_over_at:.1f} m a rede federal sem atributo federal",
                    "node_id": None,
                    "arc_id": feat_e.id(),
                    "rede": "rodoviaria",
                    "x": c_pt.x(),
                    "y": c_pt.y(),
                })
                count_sobreposicao_sem_atributo += 1

            mantidos_feats.append((feat_e, geom_e))
            count_mantidos += 1

    layer_est_limpa = QgsVectorLayer("MultiLineString?crs=EPSG:4674", nomes["links"], "memory")
    dp_l = layer_est_limpa.dataProvider()
    dp_l.addAttributes([QgsField(f.name(), f.type(), f.typeName()) for f in layer_est.fields()])
    layer_est_limpa.updateFields()
    layer_est_limpa.startEditing()
    campos_l = layer_est_limpa.fields()
    for feat_orig, geom in mantidos_feats:
        fn = QgsFeature(campos_l)
        fn.setGeometry(geom)
        for fld in layer_est.fields():
            fn[fld.name()] = feat_orig[fld.name()]
        layer_est_limpa.addFeature(fn)
    layer_est_limpa.commitChanges()

    layer_removidos = None
    if removidos_feats:
        layer_removidos = QgsVectorLayer("MultiLineString?crs=EPSG:4674", nomes["removidos"], "memory")
        dp_r = layer_removidos.dataProvider()
        campos_r_add = [QgsField(f.name(), f.type(), f.typeName()) for f in layer_est.fields()]
        if "motivo" not in nomes_campos_est:
            campos_r_add.append(QgsField("motivo", qgis_compat.field_type("string")))
        dp_r.addAttributes(campos_r_add)
        layer_removidos.updateFields()
        layer_removidos.startEditing()
        campos_r = layer_removidos.fields()
        for feat_orig, geom in removidos_feats:
            fr = QgsFeature(campos_r)
            fr.setGeometry(geom)
            for fld in layer_est.fields():
                fr[fld.name()] = feat_orig[fld.name()]
            fr["motivo"] = "duplicado_federal"
            layer_removidos.addFeature(fr)
        layer_removidos.commitChanges()

    layer_problemas = None
    if problemas_lista:
        layer_problemas = _cria_problemas_layer(problemas_lista, layer_name=nomes["problemas"])

    relatorio = {
        "mantidos": count_mantidos,
        "removidos": count_removidos,
        "cortados": count_cortados,
        "problemas": len(problemas_lista),
        "federal_sem_par": count_federal_sem_par,
        "federal_br_divergente": count_federal_br_divergente,
        "sobreposicao_sem_atributo": count_sobreposicao_sem_atributo,
    }

    if feedback is not None:
        msg_resumo = (
            f"Duplicidade federal x estadual '{layer_est.name()}': "
            f"{count_mantidos} mantidos, {count_removidos} removidos"
        )
        if count_cortados:
            msg_resumo += f" ({count_cortados} parciais)"
        if problemas_lista:
            msg_resumo += f", {len(problemas_lista)} problemas"
        feedback.pushInfo(msg_resumo)

    return (layer_est_limpa, layer_removidos, layer_problemas, relatorio)
