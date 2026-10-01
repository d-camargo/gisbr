# -*- coding: utf-8 -*-
"""Testes de integração para gisbr.core.rede_pipeline (D11)."""

import math
from typing import Tuple

import pytest
from qgis.core import (
    QgsDistanceArea,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsVectorLayer,
)

from gisbr.core import qgis_compat
from gisbr.core.rede_pipeline import (
    LIMIAR_RESTO_M,
    LIMIAR_SOBREPOSICAO_SEM_ATRIBUTO_M,
    LIMIAR_TOQUE_M,
    TOL_DUP_M,
    _nomes_camadas,
    montar_rede,
    remove_duplicidade_federal,
)


def test_nomes_camadas():
    """Valida a formação dos nomes de camadas derivados do layer_name base."""
    nomes = _nomes_camadas("dnit_snv_3118601")
    assert nomes["links"] == "dnit_snv_3118601"
    assert nomes["nos"] == "dnit_snv_nos_3118601"
    assert nomes["problemas"] == "dnit_snv_problemas_3118601"
    assert nomes["removidos"] == "dnit_snv_removidos_3118601"

    nomes_simples = _nomes_camadas("rede")
    assert nomes_simples["links"] == "rede"
    assert nomes_simples["nos"] == "rede_nos"
    assert nomes_simples["problemas"] == "rede_problemas"
    assert nomes_simples["removidos"] == "rede_removidos"


def test_montar_rede_4_feicoes(qgis_app):
    """Testa montar_rede a partir de camada em memória com 4 feições:

    1. Uma feição PLA (planejada) -> deve ir para removidos com motivo=planejado;
    2. Uma feição com junção em T a ~5 m (MultiLineString com barra e haste);
    3. e 4. Duas feições coincidentes -> colapsam em 1 arco.
    """
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    layer = QgsVectorLayer("MultiLineString?crs=EPSG:4674", "teste_rede", "memory")
    dp = layer.dataProvider()
    dp.addAttributes([
        QgsField("codigo", qgis_compat.field_type("string")),
        QgsField("ds_superfi", qgis_compat.field_type("string")),
    ])
    layer.updateFields()

    # 5 m em graus lat: ~ 5.0 / 111320.0
    d5m = 5.0 / 111320.0

    layer.startEditing()

    # Feição 1: PLA (trecho planejado que deve ser excluído)
    f1 = QgsFeature(layer.fields())
    f1.setGeometry(QgsGeometry.fromWkt("MULTILINESTRING((0.0 0.05, 0.001 0.05))"))
    f1["codigo"] = "BR-116"
    f1["ds_superfi"] = "PLA"
    layer.addFeature(f1)

    # Feição 2: Um T a 5 m (barra horizontal no eixo y=0 e haste vertical a 5 m)
    f2 = QgsFeature(layer.fields())
    f2.setGeometry(QgsGeometry.fromWkt(
        f"MULTILINESTRING((0.0 0.0, 0.001 0.0), (0.0005 {d5m}, 0.0005 0.001))"
    ))
    f2["codigo"] = "BR-040"
    f2["ds_superfi"] = "PAV"
    layer.addFeature(f2)

    # Feição 3: Linha coincidente 1
    f3 = QgsFeature(layer.fields())
    f3.setGeometry(QgsGeometry.fromWkt("MULTILINESTRING((0.01 0.01, 0.02 0.01))"))
    f3["codigo"] = "BR-381"
    f3["ds_superfi"] = "PAV"
    layer.addFeature(f3)

    # Feição 4: Linha coincidente 2 (mesma geometria da Feição 3)
    f4 = QgsFeature(layer.fields())
    f4.setGeometry(QgsGeometry.fromWkt("MULTILINESTRING((0.01 0.01, 0.02 0.01))"))
    f4["codigo"] = "BR-262"
    f4["ds_superfi"] = "PAV"
    layer.addFeature(f4)

    layer.commitChanges()
    assert layer.featureCount() == 4

    cfg_rede = {
        "tipo": "rodoviaria",
        "excluir": {"campo": "ds_superfi", "valores": ["PLA"]},
    }

    resultado = montar_rede(layer, cfg_rede, None, "dnit_snv_3118601")

    # 1. Conferir que links preserva campos originais e acrescenta os do D11
    links = resultado["links"]
    assert links is not None and links.isValid()
    nomes_campos_links = links.fields().names()
    assert "codigo" in nomes_campos_links
    assert "ds_superfi" in nomes_campos_links
    d11_esperados = [
        "arc_id",
        "from_node",
        "to_node",
        "comprimento_m",
        "componente",
        "componente_tam",
        "coincidentes",
    ]
    for campo in d11_esperados:
        assert campo in nomes_campos_links

    # 2. Conferir que a PLA está na camada removidos com motivo=planejado
    removidos = resultado["removidos"]
    assert removidos is not None and removidos.isValid()
    assert removidos.featureCount() == 1
    feat_rem = next(removidos.getFeatures())
    assert feat_rem["ds_superfi"] == "PLA"
    assert feat_rem["codigo"] == "BR-116"
    assert feat_rem["motivo"] == "planejado"

    # 3. Conferir que a problemas tem ponta_conectada e coincidente_colapsado
    # com severidade=corrigido e rede="rodoviaria"
    problemas = resultado["problemas"]
    assert problemas is not None and problemas.isValid()
    probs = list(problemas.getFeatures())

    pontas_conectadas = [
        p for p in probs
        if p["tipo"] == "ponta_conectada"
        and p["severidade"] == "corrigido"
        and p["rede"] == "rodoviaria"
    ]
    assert len(pontas_conectadas) >= 1

    coincidentes_colapsados = [
        p for p in probs
        if p["tipo"] == "coincidente_colapsado"
        and p["severidade"] == "corrigido"
        and p["rede"] == "rodoviaria"
    ]
    assert len(coincidentes_colapsados) >= 1

    # 4. Conferir que a nós tem grau correto
    nos = resultado["nos"]
    assert nos is not None and nos.isValid()
    graus = {n["node_id"]: n["grau"] for n in nos.getFeatures()}
    # O nó da junção em T deve ter grau 3 (2 arcos da linha alvo + 1 arco da haste incidente)
    assert 3 in graus.values()
    # As pontas soltas têm grau 1
    assert 1 in graus.values()

    # Relatório com contagens
    rel = resultado["relatorio"]
    assert rel["ponta_conectada"] >= 1
    assert rel["coincidente_colapsado"] >= 1
    assert rel["removidos"] == 1


def test_montar_rede_sem_removidos(qgis_app):
    """Quando nenhuma feição coincide com o critério excluir, removidos sai None."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    layer = QgsVectorLayer("LineString?crs=EPSG:4674&field=ds_superfi:string", "teste", "memory")
    layer.startEditing()
    f = QgsFeature(layer.fields())
    f.setGeometry(QgsGeometry.fromWkt("LINESTRING(0 0, 1 1)"))
    f["ds_superfi"] = "PAV"
    layer.addFeature(f)
    layer.commitChanges()

    cfg_rede = {
        "tipo": "rodoviaria",
        "excluir": {"campo": "ds_superfi", "valores": ["PLA"]},
    }
    resultado = montar_rede(layer, cfg_rede, None, "minha_rede")
    assert resultado["removidos"] is None
    assert resultado["links"].featureCount() == 1
    assert resultado["relatorio"]["removidos"] == 0


def test_montar_rede_com_poligono_geometria(qgis_app):
    """Testa montar_rede passando polígono explícito como QgsGeometry."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    layer = QgsVectorLayer("LineString?crs=EPSG:4674&field=ds_superfi:string", "teste", "memory")
    layer.startEditing()
    f = QgsFeature(layer.fields())
    f.setGeometry(QgsGeometry.fromWkt("LINESTRING(0.01 0.01, 0.02 0.01)"))
    f["ds_superfi"] = "PAV"
    layer.addFeature(f)
    layer.commitChanges()

    poligono = QgsGeometry.fromWkt("POLYGON((0 0, 0.1 0, 0.1 0.1, 0 0.1, 0 0))")
    resultado = montar_rede(layer, {"tipo": "ferroviaria"}, poligono, "ferrovia_teste")

    assert resultado["links"].isValid()
    assert resultado["nos"].isValid()
    assert resultado["problemas"].isValid()


def test_montar_rede_com_poligono_camada(qgis_app):
    """Testa montar_rede passando polígono como QgsVectorLayer."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    layer = QgsVectorLayer("LineString?crs=EPSG:4674&field=ds_superfi:string", "teste", "memory")
    layer.startEditing()
    f = QgsFeature(layer.fields())
    f.setGeometry(QgsGeometry.fromWkt("LINESTRING(0.01 0.01, 0.02 0.01)"))
    f["ds_superfi"] = "PAV"
    layer.addFeature(f)
    layer.commitChanges()

    poly_layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "poligono_teste", "memory")
    poly_layer.startEditing()
    pf = QgsFeature(poly_layer.fields())
    pf.setGeometry(QgsGeometry.fromWkt("POLYGON((0 0, 0.1 0, 0.1 0.1, 0 0.1, 0 0))"))
    poly_layer.addFeature(pf)
    poly_layer.commitChanges()

    resultado = montar_rede(layer, {"tipo": "ferroviaria"}, poly_layer, "ferrovia_camada_teste")

    assert resultado["links"].isValid()
    assert resultado["nos"].isValid()
    assert resultado["problemas"].isValid()


# -----------------------------------------------------------------------------
# Testes de Duplicidade Federal x Estadual (D13)
# -----------------------------------------------------------------------------

def _m(x_m: float, y_m: float, lon0: float = -44.0, lat0: float = -20.0) -> Tuple[float, float]:
    """Converte deslocamentos métricos (x, y) em coordenadas (lon, lat) EPSG:4674 em MG."""
    r = 6371000.0
    phi0 = math.radians(lat0)
    lon = lon0 + math.degrees(x_m / (r * math.cos(phi0)))
    lat = lat0 + math.degrees(y_m / r)
    return (lon, lat)


def _cria_layer(nome, campos, feicoes):
    layer = QgsVectorLayer("LineString?crs=EPSG:4674", nome, "memory")
    dp = layer.dataProvider()
    dp.addAttributes([QgsField(n, qgis_compat.field_type(t)) for n, t in campos])
    layer.updateFields()
    layer.startEditing()
    for wkt, attrs in feicoes:
        f = QgsFeature(layer.fields())
        f.setGeometry(QgsGeometry.fromWkt(wkt))
        for k, v in attrs.items():
            f[k] = v
        layer.addFeature(f)
    layer.commitChanges()
    return layer


def test_constantes_d13():
    """Valida as constantes e limiares do D13."""
    assert TOL_DUP_M == 50.0
    assert LIMIAR_TOQUE_M == 100.0
    assert LIMIAR_SOBREPOSICAO_SEM_ATRIBUTO_M == 200.0
    assert LIMIAR_RESTO_M == 50.0


def test_duplicidade_mesma_br_sai_inteira(qgis_app):
    """Estadual Federal sobre o DNIT com a mesma BR -> sai inteira para removidos."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    p0 = _m(0, 0)
    p1000 = _m(1000, 0)
    fed_campos = [("codigo", "string"), ("ds_superfi", "string"), ("ds_coinc", "string")]
    est_campos = [("jurisdicao", "string"), ("rodovia", "string")]

    l_fed = _cria_layer(
        "dnit_snv_3118601",
        fed_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"codigo": "BR-040", "ds_superfi": "PAV", "ds_coinc": ""})],
    )
    l_est = _cria_layer(
        "der_mg_3118601",
        est_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"jurisdicao": "Federal", "rodovia": "BR-040"})],
    )
    cfg_dup = {"campo_jurisdicao": "jurisdicao", "valor_federal": "Federal", "campo_br": "rodovia"}
    cfg_fed = {"tipo": "rodoviaria", "excluir": {"campo": "ds_superfi", "valores": ["PLA"]}}

    limpa, rem, prob, rel = remove_duplicidade_federal(l_est, l_fed, cfg_dup, cfg_fed)

    assert limpa.featureCount() == 0
    assert rem is not None and rem.featureCount() == 1
    f_rem = next(rem.getFeatures())
    assert f_rem["motivo"] == "duplicado_federal"
    assert f_rem["rodovia"] == "BR-040"
    assert prob is None
    assert rel["removidos"] == 1
    assert rel["mantidos"] == 0
    assert rel["problemas"] == 0


def test_duplicidade_60_pct_sobreposto_corta_e_resto_fica(qgis_app):
    """Estadual Federal com 60 % sobreposto -> sai só a parte sobreposta e o resto fica."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    p0 = _m(0, 0)
    p1000 = _m(1000, 0)
    p400 = _m(400, 0)
    p1400 = _m(1400, 0)
    fed_campos = [("codigo", "string"), ("ds_superfi", "string"), ("ds_coinc", "string")]
    est_campos = [("jurisdicao", "string"), ("rodovia", "string")]

    l_fed = _cria_layer(
        "dnit_snv_3118601",
        fed_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"codigo": "BR-040", "ds_superfi": "PAV", "ds_coinc": ""})],
    )
    l_est = _cria_layer(
        "der_mg_3118601",
        est_campos,
        [(f"LINESTRING({p400[0]} {p400[1]}, {p1400[0]} {p1400[1]})", {"jurisdicao": "Federal", "rodovia": "BR-040"})],
    )
    cfg_dup = {"campo_jurisdicao": "jurisdicao", "valor_federal": "Federal", "campo_br": "rodovia"}
    cfg_fed = {"tipo": "rodoviaria", "excluir": {"campo": "ds_superfi", "valores": ["PLA"]}}

    limpa, rem, prob, rel = remove_duplicidade_federal(l_est, l_fed, cfg_dup, cfg_fed)

    assert limpa.featureCount() == 1
    assert rem is not None and rem.featureCount() == 1
    assert prob is None
    assert rel["removidos"] == 1
    assert rel["mantidos"] == 1
    assert rel["cortados"] == 1

    d = QgsDistanceArea()
    d.setEllipsoid("GRS80")
    f_limpa = next(limpa.getFeatures())
    f_rem = next(rem.getFeatures())
    assert 390.0 < d.measureLength(f_limpa.geometry()) < 410.0
    assert 590.0 < d.measureLength(f_rem.geometry()) < 610.0
    assert f_rem["motivo"] == "duplicado_federal"
    assert f_limpa["rodovia"] == "BR-040"


def test_duplicidade_federal_sobre_pla_fica_e_problema(qgis_app):
    """Estadual Federal sobre um federal PLA -> fica + federal_sem_par."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    p0 = _m(0, 0)
    p1000 = _m(1000, 0)
    fed_campos = [("codigo", "string"), ("ds_superfi", "string"), ("ds_coinc", "string")]
    est_campos = [("jurisdicao", "string"), ("rodovia", "string")]

    l_fed = _cria_layer(
        "dnit_snv_3118601",
        fed_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"codigo": "BR-040", "ds_superfi": "PLA", "ds_coinc": ""})],
    )
    l_est = _cria_layer(
        "der_mg_3118601",
        est_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"jurisdicao": "Federal", "rodovia": "BR-040"})],
    )
    cfg_dup = {"campo_jurisdicao": "jurisdicao", "valor_federal": "Federal", "campo_br": "rodovia"}
    cfg_fed = {"tipo": "rodoviaria", "excluir": {"campo": "ds_superfi", "valores": ["PLA"]}}

    limpa, rem, prob, rel = remove_duplicidade_federal(l_est, l_fed, cfg_dup, cfg_fed)

    assert limpa.featureCount() == 1
    assert rem is None
    assert prob is not None and prob.featureCount() == 1
    p = next(prob.getFeatures())
    assert p["tipo"] == "federal_sem_par"
    assert p["rede"] == "rodoviaria"
    assert rel["federal_sem_par"] == 1
    assert rel["removidos"] == 0


def test_duplicidade_federal_br_divergente_fica_e_problema(qgis_app):
    """Estadual Federal sobreposta com BR diferente -> fica + federal_br_divergente."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    p0 = _m(0, 0)
    p1000 = _m(1000, 0)
    fed_campos = [("codigo", "string"), ("ds_superfi", "string"), ("ds_coinc", "string")]
    est_campos = [("jurisdicao", "string"), ("rodovia", "string")]

    l_fed = _cria_layer(
        "dnit_snv_3118601",
        fed_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"codigo": "BR-040", "ds_superfi": "PAV", "ds_coinc": ""})],
    )
    l_est = _cria_layer(
        "der_mg_3118601",
        est_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"jurisdicao": "Federal", "rodovia": "BR-381"})],
    )
    cfg_dup = {"campo_jurisdicao": "jurisdicao", "valor_federal": "Federal", "campo_br": "rodovia"}
    cfg_fed = {"tipo": "rodoviaria", "excluir": {"campo": "ds_superfi", "valores": ["PLA"]}}

    limpa, rem, prob, rel = remove_duplicidade_federal(l_est, l_fed, cfg_dup, cfg_fed)

    assert limpa.featureCount() == 1
    assert rem is None
    assert prob is not None and prob.featureCount() == 1
    p = next(prob.getFeatures())
    assert p["tipo"] == "federal_br_divergente"
    assert p["rede"] == "rodoviaria"
    assert rel["federal_br_divergente"] == 1
    assert rel["removidos"] == 0


def test_duplicidade_estadual_sobreposta_300m_fica_e_problema(qgis_app):
    """Estadual Estadual sobreposta 300 m -> fica + sobreposicao_sem_atributo."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    p0 = _m(0, 0)
    p1000 = _m(1000, 0)
    p300 = _m(300, 0)
    fed_campos = [("codigo", "string"), ("ds_superfi", "string"), ("ds_coinc", "string")]
    est_campos = [("jurisdicao", "string"), ("rodovia", "string")]

    l_fed = _cria_layer(
        "dnit_snv_3118601",
        fed_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"codigo": "BR-040", "ds_superfi": "PAV", "ds_coinc": ""})],
    )
    l_est = _cria_layer(
        "der_mg_3118601",
        est_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p300[0]} {p300[1]})", {"jurisdicao": "Estadual", "rodovia": "MG-010"})],
    )
    cfg_dup = {"campo_jurisdicao": "jurisdicao", "valor_federal": "Federal", "campo_br": "rodovia"}
    cfg_fed = {"tipo": "rodoviaria", "excluir": {"campo": "ds_superfi", "valores": ["PLA"]}}

    limpa, rem, prob, rel = remove_duplicidade_federal(l_est, l_fed, cfg_dup, cfg_fed)

    assert limpa.featureCount() == 1
    assert rem is None
    assert prob is not None and prob.featureCount() == 1
    p = next(prob.getFeatures())
    assert p["tipo"] == "sobreposicao_sem_atributo"
    assert p["rede"] == "rodoviaria"
    assert rel["sobreposicao_sem_atributo"] == 1
    assert rel["removidos"] == 0


def test_duplicidade_toque_entroncamento_menor_100m_nada(qgis_app):
    """Toque só no entroncamento (< 100 m) -> nada (mantém sem problema e sem remoção)."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    p0 = _m(0, 0)
    p1000 = _m(1000, 0)
    p500 = _m(500, 0)
    p500_500 = _m(500, 500)
    fed_campos = [("codigo", "string"), ("ds_superfi", "string"), ("ds_coinc", "string")]
    est_campos = [("jurisdicao", "string"), ("rodovia", "string")]

    l_fed = _cria_layer(
        "dnit_snv_3118601",
        fed_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"codigo": "BR-040", "ds_superfi": "PAV", "ds_coinc": ""})],
    )
    l_est = _cria_layer(
        "der_mg_3118601",
        est_campos,
        [(f"LINESTRING({p500[0]} {p500[1]}, {p500_500[0]} {p500_500[1]})", {"jurisdicao": "Estadual", "rodovia": "MG-010"})],
    )
    cfg_dup = {"campo_jurisdicao": "jurisdicao", "valor_federal": "Federal", "campo_br": "rodovia"}
    cfg_fed = {"tipo": "rodoviaria", "excluir": {"campo": "ds_superfi", "valores": ["PLA"]}}

    limpa, rem, prob, rel = remove_duplicidade_federal(l_est, l_fed, cfg_dup, cfg_fed)

    assert limpa.featureCount() == 1
    assert rem is None
    assert prob is None
    assert rel["removidos"] == 0
    assert rel["problemas"] == 0


def test_duplicidade_campo_br_ausente_decide_por_jurisdicao(qgis_app):
    """Campo_br ausente -> decide só por jurisdição e sobreposição."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    p0 = _m(0, 0)
    p1000 = _m(1000, 0)
    fed_campos = [("codigo", "string"), ("ds_superfi", "string"), ("ds_coinc", "string")]
    est_campos = [("jurisdicao", "string")]

    l_fed = _cria_layer(
        "dnit_snv_3118601",
        fed_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"codigo": "BR-040", "ds_superfi": "PAV", "ds_coinc": ""})],
    )
    l_est = _cria_layer(
        "der_mg_3118601",
        est_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"jurisdicao": "Federal"})],
    )
    cfg_dup = {"campo_jurisdicao": "jurisdicao", "valor_federal": "Federal"}
    cfg_fed = {"tipo": "rodoviaria", "excluir": {"campo": "ds_superfi", "valores": ["PLA"]}}

    limpa, rem, prob, rel = remove_duplicidade_federal(l_est, l_fed, cfg_dup, cfg_fed)

    assert limpa.featureCount() == 0
    assert rem is not None and rem.featureCount() == 1
    assert prob is None
    assert rel["removidos"] == 1


def test_duplicidade_federal_coincidente_aceita_br_coincidente(qgis_app):
    """Federal coincidente (ds_coinc '040…;135…') aceita a BR 135."""
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")

    p0 = _m(0, 0)
    p1000 = _m(1000, 0)
    fed_campos = [("codigo", "string"), ("ds_superfi", "string"), ("ds_coinc", "string")]
    est_campos = [("jurisdicao", "string"), ("rodovia", "string")]

    l_fed = _cria_layer(
        "dnit_snv_3118601",
        fed_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"codigo": "BR-040", "ds_superfi": "PAV", "ds_coinc": "040…;135…"})],
    )
    l_est = _cria_layer(
        "der_mg_3118601",
        est_campos,
        [(f"LINESTRING({p0[0]} {p0[1]}, {p1000[0]} {p1000[1]})", {"jurisdicao": "Federal", "rodovia": "BR-135"})],
    )
    cfg_dup = {"campo_jurisdicao": "jurisdicao", "valor_federal": "Federal", "campo_br": "rodovia"}
    cfg_fed = {"tipo": "rodoviaria", "excluir": {"campo": "ds_superfi", "valores": ["PLA"]}}

    limpa, rem, prob, rel = remove_duplicidade_federal(l_est, l_fed, cfg_dup, cfg_fed)

    assert limpa.featureCount() == 0
    assert rem is not None and rem.featureCount() == 1
    assert prob is None
    assert rel["removidos"] == 1

