# -*- coding: utf-8 -*-
"""Testes unitários para gisbr.core.agro_pipeline (tabela_para_camada e formato largo)."""

import pytest

qgis_core = pytest.importorskip("qgis.core")
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
)

from gisbr.core import agro_pipeline, qgis_compat
from gisbr.core.agro_pipeline import (
    MAX_GEOPACKAGE_FIELD_LEN,
    normalizar_texto,
    tabela_para_camada,
)


def _dummy_muni_layer():
    """Cria uma camada de polígono sintética para representar o município."""
    pts = [
        QgsPointXY(-44.0, -20.0),
        QgsPointXY(-44.0, -19.0),
        QgsPointXY(-43.0, -19.0),
        QgsPointXY(-43.0, -20.0),
        QgsPointXY(-44.0, -20.0),
    ]
    geom = QgsGeometry.fromPolygonXY([pts])
    layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "municipio", "memory")
    layer.startEditing()
    feat = QgsFeature(layer.fields())
    feat.setGeometry(geom)
    layer.addFeature(feat)
    layer.commitChanges()
    return layer


def test_tabela_sintetica_produto_vazio_descartado(monkeypatch, qgis_app):
    """Teste principal: tabela sintética com produto 100% None (D5).

    Garante: 1 feição, campos esperados e SEM a coluna do produto vazio.
    """
    monkeypatch.setattr(
        agro_pipeline,
        "_municipio_poligono",
        lambda code, name=None: _dummy_muni_layer(),
    )

    tabela = [
        ("109", "Área plantada", "Hectares", "Soja (em grão)", "2023", 100.0),
        ("109", "Área plantada", "Hectares", "Milho (em grão)", "2023", 250.0),
        ("109", "Área plantada", "Hectares", "Algodão em caroço", "2023", None),
    ]

    layer, relatorio = tabela_para_camada(
        tabela=tabela,
        code_muni="3106200",
        nome_muni="Belo Horizonte",
        layer_name="pam_temporarias",
    )

    assert layer.isValid()
    assert layer.featureCount() == 1

    field_names = [f.name() for f in layer.fields()]
    assert "code_muni" in field_names
    assert "soja_em_grao" in field_names
    assert "milho_em_grao" in field_names
    # Produto 100% None NAO deve gerar coluna (D5)
    assert "algodao_em_caroco" not in field_names

    # Asserções no relatório
    assert relatorio["produtos_aproveitados"] == 2
    assert relatorio["produtos_descartados"] == 1
    assert relatorio["produtos_aproveitados_lista"] == ["Soja (em grão)", "Milho (em grão)"]
    assert relatorio["produtos_descartados_lista"] == ["Algodão em caroço"]

    # Atributos da feição
    feats = list(layer.getFeatures())
    feat = feats[0]
    assert feat["code_muni"] == "3106200"
    assert feat["soja_em_grao"] == 100.0
    assert feat["milho_em_grao"] == 250.0


def test_normalizacao_e_acentos():
    """Valida normalização de strings com unicodedata, minúsculas e caracteres especiais."""
    assert normalizar_texto("Feijão (em grão)") == "feijao_em_grao"
    assert normalizar_texto("Café em grão (Arábica)") == "cafe_em_grao_arabica"
    assert normalizar_texto("Cana-de-açúcar") == "cana_de_acucar"
    assert normalizar_texto("Área plantada (Hectares)") == "area_plantada_hectares"


def test_colisao_e_truncamento_geopackage(monkeypatch, qgis_app):
    """Valida truncamento a 63 caracteres e desempate determinístico em colisões."""
    monkeypatch.setattr(
        agro_pipeline,
        "_municipio_poligono",
        lambda code, name=None: _dummy_muni_layer(),
    )

    prod1 = "Produto Extremamente Longo De Teste Com Nome Identico No Inicio Para Geopackage Alfa"
    prod2 = "Produto Extremamente Longo De Teste Com Nome Identico No Inicio Para Geopackage Beta"

    tabela = [
        ("109", "Área plantada", "Hectares", prod1, "2023", 10.0),
        ("109", "Área plantada", "Hectares", prod2, "2023", 20.0),
    ]

    layer, relatorio = tabela_para_camada(
        tabela=tabela,
        code_muni="3106200",
        layer_name="test_collision",
    )

    assert layer.isValid()
    field_names = [f.name() for f in layer.fields() if f.name() != "code_muni"]
    assert len(field_names) == 2

    # Nenhum campo pode exceder 63 caracteres (limite GeoPackage)
    for fn in field_names:
        assert len(fn) <= MAX_GEOPACKAGE_FIELD_LEN

    # Os nomes devem ser distintos devido ao desempate determinístico
    assert field_names[0] != field_names[1]
    assert field_names[1].endswith("_2")


def test_multiplas_variaveis(monkeypatch, qgis_app):
    """Valida criação de campos formato largo para múltiplas variáveis (variável x produto)."""
    monkeypatch.setattr(
        agro_pipeline,
        "_municipio_poligono",
        lambda code, name=None: _dummy_muni_layer(),
    )

    tabela = [
        ("109", "Área plantada", "Hectares", "Soja (em grão)", "2023", 100.0),
        ("214", "Quantidade produzida", "Toneladas", "Soja (em grão)", "2023", 500.0),
    ]

    layer, _ = tabela_para_camada(
        tabela=tabela,
        code_muni="3106200",
        layer_name="test_multivar",
    )

    assert layer.isValid()
    field_names = [f.name() for f in layer.fields()]
    assert "area_plantada_soja_em_grao" in field_names
    assert "quantidade_produzida_soja_em_grao" in field_names

    feat = list(layer.getFeatures())[0]
    assert feat["area_plantada_soja_em_grao"] == 100.0
    assert feat["quantidade_produzida_soja_em_grao"] == 500.0


def test_poligono_ausente(monkeypatch, qgis_app):
    """Valida comportamento de erro quando o polígono municipal não é encontrado."""
    monkeypatch.setattr(
        agro_pipeline,
        "_municipio_poligono",
        lambda code, name=None: None,
    )

    tabela = [("109", "Área plantada", "Hectares", "Soja", "2023", 100.0)]

    layer, relatorio = tabela_para_camada(
        tabela=tabela,
        code_muni="9999999",
        layer_name="test_invalid",
    )

    assert not layer.isValid()
    assert hasattr(layer, "error_msg")
    assert "Nao foi possivel obter o poligono" in layer.error_msg
    assert relatorio["produtos_aproveitados"] == 0
    assert len(relatorio["avisos"]) > 0


def test_tabela_como_qgsvectorlayer(monkeypatch, qgis_app):
    """Valida aceitação de QgsVectorLayer de memória como entrada para tabela."""
    monkeypatch.setattr(
        agro_pipeline,
        "_municipio_poligono",
        lambda code, name=None: _dummy_muni_layer(),
    )

    # Cria camada vetorial de memória no formato da API IBGE Agregados
    uri = (
        "None?field=var_id:string&field=var_nome:string&field=unidade:string&"
        "field=produto:string&field=periodo:string&field=valor:double"
    )
    tab_layer = QgsVectorLayer(uri, "ibge_memory", "memory")
    tab_layer.startEditing()
    
    f1 = QgsFeature(tab_layer.fields())
    f1.setAttributes(["109", "Área plantada", "Hectares", "Café", "2023", 50.0])
    tab_layer.addFeature(f1)
    
    f2 = QgsFeature(tab_layer.fields())
    f2.setAttributes(["109", "Área plantada", "Hectares", "Laranja", "2023", None])
    tab_layer.addFeature(f2)
    
    tab_layer.commitChanges()

    layer, relatorio = tabela_para_camada(
        tabela=tab_layer,
        code_muni="3106200",
        layer_name="test_vector_input",
    )

    assert layer.isValid()
    assert layer.featureCount() == 1
    assert relatorio["produtos_aproveitados"] == 1
    assert relatorio["produtos_descartados"] == 1

    field_names = [f.name() for f in layer.fields()]
    assert "cafe" in field_names
    assert "laranja" not in field_names
