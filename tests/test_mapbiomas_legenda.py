# -*- coding: utf-8 -*-
"""Testes unitários para a legenda e renderizador paletado do MapBiomas Coleção 9.

Testa a leitura do CSV sem QGIS (stdlib pura) e a criação do QgsPalettedRasterRenderer.
"""

import re
import pytest

from gisbr.core.mapbiomas_legenda import (
    carregar_classes_mapbiomas,
    extrair_codigos_presentes_raster,
    obter_classes_presentes,
    criar_renderizador_paletado,
)


def test_carregar_classes_mapbiomas_csv_lido():
    classes = carregar_classes_mapbiomas()
    assert isinstance(classes, dict)
    assert len(classes) == 41

    # Verificar codigos de destaque esperados
    codigos_esperados = [1, 3, 4, 15, 19, 23, 24, 30, 33, 91]
    for cod in codigos_esperados:
        assert cod in classes
        assert "rotulo_pt" in classes[cod]
        assert "rotulo_en" in classes[cod]
        assert "cor_hex" in classes[cod]

    assert classes[15]["rotulo_pt"] == "Pastagem"
    assert classes[23]["rotulo_pt"] == "Praia, Duna e Areal"
    assert classes[24]["rotulo_pt"] == "Área Urbanizada"
    assert classes[30]["rotulo_pt"] == "Mineração"
    assert classes[33]["rotulo_pt"] == "Rio, Lago e Oceano"


def test_classes_mapbiomas_cores_hex_validas():
    classes = carregar_classes_mapbiomas()
    hex_pattern = re.compile(r"^#[A-Fa-f0-9]{6}$")

    for codigo, info in classes.items():
        cor = info["cor_hex"]
        assert hex_pattern.match(cor), f"Codigo {codigo} possui cor hex invalida: {cor}"


def test_classes_mapbiomas_rotulos_nao_vazios():
    classes = carregar_classes_mapbiomas()
    for codigo, info in classes.items():
        assert info["rotulo_pt"].strip(), f"Codigo {codigo} possui rotulo PT vazio"
        assert info["rotulo_en"].strip(), f"Codigo {codigo} possui rotulo EN vazio"


def test_obter_classes_presentes_filtragem():
    presentes = obter_classes_presentes({24, 3, 15})
    assert len(presentes) == 3
    # Deve vir ordenado por codigo
    assert [p["codigo"] for p in presentes] == [3, 15, 24]
    assert presentes[0]["rotulo"] == "Formação Florestal"
    assert presentes[1]["rotulo"] == "Pastagem"
    assert presentes[2]["rotulo"] == "Área Urbanizada"


def test_obter_classes_presentes_idioma_en():
    presentes = obter_classes_presentes({15, 24}, lang="en")
    assert len(presentes) == 2
    assert presentes[0]["rotulo"] == "Pasture"
    assert presentes[1]["rotulo"] == "Urban Area"


def test_obter_classes_presentes_codigos_desconhecidos_ignorados():
    presentes = obter_classes_presentes({15, 999, 0})
    assert len(presentes) == 1
    assert presentes[0]["codigo"] == 15


def test_criar_renderizador_paletado_qgis(qgis_app):
    qgis_core = pytest.importorskip("qgis.core")
    from qgis.core import QgsPalettedRasterRenderer, QgsRasterLayer

    layer = QgsRasterLayer("type=memory", "test_raster")
    renderer = criar_renderizador_paletado(layer, codigos_presentes={3, 15, 24}, lang="pt")
    assert isinstance(renderer, QgsPalettedRasterRenderer)
    assert len(renderer.classes()) == 3
