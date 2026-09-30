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


def test_camada_do_recorte_sem_extra_params_passa_output(monkeypatch):
    layer_mock = MagicMock()
    layer_mock.featureCount.return_value = 1

    run_calls = []

    def mock_run(alg, params, **kwargs):
        run_calls.append((alg, params))
        if alg.startswith("gisbr:"):
            if "OUTPUT" not in params:
                raise ValueError(f"Parâmetro obrigatório 'OUTPUT' não fornecido para {alg}")
        if alg == "gisbr:read_municipality":
            return {"OUTPUT": "layer_mg"}
        if alg == "native:extractbyexpression":
            return {"OUTPUT": layer_mock}
        return {}

    mock_proc = types.ModuleType("processing")
    mock_proc.run = mock_run
    monkeypatch.setitem(sys.modules, "processing", mock_proc)

    r = Recorte.de_municipio("3106200", "Contagem")
    res = camada_do_recorte(r)

    assert res is not None
    gisbr_calls = [params for alg, params in run_calls if alg == "gisbr:read_municipality"]
    assert len(gisbr_calls) == 1
    assert gisbr_calls[0].get("OUTPUT") == "TEMPORARY_OUTPUT"
    assert gisbr_calls[0].get("SIMPLIFIED") is True



def test_recorte_generalizado():
    # Regressão município
    rmun = Recorte.de_municipio("3106200", "Contagem")
    assert rmun.sufixo == "3106200"
    assert rmun.nome_camada_limite is None
    assert rmun.escala == 0
    assert rmun.siglas_uf == ["MG"]
    assert not rmun.e_agregado

    # Regressão RM
    rrm = Recorte.de_rm("06301", "Região Metropolitana da Serra", ["3106200"])
    assert rrm.sufixo == "rm06301"
    assert rrm.nome_camada_limite == "rm_06301"
    assert rrm.escala == 1
    assert rrm.siglas_uf == ["MG"]
    assert rrm.e_agregado
    assert rrm.rotulo == "RM da Serra"

    # Novos tipos do D3: id IBGE em micro/meso/macro, sigla em uf
    rmicro = Recorte.de_agregado("micro", "31030", "Microrregião de Belo Horizonte", ["3118601"])
    assert rmicro.sufixo == "micro31030"
    assert rmicro.nome_camada_limite == "micro_31030"
    assert rmicro.escala == 1

    rmeso = Recorte.de_agregado("meso", "3107", "Mesorregião Metropolitana de Belo Horizonte", ["3118601"])
    assert rmeso.sufixo == "meso3107"
    assert rmeso.nome_camada_limite == "meso_3107"
    assert rmeso.escala == 2

    ruf = Recorte.de_agregado("uf", "MG", "Minas Gerais (MG)", ["3106200"])
    assert ruf.sufixo == "ufmg"
    assert ruf.nome_camada_limite == "uf_mg"
    assert ruf.escala == 3
    assert ruf.siglas_uf == ["MG"]

    rmacro = Recorte.de_agregado("macro", "3", "Região Sudeste", ["3106200", "3200000", "3300000", "3500000"])
    assert rmacro.sufixo == "macro3"
    assert rmacro.nome_camada_limite == "macro_3"
    assert rmacro.escala == 4
    assert rmacro.siglas_uf == ["ES", "MG", "RJ", "SP"]

    # Agregado desconhecido: default regional (2)
    rrpi = Recorte.de_agregado("rpi", "310001", "Região Imediata", ["3106200", "3550308"])
    assert rrpi.sufixo == "rpi310001"
    assert rrpi.nome_camada_limite == "rpi_310001"
    assert rrpi.escala == 2
    assert rrpi.siglas_uf == ["MG", "SP"]
    assert rrpi.e_agregado
    assert rrpi.rotulo == "Região Imediata"
