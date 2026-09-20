# -*- coding: utf-8 -*-
"""Testes de `OsmNetworkTask`.

Chama `run()` diretamente (sem `QgsApplication.taskManager()`), com
`compute_osm_network` monkeypatchado — exige QGIS só por causa de `QgsTask`
(pyqtSignal/QObject); pula se `qgis_app` vier `None`.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qgis_app")


def _skip_sem_qgis(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")


def test_run_caminho_feliz_devolve_true_e_preenche_dados(qgis_app, monkeypatch):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_task

    dados_fake = {"raw_cache": None, "arcos_todos": [1], "arcos": [1],
                  "diag": {}, "nodes_dict": {},
                  "problemas": [], "metadata": {"code_muni": "3106200"}}
    monkeypatch.setattr(osm_task, "compute_osm_network", lambda *a, **k: dados_fake)

    task = osm_task.OsmNetworkTask("teste", "3106200", "Belo Horizonte", (0, 0, 1, 1), None)
    assert task.run() is True
    assert task.dados is dados_fake
    assert task.erro is None


def test_run_devolve_false_quando_compute_devolve_erro(qgis_app, monkeypatch):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_task

    dados_fake = {"raw_cache": None, "arcos_todos": None, "arcos": None,
                  "diag": None, "nodes_dict": None,
                  "problemas": None, "metadata": {"erro": "Erro no Overpass: timeout"}}
    monkeypatch.setattr(osm_task, "compute_osm_network", lambda *a, **k: dados_fake)

    task = osm_task.OsmNetworkTask("teste", "3106200", "Belo Horizonte", (0, 0, 1, 1), None)
    assert task.run() is False
    assert task.dados is None
    assert task.erro == "Erro no Overpass: timeout"
    assert task.sem_vias is False


def test_run_marca_sem_vias_quando_payload_sem_ways(qgis_app, monkeypatch):
    """Paridade com o caminho síncrono (`carregar_fontes`): 'nenhuma via no
    bbox' precisa ficar marcado (`self.sem_vias`), não só como erro genérico
    — é o painel quem decide, com esse dado, logar SKIPPED em vez de FAILED."""
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_task

    dados_fake = {"raw_cache": "/tmp/x.json", "arcos_todos": None, "arcos": None,
                  "diag": None, "nodes_dict": None,
                  "problemas": None,
                  "metadata": {"erro": "nenhum way com highway encontrado no bbox", "sem_vias": True}}
    monkeypatch.setattr(osm_task, "compute_osm_network", lambda *a, **k: dados_fake)

    task = osm_task.OsmNetworkTask("teste", "3106200", "Belo Horizonte", (0, 0, 1, 1), None)
    assert task.run() is False
    assert task.dados is None
    assert task.sem_vias is True
    assert task.erro == "nenhum way com highway encontrado no bbox"


def test_run_emite_sinal_mensagem(qgis_app, monkeypatch):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_task

    def compute_fake(code_muni, nome_muni, bbox, mun_geom, cache_dir=None, force=False, feedback=None):
        feedback.pushInfo("OSM: mensagem de teste")
        return {"raw_cache": None, "arcos_todos": [1], "arcos": [1],
                "diag": {}, "nodes_dict": {},
                "problemas": [], "metadata": {}}

    monkeypatch.setattr(osm_task, "compute_osm_network", compute_fake)

    task = osm_task.OsmNetworkTask("teste", "3106200", "Belo Horizonte", (0, 0, 1, 1), None)
    coletadas = []
    task.mensagem.connect(coletadas.append)

    assert task.run() is True
    assert "OSM: mensagem de teste" in coletadas


def test_cancel_antes_do_run_devolve_false_e_nao_chama_compute(qgis_app, monkeypatch):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_task

    chamadas = []
    monkeypatch.setattr(osm_task, "compute_osm_network", lambda *a, **k: chamadas.append(1))

    task = osm_task.OsmNetworkTask("teste", "3106200", "Belo Horizonte", (0, 0, 1, 1), None)
    task.cancel()

    assert task.run() is False
    assert chamadas == []
    assert task.dados is None


def test_finished_emite_concluida_com_dados_ou_none(qgis_app, monkeypatch):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_task

    task = osm_task.OsmNetworkTask("teste", "3106200", "Belo Horizonte", (0, 0, 1, 1), None)
    recebidos = []
    task.concluida.connect(recebidos.append)

    task.dados = {"algo": 1}
    task.finished(True)
    assert recebidos == [{"algo": 1}]

    task.dados = {"algo": 1}
    task.finished(False)
    assert recebidos == [{"algo": 1}, None]
