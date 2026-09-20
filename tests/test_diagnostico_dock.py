# -*- coding: utf-8 -*-
"""Testes headless do painel DiagnosticoDock (D8)."""

import pytest

pytest.importorskip("qgis.core")

from qgis.PyQt.QtCore import Qt
from gisbr.gui import diagnostico_dock
from gisbr.gui.diagnostico_dock import DiagnosticoDock, TAB_CENSO, TAB_LOG, _LogFeedback
from gisbr.core import catalog_censo

_SETTINGS_STORE = {}


class MemoryQSettings:
    def value(self, key, default=None):
        return _SETTINGS_STORE.get(key, default)

    def setValue(self, key, value):
        _SETTINGS_STORE[key] = value


@pytest.fixture
def dock(qgis_app, monkeypatch):
    if qgis_app is None:
        pytest.skip("qgis app não disponível")

    _SETTINGS_STORE.clear()

    monkeypatch.setattr(catalog_censo, "available_years", lambda: [2000, 2010, 2022])
    monkeypatch.setattr(
        catalog_censo,
        "available_datasets_por_ano",
        lambda: {2000: ["Basico"], 2010: ["Basico", "DomicilioRenda"], 2022: ["Basico"]},
    )
    monkeypatch.setattr(
        diagnostico_dock, "QSettings", lambda *args, **kwargs: MemoryQSettings()
    )

    return DiagnosticoDock(iface=None)


def _find_tree_item_by_user_data(tree, target_id):
    for i in range(tree.topLevelItemCount()):
        parent = tree.topLevelItem(i)
        for j in range(parent.childCount()):
            child = parent.child(j)
            if child.data(0, Qt.ItemDataRole.UserRole) == target_id:
                return child
    return None


def test_dock_tab_count_and_labels(dock):
    assert dock.tabs.count() == 5
    labels = [dock.tabs.tabText(i) for i in range(dock.tabs.count())]
    assert labels == ["Location", "Sources", "Census", "Output", "Log"]


def test_aba_censo_inicialmente_desabilitada(dock):
    assert dock.tabs.isTabEnabled(TAB_CENSO) is False
    assert dock.tabs.tabToolTip(TAB_CENSO) != ""


def test_marcar_desmarcar_geobr_setores_habilita_aba_censo(dock):
    item = _find_tree_item_by_user_data(dock.tree, "geobr_setores")
    assert item is not None

    item.setCheckState(0, Qt.CheckState.Checked)
    assert dock.tabs.isTabEnabled(TAB_CENSO) is True
    assert dock.tabs.tabToolTip(TAB_CENSO) == ""

    item.setCheckState(0, Qt.CheckState.Unchecked)
    assert dock.tabs.isTabEnabled(TAB_CENSO) is False
    assert dock.tabs.tabToolTip(TAB_CENSO) != ""


def test_selected_source_ids(dock):
    for i in range(dock.tree.topLevelItemCount()):
        parent = dock.tree.topLevelItem(i)
        for j in range(parent.childCount()):
            parent.child(j).setCheckState(0, Qt.CheckState.Unchecked)

    item = _find_tree_item_by_user_data(dock.tree, "geobr_setores")
    assert item is not None
    item.setCheckState(0, Qt.CheckState.Checked)

    assert dock._selected_source_ids() == ["geobr_setores"]


def test_log_focar(dock):
    dock._log("oi", focar=True)
    assert "oi" in dock.txt_log.toPlainText()
    assert dock.tabs.currentIndex() == TAB_LOG


def test_mapbiomas_ano_combobox_habilita_deshabilita(dock):
    assert dock.cmb_mapbiomas_ano.isEnabled() is False

    item = _find_tree_item_by_user_data(dock.tree, "mapbiomas_cobertura")
    assert item is not None

    item.setCheckState(0, Qt.CheckState.Checked)
    assert dock.cmb_mapbiomas_ano.isEnabled() is True

    item.setCheckState(0, Qt.CheckState.Unchecked)
    assert dock.cmb_mapbiomas_ano.isEnabled() is False


def test_mapbiomas_ano_qsettings_persistencia(dock, monkeypatch):
    _SETTINGS_STORE["gisbr/mapbiomas_ano"] = 2015
    new_dock = DiagnosticoDock(iface=None)
    assert new_dock.cmb_mapbiomas_ano.currentData() == 2015

    idx_2020 = new_dock.cmb_mapbiomas_ano.findData(2020)
    assert idx_2020 != -1
    new_dock.cmb_mapbiomas_ano.setCurrentIndex(idx_2020)

    assert _SETTINGS_STORE.get("gisbr/mapbiomas_ano") == 2020


# --- Passo 6b: barra de progresso -------------------------------------

def test_progress_bar_e_botao_cancelar_comecam_escondidos(dock):
    assert dock.progress_bar.isVisible() is False
    assert dock.btn_cancelar.isVisible() is False


def test_logfeedback_sem_barra_continua_funcionando_como_antes(dock):
    # Sem `progress_bar` (default None), _LogFeedback nao pode quebrar —
    # so loga e reporta progresso pela API padrao do QgsProcessingFeedback.
    fb = _LogFeedback(dock.txt_log)
    fb.pushInfo("mensagem de teste")
    fb.setProgressText("etapa")
    fb.setProgress(42)
    assert "mensagem de teste" in dock.txt_log.toPlainText()
    assert fb.progress() == 42


def test_logfeedback_com_barra_atualiza_valor_e_formato(dock):
    fb = _LogFeedback(dock.txt_log, progress_bar=dock.progress_bar)
    fb.setProgressText("Consultando Overpass")
    fb.setProgress(55)
    assert dock.progress_bar.value() == 55
    assert "Consultando Overpass" in dock.progress_bar.format()


def test_on_cancelar_chama_cancel_do_feedback_atual(dock):
    fb = _LogFeedback(dock.txt_log, progress_bar=dock.progress_bar)
    dock._feedback_atual = fb
    dock.btn_cancelar.setEnabled(True)

    dock._on_cancelar()

    assert fb.isCanceled() is True
    assert dock.btn_cancelar.isEnabled() is False


def test_on_cancelar_sem_feedback_atual_nao_quebra(dock):
    dock._feedback_atual = None
    dock._on_cancelar()  # nao deve lancar excecao


# --- Passo 3/4 do plano osm_qgstask: OsmNetworkTask no painel ------------

class _TaskDuplo:
    """Duplo mínimo de OsmNetworkTask para testar `_on_cancelar`."""

    def __init__(self):
        self.cancelado = False

    def cancel(self):
        self.cancelado = True

    def isCanceled(self):
        return self.cancelado


def test_on_cancelar_chama_cancel_da_task_osm(dock):
    task = _TaskDuplo()
    dock._task_osm = task
    dock.btn_cancelar.setEnabled(True)

    dock._on_cancelar()

    assert task.cancelado is True
    assert dock.btn_cancelar.isEnabled() is False


def test_iniciar_osm_vias_nao_sobrescreve_task_em_andamento(dock):
    """Guarda contra clique duplo em 'Load selected': o botão volta a ficar
    habilitado antes da task de OSM terminar (finally do trecho síncrono) —
    sem a guarda, uma segunda chamada sobrescreveria `_task_osm`, deixando a
    primeira órfã e as duas gravando no mesmo GeoPackage."""
    task_existente = _TaskDuplo()
    dock._task_osm = task_existente

    dock._iniciar_osm_vias("3106200", "Belo Horizonte", "/tmp/x.gpkg", force=False)

    assert dock._task_osm is task_existente
    assert "SKIPPED osm_vias" in dock.txt_log.toPlainText()
    assert "already in progress" in dock.txt_log.toPlainText()


def test_on_osm_concluida_none_por_cancelamento_nao_quebra_e_loga(dock):
    task = _TaskDuplo()
    task.cancelado = True
    dock._task_osm = task
    dock._osm_code, dock._osm_nome, dock._osm_gpkg = "3106200", "Belo Horizonte", "/tmp/x.gpkg"
    dock.progress_bar.setVisible(True)
    dock.btn_cancelar.setVisible(True)

    dock._on_osm_concluida(None)

    assert "SKIPPED osm_vias" in dock.txt_log.toPlainText()
    assert dock.progress_bar.isVisible() is False
    assert dock.btn_cancelar.isVisible() is False
    assert dock._task_osm is None


def test_on_osm_concluida_none_por_erro_nao_quebra_e_loga(dock):
    class _TaskComErro:
        erro = "Erro no Overpass: timeout"
        sem_vias = False
        def isCanceled(self):
            return False

    dock._task_osm = _TaskComErro()
    dock._osm_code, dock._osm_nome, dock._osm_gpkg = "3106200", "Belo Horizonte", "/tmp/x.gpkg"

    dock._on_osm_concluida(None)

    assert "FAILED osm_vias" in dock.txt_log.toPlainText()
    assert "timeout" in dock.txt_log.toPlainText()


def test_on_osm_concluida_none_por_sem_vias_loga_skipped_nao_failed(dock):
    """Paridade com o caminho síncrono: 'nenhuma via no bbox' é SKIPPED, não
    FAILED, não importa se veio do `OsmNetworkTask` ou de `carregar_fontes`."""
    class _TaskSemVias:
        erro = "nenhum way com highway encontrado no bbox"
        sem_vias = True
        def isCanceled(self):
            return False

    dock._task_osm = _TaskSemVias()
    dock._osm_code, dock._osm_nome, dock._osm_gpkg = "3106200", "Belo Horizonte", "/tmp/x.gpkg"

    dock._on_osm_concluida(None)

    texto = dock.txt_log.toPlainText()
    assert "SKIPPED osm_vias" in texto
    assert "nenhum way com highway encontrado no bbox" in texto
    assert "FAILED" not in texto


def test_on_osm_concluida_com_dados_sintéticos_adiciona_camadas(dock, tmp_path):
    from qgis.core import QgsProject
    from gisbr.core import osm_pipeline

    dock._task_osm = None
    code, nome = "3106200", "Belo Horizonte"
    gpkg = str(tmp_path / "test.gpkg")
    dock._osm_code, dock._osm_nome, dock._osm_gpkg = code, nome, gpkg

    payload = {
        "elements": [
            {"type": "node", "id": 1, "lat": -19.95, "lon": -43.95},
            {"type": "node", "id": 2, "lat": -19.95, "lon": -43.94},
            {"type": "way", "id": 100, "nodes": [1, 2], "tags": {"highway": "residential"}},
        ]
    }

    from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer
    municipio = QgsVectorLayer("Polygon?crs=EPSG:4674", "municipio", "memory")
    municipio.startEditing()
    feat = QgsFeature(municipio.fields())
    feat.setGeometry(QgsGeometry.fromWkt("POLYGON((-44 -20, -43.9 -20, -43.9 -19.9, -44 -19.9, -44 -20))"))
    municipio.addFeature(feat)
    municipio.commitChanges()
    bbox = osm_pipeline._bbox_da_camada(municipio)
    mun_geom = osm_pipeline._geometria_municipio(municipio)

    import gisbr.core.osm_pipeline as osm_pipeline_mod
    orig_fetch = osm_pipeline_mod.osm.fetch_overpass_json
    orig_save = osm_pipeline_mod.osm.save_overpass_cache
    orig_load = osm_pipeline_mod.osm.load_overpass_cache
    osm_pipeline_mod.osm.fetch_overpass_json = lambda *a, **k: payload
    osm_pipeline_mod.osm.save_overpass_cache = lambda *a, **k: None
    osm_pipeline_mod.osm.load_overpass_cache = lambda *a, **k: None
    try:
        dados = osm_pipeline.compute_osm_network(code, nome, bbox, mun_geom, cache_dir=tmp_path)
    finally:
        osm_pipeline_mod.osm.fetch_overpass_json = orig_fetch
        osm_pipeline_mod.osm.save_overpass_cache = orig_save
        osm_pipeline_mod.osm.load_overpass_cache = orig_load

    antes = set(QgsProject.instance().mapLayers().keys())
    try:
        dock._on_osm_concluida(dados)

        assert "OK: osm_links (GPKG)" in dock.txt_log.toPlainText()
        assert "OK: osm_nodes (GPKG)" in dock.txt_log.toPlainText()

        depois = QgsProject.instance().mapLayers()
        novas = [lyr for lid, lyr in depois.items() if lid not in antes]
        nomes = {lyr.name() for lyr in novas}
        assert any(n.startswith("osm_links") for n in nomes)
        assert any(n.startswith("osm_nodes") for n in nomes)
    finally:
        depois_ids = set(QgsProject.instance().mapLayers().keys())
        QgsProject.instance().removeMapLayers(list(depois_ids - antes))

