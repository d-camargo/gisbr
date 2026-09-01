# -*- coding: utf-8 -*-
"""Testes para _validar_payload em gisbr.core.connectors.osm."""

import pytest
from gisbr.core.connectors.osm import OverpassError, _validar_payload


def test_validar_payload_html_error_real_medido():
    html = b"""
    <html>
    <head><title>Error</title></head>
    <body>
    <p>Dispatcher_Client::request_read_and_idx::timeout</p>
    </body>
    </html>
    """
    with pytest.raises(OverpassError) as excinfo:
        _validar_payload(html, "overpass-api.de")
    assert "Overpass (host: overpass-api.de): erro do servidor — Dispatcher_Client::request_read_and_idx::timeout" in str(excinfo.value)


def test_validar_payload_html_error():
    html = b"""
    <html>
    <head><title>Error</title></head>
    <body>
    <p>Error: runtime error: Query timed out after 180 seconds.</p>
    </body>
    </html>
    """
    with pytest.raises(OverpassError) as excinfo:
        _validar_payload(html, "overpass-api.de")
    assert "Overpass (host: overpass-api.de): erro do servidor — Error: runtime error: Query timed out after 180 seconds." in str(excinfo.value)


def test_validar_payload_json_remark_error():
    payload = b'{"version": 0.6, "remark": "runtime error: Query timed out after 180 seconds.", "elements": []}'
    with pytest.raises(OverpassError) as excinfo:
        _validar_payload(payload, "overpass-api.de")
    assert str(excinfo.value) == "runtime error: Query timed out after 180 seconds."


def test_validar_payload_json_remark_out_of_memory():
    payload = b'{"version": 0.6, "remark": "out of memory", "elements": []}'
    with pytest.raises(OverpassError) as excinfo:
        _validar_payload(payload, "overpass-api.de")
    assert str(excinfo.value) == "out of memory"


def test_validar_payload_json_sem_elements():
    payload = b'{"version": 0.6, "generator": "Overpass API"}'
    with pytest.raises(OverpassError) as excinfo:
        _validar_payload(payload, "overpass-api.de")
    assert "resposta sem 'elements'" in str(excinfo.value)


def test_validar_payload_elements_vazio_ok():
    payload = b'{"version": 0.6, "elements": []}'
    res = _validar_payload(payload, "overpass-api.de")
    assert res == {"version": 0.6, "elements": []}


def test_validar_payload_json_invalido_snippet():
    raw = b"502 Bad Gateway Server Response"
    with pytest.raises(OverpassError) as excinfo:
        _validar_payload(raw, "overpass-api.de")
    assert "Erro ao decodificar JSON do Overpass" in str(excinfo.value)
    assert "502 Bad Gateway Server Response" in str(excinfo.value)


def test_save_overpass_cache_valid(tmp_path):
    from gisbr.core.connectors.osm import save_overpass_cache
    cache_file = tmp_path / "cache.json"
    valid_payload = {"version": 0.6, "elements": []}
    res = save_overpass_cache(valid_payload, cache_file)
    assert res == cache_file
    assert cache_file.exists()


def test_save_overpass_cache_recusa_sem_elements(tmp_path):
    from gisbr.core.connectors.osm import save_overpass_cache
    cache_file = tmp_path / "cache.json"
    invalid_payload = {"version": 0.6}
    with pytest.raises(ValueError) as excinfo:
        save_overpass_cache(invalid_payload, cache_file)
    assert "falta 'elements'" in str(excinfo.value)
    assert not cache_file.exists()


def test_save_overpass_cache_recusa_remark_erro(tmp_path):
    from gisbr.core.connectors.osm import save_overpass_cache
    cache_file = tmp_path / "cache.json"
    invalid_payload = {"version": 0.6, "remark": "runtime error: Query timed out", "elements": []}
    with pytest.raises(ValueError) as excinfo:
        save_overpass_cache(invalid_payload, cache_file)
    assert "remark de erro" in str(excinfo.value)
    assert not cache_file.exists()


def test_load_overpass_cache_valid(tmp_path):
    from gisbr.core.connectors.osm import load_overpass_cache
    cache_file = tmp_path / "cache.json"
    cache_file.write_text('{"version": 0.6, "elements": []}', encoding="utf-8")
    payload = load_overpass_cache(cache_file)
    assert payload == {"version": 0.6, "elements": []}


def test_load_overpass_cache_invalido_retorna_none(tmp_path):
    from gisbr.core.connectors.osm import load_overpass_cache
    cache_file = tmp_path / "cache.json"
    
    # HTML Error
    cache_file.write_text("<html><p>Error: timeout</p></html>", encoding="utf-8")
    assert load_overpass_cache(cache_file) is None

    # Remark Error
    cache_file.write_text('{"version": 0.6, "remark": "runtime error", "elements": []}', encoding="utf-8")
    assert load_overpass_cache(cache_file) is None

    # Missing elements
    cache_file.write_text('{"version": 0.6}', encoding="utf-8")
    assert load_overpass_cache(cache_file) is None

    # Non-existent
    assert load_overpass_cache(tmp_path / "non_existent.json") is None


def test_fetch_json_fallback_warning(tmp_path, monkeypatch):
    from gisbr.core.connectors.osm import _fetch_json, OverpassError

    def mock_post_overpass(query, timeout):
        raise OverpassError("Rede indisponivel")

    monkeypatch.setattr("gisbr.core.connectors.osm._post_overpass", mock_post_overpass)

    cache_file = tmp_path / "cache.json"
    cache_file.write_text('{"version": 0.6, "elements": []}', encoding="utf-8")

    class MockFeedback:
        def __init__(self):
            self.warnings = []
        def pushWarning(self, msg):
            self.warnings.append(msg)

    fb = MockFeedback()
    res = _fetch_json("query", 180, cache_path=cache_file, feedback=fb)
    assert res == {"version": 0.6, "elements": []}
    assert len(fb.warnings) == 1
    assert "Usando dados antigos do cache local" in fb.warnings[0]


def test_osm_pipeline_cache_logging(tmp_path, monkeypatch):
    from gisbr.core import osm_pipeline

    class DummyLayer:
        def extent(self):
            class Extent:
                def xMinimum(self): return -44.0
                def yMinimum(self): return -20.0
                def xMaximum(self): return -43.9
                def yMaximum(self): return -19.9
            return Extent()
        def name(self):
            return "municipio"

    monkeypatch.setattr(osm_pipeline, "_municipio_poligono", lambda code, name=None: DummyLayer())

    class MockFeedback:
        def __init__(self):
            self.infos = []
        def pushInfo(self, msg):
            self.infos.append(msg)

    # 1. Cache valido
    cache_path = tmp_path / "osm_overpass_3106200.json"
    cache_path.write_text('{"version": 0.6, "elements": []}', encoding="utf-8")
    fb1 = MockFeedback()
    osm_pipeline.build_osm_municipal_network("3106200", "Belo Horizonte", str(tmp_path / "test.gpkg"), feedback=fb1)
    assert any("OSM: cache reutilizado" in msg and str(cache_path) in msg for msg in fb1.infos)

    # 2. Cache corrompido
    cache_path.write_text('<html>Error</html>', encoding="utf-8")
    fb2 = MockFeedback()
    monkeypatch.setattr("gisbr.core.connectors.osm.fetch_overpass_json", lambda bbox, timeout=180, cache_path=None, feedback=None: {"elements": []})
    osm_pipeline.build_osm_municipal_network("3106200", "Belo Horizonte", str(tmp_path / "test.gpkg"), feedback=fb2)
    assert any("OSM: cache invalido ou corrompido em" in msg and str(cache_path) in msg for msg in fb2.infos)


def test_poi_pipeline_cache_logging(tmp_path, monkeypatch):
    from gisbr.core import poi_pipeline

    class DummyLayer:
        def extent(self):
            class Extent:
                def xMinimum(self): return -44.0
                def yMinimum(self): return -20.0
                def xMaximum(self): return -43.9
                def yMaximum(self): return -19.9
            return Extent()
        def getFeatures(self):
            return []

    monkeypatch.setattr(poi_pipeline, "_municipio_poligono", lambda code, name=None: DummyLayer())
    monkeypatch.setattr(poi_pipeline, "_geometria_municipio", lambda mun: "dummy_geom")

    class MockFeedback:
        def __init__(self):
            self.infos = []
        def pushInfo(self, msg):
            self.infos.append(msg)

    # 1. Cache valido
    cache_path = tmp_path / "osm_poi_3106200.json"
    cache_path.write_text('{"version": 0.6, "elements": []}', encoding="utf-8")
    fb1 = MockFeedback()
    poi_pipeline.build_osm_municipal_pois("3106200", "Belo Horizonte", str(tmp_path / "test.gpkg"), feedback=fb1)
    assert any("OSM POI: cache reutilizado" in msg and str(cache_path) in msg for msg in fb1.infos)

    # 2. Cache corrompido
    cache_path.write_text('<html>Error</html>', encoding="utf-8")
    fb2 = MockFeedback()
    monkeypatch.setattr("gisbr.core.connectors.osm.fetch_poi_json", lambda bbox, timeout=180, cache_path=None, feedback=None: {"elements": []})
    poi_pipeline.build_osm_municipal_pois("3106200", "Belo Horizonte", str(tmp_path / "test.gpkg"), feedback=fb2)
    assert any("OSM POI: cache invalido ou corrompido em" in msg and str(cache_path) in msg for msg in fb2.infos)


