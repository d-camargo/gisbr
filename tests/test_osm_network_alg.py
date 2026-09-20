# -*- coding: utf-8 -*-
"""Testes do algoritmo `gisbr:osm_network` e de `build_osm_network_layers`
(Passos 2, 3, 4 e 6 do plano `osm_network`).

Exige QGIS (QgsGeometry, QgsProcessingContext, QgsVectorLayer) — pula se
`qgis_app` vier None (ver tests/conftest.py).
"""

import pytest

pytestmark = pytest.mark.usefixtures("qgis_app")


def _skip_sem_qgis(qgis_app):
    if qgis_app is None:
        pytest.skip("QGIS indisponivel neste ambiente")


def _municipio_fake(*args, **kwargs):
    from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer

    layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "municipio", "memory")
    layer.startEditing()
    feat = QgsFeature(layer.fields())
    feat.setGeometry(QgsGeometry.fromWkt(
        "POLYGON((-44 -20, -43.9 -20, -43.9 -19.9, -44 -19.9, -44 -20))"))
    layer.addFeature(feat)
    layer.commitChanges()
    return layer


def _payload_um_way(highway="residential", maxspeed="60"):
    tags = {"highway": highway}
    if maxspeed is not None:
        tags["maxspeed"] = maxspeed
    return {
        "elements": [
            {"type": "node", "id": 1, "lat": -19.95, "lon": -43.95},
            {"type": "node", "id": 2, "lat": -19.95, "lon": -43.94},
            {"type": "node", "id": 3, "lat": -19.94, "lon": -43.94},
            {"type": "way", "id": 100, "nodes": [1, 2, 3], "tags": tags},
        ]
    }


def _monkeypatch_overpass(monkeypatch, payload, municipio=_municipio_fake):
    from gisbr.core import osm_pipeline

    monkeypatch.setattr(osm_pipeline, "_municipio_poligono", municipio)
    monkeypatch.setattr(osm_pipeline.osm, "fetch_overpass_json", lambda *a, **k: payload)
    monkeypatch.setattr(osm_pipeline.osm, "save_overpass_cache", lambda *a, **k: None)
    monkeypatch.setattr(osm_pipeline.osm, "load_overpass_cache", lambda *a, **k: None)


# --- comprimento_m (Passo 2) -----------------------------------------------

def test_comprimento_m_arco_de_1km_fica_no_intervalo_esperado(qgis_app, monkeypatch, tmp_path):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    # ~1 km no eixo x, perto do equador (111320 m/grau, sem fator cos(lat)):
    # 1000 m / 111320 m/grau ~= 0.008983 grau
    dlon = 1000.0 / 111320.0
    payload = {
        "elements": [
            {"type": "node", "id": 1, "lat": 0.0, "lon": 0.0},
            {"type": "node", "id": 2, "lat": 0.0, "lon": dlon},
            {"type": "way", "id": 200, "nodes": [1, 2], "tags": {"highway": "residential"}},
        ]
    }

    def municipio_grande(*args, **kwargs):
        from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer
        layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "municipio", "memory")
        layer.startEditing()
        feat = QgsFeature(layer.fields())
        feat.setGeometry(QgsGeometry.fromWkt("POLYGON((-1 -1, 1 -1, 1 1, -1 1, -1 -1))"))
        layer.addFeature(feat)
        layer.commitChanges()
        return layer

    _monkeypatch_overpass(monkeypatch, payload, municipio=municipio_grande)

    resultado = osm_pipeline.build_osm_network_layers(
        "0000000", cache_dir=tmp_path)
    links = resultado["layers"]["osm_links"]
    assert links is not None and links.featureCount() == 1
    feat = next(links.getFeatures())
    assert 990.0 <= feat["comprimento_m"] <= 1010.0


# --- build_osm_network_layers monkeypatchado (Passo 1 + Passo 2) ----------

def test_build_osm_network_layers_devolve_tres_camadas_sem_tocar_disco(qgis_app, monkeypatch, tmp_path):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    _monkeypatch_overpass(monkeypatch, _payload_um_way())

    cache_dir = tmp_path / "cache_nao_deve_ganhar_gpkg"
    resultado = osm_pipeline.build_osm_network_layers(
        "3106200", cache_dir=cache_dir, feedback=None)

    metadata = resultado["metadata"]
    assert "erro" not in metadata
    layers = resultado["layers"]
    links, nodes, problemas = layers["osm_links"], layers["osm_nodes"], layers["osm_problemas"]
    assert links.featureCount() == 1
    assert nodes.featureCount() == 2
    assert problemas is not None

    campos_link = {f.name() for f in links.fields()}
    assert {"maxspeed", "velocidade_kmh", "comprimento_m"} <= campos_link

    feat = next(links.getFeatures())
    assert feat["maxspeed"] == "60"
    assert feat["velocidade_kmh"] == 60.0

    # nada gravado em disco: so o cache do Overpass (mockado, nunca chamado
    # de verdade) poderia criar arquivo, e ele esta patchado para no-op.
    assert list(cache_dir.glob("*.gpkg")) == []


def test_build_osm_municipal_network_casca_continua_gravando_gpkg_e_gpkg_ok(qgis_app, monkeypatch, tmp_path):
    """Regressao do Passo 1: a casca sobre `build_osm_network_layers`
    continua gravando as 3 camadas no GPKG e devolvendo `gpkg_ok`."""
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    _monkeypatch_overpass(monkeypatch, _payload_um_way())

    gpkg_path = str(tmp_path / "diagnostico.gpkg")
    resultado = osm_pipeline.build_osm_municipal_network(
        "3106200", "Municipio Teste", gpkg_path, feedback=None)

    metadata = resultado["metadata"]
    assert metadata.get("gpkg_ok") is True

    import os
    assert os.path.exists(gpkg_path)

    from qgis.core import QgsVectorLayer
    for nome in ("osm_links_3106200", "osm_nodes_3106200", "osm_problemas_3106200"):
        camada = QgsVectorLayer("{}|layername={}".format(gpkg_path, nome), nome, "ogr")
        assert camada.isValid(), nome


# --- Passo 6: progresso e cancelamento -------------------------------------

class _FeedbackDuplo:
    """Duplo de feedback que so registra chamadas (sem QgsProcessingFeedback)."""

    def __init__(self, cancela_na_chamada=None):
        self.progressos = []
        self._chamadas_iscanceled = 0
        self._cancela_na_chamada = cancela_na_chamada

    def pushInfo(self, msg):
        pass

    def pushWarning(self, msg):
        pass

    def setProgressText(self, texto):
        pass

    def setProgress(self, pct):
        self.progressos.append(pct)

    def isCanceled(self):
        self._chamadas_iscanceled += 1
        if self._cancela_na_chamada is None:
            return False
        return self._chamadas_iscanceled >= self._cancela_na_chamada


def test_progresso_monotonico_comeca_ate_5_e_termina_em_100(qgis_app, monkeypatch, tmp_path):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    _monkeypatch_overpass(monkeypatch, _payload_um_way())

    fb = _FeedbackDuplo()
    resultado = osm_pipeline.build_osm_network_layers("3106200", cache_dir=tmp_path, feedback=fb)

    assert "cancelado" not in resultado["metadata"]
    assert fb.progressos == sorted(fb.progressos)
    assert fb.progressos[0] <= 5
    assert fb.progressos[-1] == 100


def test_iscanceled_no_meio_do_laco_interrompe_e_devolve_cancelado(qgis_app, monkeypatch, tmp_path):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    _monkeypatch_overpass(monkeypatch, _payload_um_way())

    # cancela na 2a chamada de isCanceled() (a 1a acontece dentro do laco de
    # ponta_quase_conectada da rede veicular; a 2a, dentro de
    # cruzamento_sem_no da mesma rede) — cancela ainda na verificacao.
    fb = _FeedbackDuplo(cancela_na_chamada=2)
    resultado = osm_pipeline.build_osm_network_layers("3106200", cache_dir=tmp_path, feedback=fb)

    metadata = resultado["metadata"]
    assert metadata.get("cancelado") is True
    layers = resultado["layers"]
    assert layers["osm_links"] is not None
    assert layers["osm_nodes"] is not None
    assert layers["osm_problemas"] is None


def test_feedback_none_nao_quebra(qgis_app, monkeypatch, tmp_path):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    _monkeypatch_overpass(monkeypatch, _payload_um_way())

    resultado = osm_pipeline.build_osm_network_layers("3106200", cache_dir=tmp_path, feedback=None)
    assert resultado["layers"]["osm_links"].featureCount() == 1


# --- Registro do algoritmo (Passo 3) ---------------------------------------

def test_osm_network_registrado_em_algorithms(qgis_app):
    _skip_sem_qgis(qgis_app)
    from gisbr.algorithms import ALGORITHMS
    from gisbr.algorithms.diagnostico.osm_network import OsmNetwork

    assert OsmNetwork in ALGORITHMS

    inst = OsmNetwork()
    assert inst.name() == "osm_network"
    assert inst.groupId() == "diagnostico"

    inst2 = inst.createInstance()
    assert inst2 is not inst
    assert isinstance(inst2, OsmNetwork)


# --- processAlgorithm end-to-end (sem o plugin `processing`, so QGIS core) -

def test_processalgorithm_copia_camadas_para_os_sinks(qgis_app, monkeypatch, tmp_path):
    _skip_sem_qgis(qgis_app)
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback, QgsProject
    from gisbr.algorithms.diagnostico.osm_network import OsmNetwork

    _monkeypatch_overpass(monkeypatch, _payload_um_way())

    alg = OsmNetwork()
    alg.initAlgorithm()
    context = QgsProcessingContext()
    context.setProject(QgsProject.instance())
    feedback = QgsProcessingFeedback()
    params = {
        "CODE": "3106200", "FORCE": False, "CACHE_DIR": str(tmp_path),
        "LINKS": "memory:links", "NODES": "memory:nodes", "PROBLEMAS": "memory:problemas",
    }
    result = alg.processAlgorithm(params, context, feedback)

    links = context.temporaryLayerStore().mapLayer(result["LINKS"])
    nodes = context.temporaryLayerStore().mapLayer(result["NODES"])
    problemas = context.temporaryLayerStore().mapLayer(result["PROBLEMAS"])

    assert links.featureCount() == 1
    assert nodes.featureCount() == 2
    assert problemas.featureCount() >= 1
    campos_link = {f.name() for f in links.fields()}
    assert {"maxspeed", "velocidade_kmh", "comprimento_m"} <= campos_link


def test_processalgorithm_erro_overpass_levanta_excecao(qgis_app, monkeypatch, tmp_path):
    _skip_sem_qgis(qgis_app)
    from qgis.core import (QgsProcessingContext, QgsProcessingException,
                           QgsProcessingFeedback, QgsProject)
    from gisbr.algorithms.diagnostico.osm_network import OsmNetwork
    from gisbr.core import osm_pipeline

    def falha_municipio(*args, **kwargs):
        return None

    monkeypatch.setattr(osm_pipeline, "_municipio_poligono", falha_municipio)

    alg = OsmNetwork()
    alg.initAlgorithm()
    context = QgsProcessingContext()
    context.setProject(QgsProject.instance())
    feedback = QgsProcessingFeedback()
    params = {
        "CODE": "9999999", "FORCE": False, "CACHE_DIR": str(tmp_path),
        "LINKS": "memory:links", "NODES": "memory:nodes", "PROBLEMAS": "memory:problemas",
    }
    with pytest.raises(QgsProcessingException):
        alg.processAlgorithm(params, context, feedback)
