# -*- coding: utf-8 -*-
import sys
import types
import pytest

from unittest.mock import MagicMock
from gisbr.core.recorte import Recorte, camada_do_recorte

pytest.importorskip("qgis.core")

def test_recorte_municipio():
    r = Recorte.de_municipio("3106200", "Contagem")
    assert r.tipo == "municipio"
    assert r.sufixo == "3106200"
    assert r.rotulo == "Contagem"
    assert r.e_rm is False
    assert r.codes_por_uf() == {"31": ["3106200"]}
    assert r.uf_por_code == {"31": ["3106200"]}
    assert r.codes == ["3106200"]

def test_recorte_rm():
    r = Recorte.de_rm("04501", "Região Metropolitana de Belo Horizonte", ["3106200", "3106705"])
    assert r.tipo == "rm"
    assert r.sufixo == "rm04501"
    assert r.rotulo == "RM de Belo Horizonte"
    assert r.e_rm is True
    assert r.codes_por_uf() == {"31": ["3106200", "3106705"]}

def test_recorte_multiplas_ufs():
    r = Recorte.de_rm("ride1", "Região Metropolitana de Algum Lugar", ["5300108", "5200000", "3100000"])
    assert r.codes_por_uf() == {
        "53": ["5300108"],
        "52": ["5200000"],
        "31": ["3100000"]
    }


def test_camada_do_recorte_uma_uf(monkeypatch):
    layer_mock = MagicMock()
    layer_mock.featureCount.return_value = 1
    
    run_calls = []

    def mock_run(alg, params, **kwargs):
        run_calls.append((alg, params))
        if alg == "gisbr:read_municipality":
            return {"OUTPUT": "layer_mg"}
        if alg == "native:extractbyexpression":
            return {"OUTPUT": layer_mock}
        return {}

    mock_proc = types.ModuleType("processing")
    mock_proc.run = mock_run
    monkeypatch.setitem(sys.modules, "processing", mock_proc)

    r = Recorte.de_municipio("3106200", "Contagem")
    feedback = MagicMock()
    
    res = camada_do_recorte(r, feedback=feedback)
    
    assert res == layer_mock
    
    algs = [call[0] for call in run_calls]
    assert "gisbr:read_municipality" in algs
    assert "native:extractbyexpression" in algs
    assert "native:mergevectorlayers" not in algs
    
    for alg, params in run_calls:
        if alg == "gisbr:read_municipality":
            assert params["CODE"] == "31"
        if alg == "native:extractbyexpression":
            assert params["INPUT"] == "layer_mg"
            assert params["EXPRESSION"] == '"code_muni" IN (\'3106200\')'


def test_camada_do_recorte_multiplas_ufs(monkeypatch):
    layer_mock = MagicMock()
    layer_mock.featureCount.return_value = 2
    
    run_calls = []

    def mock_run(alg, params, **kwargs):
        run_calls.append((alg, params))
        if alg == "gisbr:read_municipality":
            dummy_layer = MagicMock()
            dummy_layer.crs.return_value = "CRS_MOCK"
            return {"OUTPUT": dummy_layer}
        if alg == "native:mergevectorlayers":
            return {"OUTPUT": "merged_layer"}
        if alg == "native:extractbyexpression":
            return {"OUTPUT": layer_mock}
        return {}

    mock_proc = types.ModuleType("processing")
    mock_proc.run = mock_run
    monkeypatch.setitem(sys.modules, "processing", mock_proc)

    r = Recorte.de_rm("ride1", "RIDE", ["5300108", "5200000"])
    res = camada_do_recorte(r)
    
    assert res == layer_mock
    
    algs = [call[0] for call in run_calls]
    assert algs.count("gisbr:read_municipality") == 2
    assert "native:mergevectorlayers" in algs
    assert "native:extractbyexpression" in algs

def test_camada_do_recorte_feature_count_menor(monkeypatch):
    layer_mock = MagicMock()
    layer_mock.featureCount.return_value = 1
    
    def mock_run(alg, params, **kwargs):
        if alg == "gisbr:read_municipality":
            return {"OUTPUT": "layer"}
        if alg == "native:extractbyexpression":
            return {"OUTPUT": layer_mock}

    mock_proc = types.ModuleType("processing")
    mock_proc.run = mock_run
    monkeypatch.setitem(sys.modules, "processing", mock_proc)

    r = Recorte.de_rm("teste", "Teste RM", ["3100000", "3100001"])
    feedback = MagicMock()
    
    res = camada_do_recorte(r, feedback)
    
    assert res == layer_mock
    feedback.pushInfo.assert_called_once()
    assert "Aviso: camada extraída para Teste RM tem 1 feições" in feedback.pushInfo.call_args[0][0]

def test_camada_do_recorte_camada_vazia(monkeypatch):
    layer_mock = MagicMock()
    layer_mock.featureCount.return_value = 0
    
    def mock_run(alg, params, **kwargs):
        if alg == "gisbr:read_municipality":
            return {"OUTPUT": "layer"}
        if alg == "native:extractbyexpression":
            return {"OUTPUT": layer_mock}

    mock_proc = types.ModuleType("processing")
    mock_proc.run = mock_run
    monkeypatch.setitem(sys.modules, "processing", mock_proc)

    r = Recorte.de_municipio("3100000", "Vazio")
    feedback = MagicMock()
    
    res = camada_do_recorte(r, feedback)
    
    assert res is None
    feedback.reportError.assert_called_once()
