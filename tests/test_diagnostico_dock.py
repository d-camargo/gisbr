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


# --- barra de progresso -------------------------------------

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


# --- OsmNetworkTask no painel (roda em segundo plano, sem travar a UI) ---

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


# --- testes da selecao de modo de recorte (Municipio x RM) ---

def test_modo_recorte_inicial_e_municipio(dock):
    from gisbr.gui.diagnostico_dock import ModoRecorte
    assert dock.modo_recorte == ModoRecorte.MUNICIPIO
    assert dock.rad_muni.isChecked() is True
    assert dock.rad_rm.isChecked() is False

    # Widgets do modo municipio habilitados
    assert dock.cmb_muni.isEnabled() is True
    assert dock.ed_muni.isEnabled() is True
    assert dock.lbl_muni.isEnabled() is True
    assert dock.lbl_ed_muni.isEnabled() is True

    # Widgets do modo RM desabilitados
    assert dock.cmb_rm.isEnabled() is False
    assert dock.lst_rm_munis.isEnabled() is False
    assert dock.lbl_rm.isEnabled() is False
    assert dock.lbl_rm_munis_count.isEnabled() is False


def test_troca_modo_habilita_deshabilita_widgets_e_limpa_estado(dock):
    from gisbr.gui.diagnostico_dock import ModoRecorte

    # Alterna para modo RM
    dock.rad_rm.setChecked(True)

    assert dock.modo_recorte == ModoRecorte.RM
    assert dock.rad_rm.isChecked() is True
    assert dock.rad_muni.isChecked() is False

    # Widgets do modo municipio desabilitados
    assert dock.cmb_muni.isEnabled() is False
    assert dock.ed_muni.isEnabled() is False
    assert dock.lbl_muni.isEnabled() is False
    assert dock.lbl_ed_muni.isEnabled() is False

    # Widgets do modo RM habilitados
    assert dock.cmb_rm.isEnabled() is True
    assert dock.lst_rm_munis.isEnabled() is True
    assert dock.lbl_rm.isEnabled() is True
    assert dock.lbl_rm_munis_count.isEnabled() is True

    # Alterna de volta para modo municipio
    dock.rad_muni.setChecked(True)
    assert dock.modo_recorte == ModoRecorte.MUNICIPIO
    assert dock.cmb_muni.isEnabled() is True
    assert dock.cmb_rm.isEnabled() is False


def test_modo_rm_selecao_uf_mg_e_rm_bh(dock, monkeypatch):
    # Garantir que _listar_municipios NAO e chamado em modo RM
    listar_muni_chamado = False
    def _fake_listar_muni(uf):
        nonlocal listar_muni_chamado
        listar_muni_chamado = True
        return {}

    monkeypatch.setattr(dock, "_listar_municipios", _fake_listar_muni)

    # Marca modo RM
    dock.rad_rm.setChecked(True)

    # Escolhe UF MG
    idx_mg = dock.cmb_uf.findData("MG")
    assert idx_mg != -1
    dock.cmb_uf.setCurrentIndex(idx_mg)

    # _listar_municipios nao deve ter sido chamado (sem download de malha)
    assert listar_muni_chamado is False

    # cmb_rm deve conter 4 RMs
    assert dock.cmb_rm.count() == 4

    # Escolher RM de BH (id "03101" ou texto contendo "Belo Horizonte")
    idx_bh = -1
    for i in range(dock.cmb_rm.count()):
        text = dock.cmb_rm.itemText(i)
        if "Belo Horizonte" in text and "Colar" not in text:
            idx_bh = i
            break

    assert idx_bh != -1
    dock.cmb_rm.setCurrentIndex(idx_bh)

    # Lista de municipios membros deve conter 34 itens
    assert dock.lst_rm_munis.count() == 34
    assert "34" in dock.lbl_rm_munis_count.text()


def test_modo_rm_desabilita_e_desmarca_fontes_osm_e_loga_motivo(dock):
    vias_item = _find_tree_item_by_user_data(dock.tree, "osm_vias")
    pois_item = _find_tree_item_by_user_data(dock.tree, "osm_pois")
    assert vias_item is not None
    assert pois_item is not None
    vias_item.setCheckState(0, Qt.CheckState.Checked)
    pois_item.setCheckState(0, Qt.CheckState.Checked)

    # Entra no modo RM
    dock.rad_rm.setChecked(True)

    # Verifica se foram desmarcados e desabilitados
    assert vias_item.checkState(0) == Qt.CheckState.Unchecked
    assert pois_item.checkState(0) == Qt.CheckState.Unchecked
    assert bool(vias_item.flags() & Qt.ItemFlag.ItemIsEnabled) is False
    assert bool(pois_item.flags() & Qt.ItemFlag.ItemIsEnabled) is False

    # Verifica se a razão foi logada no log
    log_text = dock.txt_log.toPlainText()
    assert "disabled" in log_text or "municipality" in log_text

    # Volta para modo município
    dock.rad_muni.setChecked(True)
    assert bool(vias_item.flags() & Qt.ItemFlag.ItemIsEnabled) is True
    assert bool(pois_item.flags() & Qt.ItemFlag.ItemIsEnabled) is True


def test_modo_rm_on_carregar_sem_rm_escolhida_valida_mensagem(dock, monkeypatch):
    carregar_chamado = False
    def _fake_carregar_fontes(*args, **kwargs):
        nonlocal carregar_chamado
        carregar_chamado = True
        return {"ok": [], "falhou": [], "pulou": []}

    monkeypatch.setattr(diagnostico_dock.diagnostico, "carregar_fontes", _fake_carregar_fontes)

    dock.rad_rm.setChecked(True)
    dock.ed_gpkg.setText("/tmp/test.gpkg")

    item = _find_tree_item_by_user_data(dock.tree, "geobr_setores")
    item.setCheckState(0, Qt.CheckState.Checked)

    # Não seleciona NENHUMA RM
    dock._on_carregar()

    assert carregar_chamado is False
    assert "Select a metropolitan region" in dock.txt_log.toPlainText()


def test_modo_rm_on_carregar_chama_carregar_fontes_com_recorte_rm_e_sem_task_osm(dock, monkeypatch):
    captured_kwargs = {}
    def _fake_carregar_fontes(*args, **kwargs):
        captured_kwargs.update(kwargs)
        captured_kwargs["source_ids"] = args[0]
        return {"ok": ["geobr_setores"], "falhou": [], "pulou": []}

    osm_iniciado = False
    def _fake_iniciar_osm_vias(*args, **kwargs):
        nonlocal osm_iniciado
        osm_iniciado = True

    monkeypatch.setattr(diagnostico_dock.diagnostico, "carregar_fontes", _fake_carregar_fontes)
    monkeypatch.setattr(dock, "_iniciar_osm_vias", _fake_iniciar_osm_vias)

    dock.rad_rm.setChecked(True)
    idx_mg = dock.cmb_uf.findData("MG")
    dock.cmb_uf.setCurrentIndex(idx_mg)

    idx_bh = -1
    for i in range(dock.cmb_rm.count()):
        if dock.cmb_rm.itemData(i) == "04501":
            idx_bh = i
            break
    assert idx_bh != -1
    dock.cmb_rm.setCurrentIndex(idx_bh)

    dock.ed_gpkg.setText("/tmp/rm_test.gpkg")

    item = _find_tree_item_by_user_data(dock.tree, "geobr_setores")
    item.setCheckState(0, Qt.CheckState.Checked)

    dock._on_carregar()

    assert osm_iniciado is False
    assert "recorte" in captured_kwargs
    recorte = captured_kwargs["recorte"]
    assert recorte.tipo == "rm"
    assert recorte.id == "04501"
    assert len(recorte.codes) == 34
    assert recorte.rotulo == "RM de Belo Horizonte"

    log_text = dock.txt_log.toPlainText()
    assert "Metropolitan region: RM de Belo Horizonte — 34 municipalities" in log_text


def test_modo_municipio_on_carregar_continua_chamando_como_antes(dock, monkeypatch):
    captured_kwargs = {}
    def _fake_carregar_fontes(*args, **kwargs):
        captured_kwargs.update(kwargs)
        captured_kwargs["args"] = args
        return {"ok": ["geobr_setores"], "falhou": [], "pulou": []}

    osm_calls = []
    def _fake_iniciar_osm_vias(code, nome, gpkg, force):
        osm_calls.append((code, nome, gpkg, force))

    monkeypatch.setattr(diagnostico_dock.diagnostico, "carregar_fontes", _fake_carregar_fontes)
    monkeypatch.setattr(dock, "_iniciar_osm_vias", _fake_iniciar_osm_vias)
    monkeypatch.setattr(dock, "_info_municipio", lambda code: ("Belo Horizonte", (-44, -20, -43, -19)))

    dock.rad_muni.setChecked(True)
    dock.ed_muni.setText("3106200")
    dock.ed_gpkg.setText("/tmp/muni_test.gpkg")

    item = _find_tree_item_by_user_data(dock.tree, "geobr_setores")
    item.setCheckState(0, Qt.CheckState.Checked)
    vias_item = _find_tree_item_by_user_data(dock.tree, "osm_vias")
    vias_item.setCheckState(0, Qt.CheckState.Checked)

    dock._on_carregar()

    assert "recorte" in captured_kwargs
    recorte = captured_kwargs["recorte"]
    assert recorte.tipo == "municipio"
    assert recorte.id == "3106200"

    assert len(osm_calls) == 1
    assert osm_calls[0][0] == "3106200"
    assert "Municipality: Belo Horizonte (3106200)" in dock.txt_log.toPlainText()



