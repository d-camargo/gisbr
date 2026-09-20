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


# --- resolve_municipio / compute_osm_network (Passo 1, plano osm_qgstask) -

def _municipio_sem_geometria(*args, **kwargs):
    from qgis.core import QgsVectorLayer
    # camada válida mas SEM feições -> _geometria_municipio devolve None.
    return QgsVectorLayer("Polygon?crs=EPSG:4674", "municipio", "memory")


def test_resolve_municipio_devolve_none_triplo_quando_nao_resolve(qgis_app, monkeypatch):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    monkeypatch.setattr(osm_pipeline, "_municipio_poligono", lambda *a, **k: None)

    resultado = osm_pipeline.resolve_municipio("9999999")
    assert resultado == (None, None, None)


def test_resolve_municipio_devolve_mun_geom_none_quando_geometria_invalida(qgis_app, monkeypatch):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    monkeypatch.setattr(osm_pipeline, "_municipio_poligono", _municipio_sem_geometria)

    municipio, bbox, mun_geom = osm_pipeline.resolve_municipio("0000000")
    assert municipio is not None
    assert bbox is not None
    assert mun_geom is None


def test_compute_osm_network_sem_vias_tem_prioridade_sobre_geometria_invalida(qgis_app, monkeypatch, tmp_path):
    """Condição do Diego (Passo 1): a geometria do município passou a ser
    CALCULADA cedo (`resolve_municipio`), mas a VALIDAÇÃO continua na mesma
    ordem de sempre — payload sem ways devolve `sem_vias`, não "municipio
    sem geometria valida", mesmo com `mun_geom` inválido (`None`)."""
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    monkeypatch.setattr(osm_pipeline.osm, "fetch_overpass_json", lambda *a, **k: {"elements": []})
    monkeypatch.setattr(osm_pipeline.osm, "save_overpass_cache", lambda *a, **k: None)
    monkeypatch.setattr(osm_pipeline.osm, "load_overpass_cache", lambda *a, **k: None)

    dados = osm_pipeline.compute_osm_network(
        "0000000", "Municipio Teste", (-1, -1, 1, 1), None, cache_dir=tmp_path)

    metadata = dados["metadata"]
    assert metadata.get("sem_vias") is True
    assert metadata["erro"] == "nenhum way com highway encontrado no bbox"
    assert dados["arcos_todos"] is None
    assert dados["arcos"] is None


def test_build_osm_network_layers_sem_vias_precede_geometria_invalida_e2e(qgis_app, monkeypatch, tmp_path):
    """Mesma trava do teste acima, mas fim a fim por `build_osm_network_layers`
    (que compõe `resolve_municipio` + `compute_osm_network`)."""
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    _monkeypatch_overpass(monkeypatch, {"elements": []}, municipio=_municipio_sem_geometria)

    resultado = osm_pipeline.build_osm_network_layers("0000000", cache_dir=tmp_path)

    metadata = resultado["metadata"]
    assert metadata.get("sem_vias") is True
    assert metadata["erro"] == "nenhum way com highway encontrado no bbox"
    assert resultado["layers"]["osm_links_raw"] is None


def test_compute_osm_network_devolve_dados_puros_sem_qgsvectorlayer(qgis_app, monkeypatch, tmp_path):
    _skip_sem_qgis(qgis_app)
    from qgis.core import QgsVectorLayer
    from gisbr.core import osm_pipeline

    municipio = _municipio_fake()
    bbox = osm_pipeline._bbox_da_camada(municipio)
    mun_geom = osm_pipeline._geometria_municipio(municipio)

    monkeypatch.setattr(osm_pipeline.osm, "fetch_overpass_json", lambda *a, **k: _payload_um_way())
    monkeypatch.setattr(osm_pipeline.osm, "save_overpass_cache", lambda *a, **k: None)
    monkeypatch.setattr(osm_pipeline.osm, "load_overpass_cache", lambda *a, **k: None)

    dados = osm_pipeline.compute_osm_network("3106200", "Belo Horizonte", bbox, mun_geom, cache_dir=tmp_path)

    assert "erro" not in dados["metadata"]
    for chave in ("arcos_todos", "arcos", "diag_veicular", "diag_pedestre", "nodes_dict", "problemas"):
        assert not isinstance(dados[chave], QgsVectorLayer)
    assert len(dados["arcos"]) == 1
    assert isinstance(dados["problemas"], list)
    for p in dados["problemas"]:
        assert isinstance(p, dict)


def test_compute_osm_network_cancelado_deixa_problemas_none(qgis_app, monkeypatch, tmp_path):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    municipio = _municipio_fake()
    bbox = osm_pipeline._bbox_da_camada(municipio)
    mun_geom = osm_pipeline._geometria_municipio(municipio)

    monkeypatch.setattr(osm_pipeline.osm, "fetch_overpass_json", lambda *a, **k: _payload_um_way())
    monkeypatch.setattr(osm_pipeline.osm, "save_overpass_cache", lambda *a, **k: None)
    monkeypatch.setattr(osm_pipeline.osm, "load_overpass_cache", lambda *a, **k: None)

    fb = _FeedbackDuplo(cancela_na_chamada=1)
    dados = osm_pipeline.compute_osm_network(
        "3106200", "Belo Horizonte", bbox, mun_geom, cache_dir=tmp_path, feedback=fb)

    assert dados["metadata"].get("cancelado") is True
    assert dados["arcos_todos"] is not None
    assert dados["arcos"] is not None
    assert dados["problemas"] is None


def test_montar_camadas_devolve_quatro_camadas_com_campos_certos(qgis_app, monkeypatch, tmp_path):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    municipio = _municipio_fake()
    bbox = osm_pipeline._bbox_da_camada(municipio)
    mun_geom = osm_pipeline._geometria_municipio(municipio)

    monkeypatch.setattr(osm_pipeline.osm, "fetch_overpass_json", lambda *a, **k: _payload_um_way())
    monkeypatch.setattr(osm_pipeline.osm, "save_overpass_cache", lambda *a, **k: None)
    monkeypatch.setattr(osm_pipeline.osm, "load_overpass_cache", lambda *a, **k: None)

    dados = osm_pipeline.compute_osm_network("3106200", "Belo Horizonte", bbox, mun_geom, cache_dir=tmp_path)
    layers = osm_pipeline.montar_camadas(dados)

    assert layers["osm_links"].featureCount() == 1
    assert layers["osm_nodes"].featureCount() == 2
    assert layers["osm_problemas"] is not None

    campos_link = {f.name() for f in layers["osm_links"].fields()}
    assert campos_link == {n for n, _k in osm_pipeline._LINK_FIELDS}
    campos_node = {f.name() for f in layers["osm_nodes"].fields()}
    assert campos_node == {n for n, _k in osm_pipeline._NODE_FIELDS}
    campos_problema = {f.name() for f in layers["osm_problemas"].fields()}
    assert campos_problema == {n for n, _k in osm_pipeline._PROBLEMA_FIELDS}


def test_montar_camadas_sem_arcos_todos_devolve_tudo_none(qgis_app):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    layers = osm_pipeline.montar_camadas({
        "arcos_todos": None, "arcos": None, "diag_veicular": None,
        "diag_pedestre": None, "nodes_dict": None, "problemas": None,
        "metadata": {"code_muni": "0000000", "nome_muni": None},
    })
    assert layers == {"osm_links_raw": None, "osm_links": None, "osm_nodes": None, "osm_problemas": None}


def test_osm_vias_ja_existe(qgis_app):
    _skip_sem_qgis(qgis_app)
    from gisbr.core import osm_pipeline

    existentes = {"osm_links_3106200", "osm_nodes_3106200", "outra_camada"}
    assert osm_pipeline.osm_vias_ja_existe(existentes, "3106200") is True
    assert osm_pipeline.osm_vias_ja_existe(existentes, "9999999") is False
    assert osm_pipeline.osm_vias_ja_existe({"osm_links_3106200"}, "3106200") is False


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
