# -*- coding: utf-8 -*-
"""Painel (dock) do diagnostico (ARQUITETURA.md §3.4).

Permite ao usuario escolher o municipio, selecionar as fontes de dados ativas,
definir o caminho de destino do GeoPackage e carregar os dados.
"""
import os

from qgis.gui import QgsDockWidget
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QPushButton, QFileDialog,
    QLabel, QPlainTextEdit, QComboBox, QCompleter, QGroupBox, QListWidget,
    QListWidgetItem, QTabWidget, QProgressBar, QApplication)
from qgis.PyQt.QtCore import Qt, QCoreApplication, QSettings
from qgis.core import QgsApplication, QgsProject, QgsProcessingFeedback, QgsVectorLayer
from ..core.sources import SOURCES
from ..core import diagnostico, catalog_censo, censo_join, osm_pipeline
from ..core.osm_task import OsmNetworkTask


class _LogFeedback(QgsProcessingFeedback):
    """Feedback que espelha as mensagens do motor no log do painel.

    Sem isso o motor roda com feedback=None e avisos importantes (tamanho dos
    downloads do censobr, backend Parquet ausente, join que casou 0 setores)
    nunca chegam ao usuario do painel.

    Passo 6b (progresso visivel): `progress_bar` e opcional — sem ela, o
    comportamento segue igual ao de antes (so log). Com ela, `setProgress`/
    `setProgressText` atualizam a barra e chamam `processEvents()` para a
    interface repintar durante o carregamento sincrono (e para o botao
    "Cancelar" do 6c conseguir reagir a clique no meio da chamada) — mesmo
    truque em `pushInfo`.
    """

    def __init__(self, log_widget, progress_bar=None):
        super().__init__()
        self._log = log_widget
        self._progress_bar = progress_bar

    def pushInfo(self, message):
        self._log.appendPlainText(message)
        QCoreApplication.processEvents()

    def pushWarning(self, message):
        self._log.appendPlainText(self.tr("Warning: {message}").format(message=message))
        QCoreApplication.processEvents()

    def setProgress(self, pct):
        super().setProgress(pct)
        if self._progress_bar is not None:
            self._progress_bar.setValue(int(pct))
        QCoreApplication.processEvents()

    def setProgressText(self, texto):
        super().setProgressText(texto)
        if self._progress_bar is not None:
            self._progress_bar.setFormat("{} — %p%".format(texto) if texto else "%p%")
        QCoreApplication.processEvents()

_EIXO_NOMES = {
    "transportes": QCoreApplication.translate("GisBR", "1. Transport"),
    "saneamento": QCoreApplication.translate("GisBR", "2. Drainage & Sanitation"),
    "demografia": QCoreApplication.translate("GisBR", "3. Demography"),
    "ambiental": QCoreApplication.translate("GisBR", "4. Environment"),
    "educacao": QCoreApplication.translate("GisBR", "5. Education"),
    "saude": QCoreApplication.translate("GisBR", "6. Health"),
    "urbano": QCoreApplication.translate("GisBR", "7. Urban"),
    "pol-admin": QCoreApplication.translate("GisBR", "8. Administrative"),
    "agropecuaria": QCoreApplication.translate("GisBR", "9. Agriculture & Livestock"),
}

_UFS = [
    ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapa"), ("AM", "Amazonas"),
    ("BA", "Bahia"), ("CE", "Ceara"), ("DF", "Distrito Federal"),
    ("ES", "Espirito Santo"), ("GO", "Goias"), ("MA", "Maranhao"),
    ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"), ("MG", "Minas Gerais"),
    ("PA", "Para"), ("PB", "Paraiba"), ("PR", "Parana"), ("PE", "Pernambuco"),
    ("PI", "Piaui"), ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
    ("RS", "Rio Grande do Sul"), ("RO", "Rondonia"), ("RR", "Roraima"),
    ("SC", "Santa Catarina"), ("SP", "Sao Paulo"), ("SE", "Sergipe"),
    ("TO", "Tocantins"),
]

TAB_LOCAL, TAB_FONTES, TAB_CENSO, TAB_SALVAR, TAB_LOG = 0, 1, 2, 3, 4


class DiagnosticoDock(QgsDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__("GISBR", parent)
        self.iface = iface
        self._munis = {}
        self._feedback_atual = None
        # Passo 3 do plano `osm_qgstask`: fonte `osm_vias` roda em segundo
        # plano via `OsmNetworkTask`; `_task_osm` é a task viva (ou `None`),
        # e `_osm_code`/`_osm_nome`/`_osm_gpkg` guardam o contexto que
        # `_on_osm_concluida(dados)` precisa (a task só devolve `dados`).
        self._task_osm = None
        self._osm_code = None
        self._osm_nome = None
        self._osm_gpkg = None
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)

        self.tabs.addTab(self._build_tab_local(), self.tr("Location"))
        self.tabs.addTab(self._build_tab_fontes(), self.tr("Sources"))
        self.tabs.addTab(self._build_tab_censo(), self.tr("Census"))
        self.tabs.addTab(self._build_tab_salvar(), self.tr("Output"))
        self.tabs.addTab(self._build_tab_log(), self.tr("Log"))

        layout.addWidget(self.tabs, 1)

        # 5) Botao Carregar
        self.btn_carregar = QPushButton(self.tr("Load selected"))
        self.btn_carregar.clicked.connect(self._on_carregar)
        layout.addWidget(self.btn_carregar)

        self._init_censo_ui()
        self._init_mapbiomas_ui()

        self.tree.itemChanged.connect(self._on_tree_item_changed)
        self._atualizar_aba_censo()
        self._atualizar_mapbiomas_ano()

        self.setWidget(central)

    def _build_tab_local(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 1.1) Estado (UF)
        layout.addWidget(QLabel(self.tr("State:")))
        self.cmb_uf = QComboBox()
        self.cmb_uf.addItem(self.tr("— select —"), "")
        for sig, nom in _UFS:
            self.cmb_uf.addItem("{} - {}".format(sig, nom), sig)
        self.cmb_uf.currentIndexChanged.connect(self._on_uf_changed)
        layout.addWidget(self.cmb_uf)

        # 1.2) Municipio
        layout.addWidget(QLabel(self.tr("Municipality:")))
        self.cmb_muni = QComboBox()
        self.cmb_muni.currentIndexChanged.connect(self._on_muni_changed)
        self.cmb_muni.setEditable(True)
        self.cmb_muni.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        _comp = self.cmb_muni.completer()
        _comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        _comp.setFilterMode(Qt.MatchFlag.MatchContains)
        _comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        layout.addWidget(self.cmb_muni)

        # 1.3) Codigo do Municipio (IBGE 7 digitos)
        layout.addWidget(QLabel(self.tr("IBGE code (optional / filled by selection):")))
        self.ed_muni = QLineEdit()
        self.ed_muni.setPlaceholderText(self.tr("Ex: 3106200"))
        layout.addWidget(self.ed_muni)

        layout.addStretch()
        return widget

    def _build_tab_fontes(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 2) Arvore de fontes
        layout.addWidget(QLabel(self.tr("Data sources:")))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel(self.tr("Axes and layers"))
        
        # Agrupar fontes por eixo, na ORDEM definida em _EIXO_NOMES (1..8)
        sources_por_eixo = {}
        for s in SOURCES:
            if s.get("protocolo") == "basemap":
                continue
            sources_por_eixo.setdefault(s.get("eixo", "outros"), []).append(s)

        ordem = list(_EIXO_NOMES) + [e for e in sources_por_eixo if e not in _EIXO_NOMES]
        for eixo_id in ordem:
            fontes = sources_por_eixo.get(eixo_id)
            if not fontes:
                continue
            eixo_nome = _EIXO_NOMES.get(eixo_id, eixo_id.capitalize())
            parent_item = QTreeWidgetItem(self.tree, [eixo_nome])
            for s in fontes:
                child_item = QTreeWidgetItem(parent_item, [s.get("nome", s["id"])])
                child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child_item.setCheckState(0, Qt.CheckState.Unchecked)
                child_item.setData(0, Qt.ItemDataRole.UserRole, s["id"])

        self.tree.expandAll()
        layout.addWidget(self.tree)

        mapbiomas_layout = QHBoxLayout()
        mapbiomas_label = QLabel(QCoreApplication.translate("GisBR", "MapBiomas year:"))
        self.cmb_mapbiomas_ano = QComboBox()
        mapbiomas_layout.addWidget(mapbiomas_label)
        mapbiomas_layout.addWidget(self.cmb_mapbiomas_ano)
        mapbiomas_layout.addStretch()
        layout.addLayout(mapbiomas_layout)

        return widget

    def _build_tab_censo(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 2.1) Grupo Censo (censobr) (D7)
        self.grp_censo = QGroupBox(self.tr("Attach Census tables to census tracts (censobr)"))
        self.grp_censo.setCheckable(True)
        self.grp_censo.setChecked(False)
        grp_censo_layout = QVBoxLayout(self.grp_censo)

        grp_censo_layout.addWidget(QLabel(self.tr("Census year:")))
        self.cmb_censo_ano = QComboBox()
        grp_censo_layout.addWidget(self.cmb_censo_ano)

        grp_censo_layout.addWidget(QLabel(self.tr("Tables / Datasets:")))
        self.lst_censo_datasets = QListWidget()
        grp_censo_layout.addWidget(self.lst_censo_datasets)

        layout.addWidget(self.grp_censo)

        return widget

    def _build_tab_salvar(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 3) Destino GeoPackage
        layout.addWidget(QLabel(self.tr("GeoPackage destination:")))
        gpkg_layout = QHBoxLayout()
        self.ed_gpkg = QLineEdit()
        self.ed_gpkg.setPlaceholderText(self.tr("Path to .gpkg file"))
        gpkg_layout.addWidget(self.ed_gpkg)
        btn_gpkg = QPushButton("...")
        btn_gpkg.clicked.connect(self._on_choose_gpkg)
        gpkg_layout.addWidget(btn_gpkg)
        layout.addLayout(gpkg_layout)

        # 3.1) Pasta de downloads manuais (fontes protocolo "arquivo")
        layout.addWidget(QLabel(self.tr("Manual downloads folder:")))
        manual_layout = QHBoxLayout()
        self.ed_manual_folder = QLineEdit()
        self.ed_manual_folder.setReadOnly(True)
        self.ed_manual_folder.setText(diagnostico._pasta_downloads_manuais())
        self.ed_manual_folder.setPlaceholderText(self.tr("Path to manual downloads folder (optional)"))
        manual_layout.addWidget(self.ed_manual_folder)
        btn_manual = QPushButton("...")
        btn_manual.clicked.connect(self._on_choose_manual_folder)
        manual_layout.addWidget(btn_manual)
        layout.addLayout(manual_layout)

        # 4) Basemap satelite
        self.chk_satelite = QCheckBox(self.tr("Add satellite basemap"))
        layout.addWidget(self.chk_satelite)

        self.chk_atualizar = QCheckBox(self.tr("Update already-downloaded layers (re-download)"))
        layout.addWidget(self.chk_atualizar)

        layout.addStretch()

        return widget

    def _build_tab_log(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 6) PlainTextEdit para log
        layout.addWidget(QLabel(self.tr("Execution log:")))
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        layout.addWidget(self.txt_log)

        # 6.1) Barra de progresso (Passo 6b) + botao Cancelar (Passo 6c) —
        # escondidos fora da execucao.
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, 1)
        self.btn_cancelar = QPushButton(self.tr("Cancel"))
        self.btn_cancelar.setVisible(False)
        self.btn_cancelar.clicked.connect(self._on_cancelar)
        progress_layout.addWidget(self.btn_cancelar)
        layout.addLayout(progress_layout)

        return widget

    def _on_choose_gpkg(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Select GeoPackage"), "", "GeoPackage (*.gpkg)"
        )
        if path:
            if not path.lower().endswith(".gpkg"):
                path += ".gpkg"
            self.ed_gpkg.setText(path)

    def _on_choose_manual_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Select Manual Downloads Folder"), ""
        )
        if folder:
            self.ed_manual_folder.setText(folder)
            QSettings().setValue(diagnostico._QSETTINGS_PASTA_MANUAL, folder)

    def _selected_source_ids(self):
        ids = []
        for i in range(self.tree.topLevelItemCount()):
            parent_item = self.tree.topLevelItem(i)
            for j in range(parent_item.childCount()):
                child = parent_item.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    source_id = child.data(0, Qt.ItemDataRole.UserRole)
                    if source_id:
                        ids.append(source_id)
        return ids

    def _log(self, msg, focar=False):
        self.txt_log.appendPlainText(msg)
        if focar:
            self.tabs.setCurrentIndex(TAB_LOG)

    def _atualizar_aba_censo(self):
        habilitada = "geobr_setores" in self._selected_source_ids()
        self.tabs.setTabEnabled(TAB_CENSO, habilitada)
        tooltip = "" if habilitada else self.tr(
            "Select 'Setores censitarios (IBGE/geobr)' in the Sources tab to enable the Census options."
        )
        self.tabs.setTabToolTip(TAB_CENSO, tooltip)

    def _atualizar_mapbiomas_ano(self):
        habilitado = "mapbiomas_cobertura" in self._selected_source_ids()
        self.cmb_mapbiomas_ano.setEnabled(habilitado)

    def _on_tree_item_changed(self, item=None, column=0):
        self._atualizar_aba_censo()
        self._atualizar_mapbiomas_ano()

    def _init_mapbiomas_ui(self):
        mapbiomas_src = next((s for s in SOURCES if s.get("id") == "mapbiomas_cobertura"), {})
        years = mapbiomas_src.get("anos", list(range(1985, 2024)))
        default_ano = mapbiomas_src.get("ano_default", 2023)

        qs = QSettings()
        saved_ano = qs.value("gisbr/mapbiomas_ano", None)
        try:
            saved_ano_int = int(saved_ano) if saved_ano is not None else None
        except (ValueError, TypeError):
            saved_ano_int = None

        target_ano = saved_ano_int if (saved_ano_int is not None and saved_ano_int in years) else default_ano

        self.cmb_mapbiomas_ano.blockSignals(True)
        self.cmb_mapbiomas_ano.clear()
        target_idx = 0
        for idx, y in enumerate(years):
            self.cmb_mapbiomas_ano.addItem(str(y), y)
            if y == target_ano:
                target_idx = idx

        self.cmb_mapbiomas_ano.setCurrentIndex(target_idx)
        self.cmb_mapbiomas_ano.blockSignals(False)

        self.cmb_mapbiomas_ano.currentIndexChanged.connect(self._on_mapbiomas_ano_changed)
        self._atualizar_mapbiomas_ano()

    def _on_mapbiomas_ano_changed(self):
        ano = self.cmb_mapbiomas_ano.currentData()
        if ano is not None:
            QSettings().setValue("gisbr/mapbiomas_ano", int(ano))

    def _listar_municipios(self, uf_sigla):
        """{code(str): (nome, bbox)} dos municipios da UF via read_municipality."""
        import processing
        res = processing.run("gisbr:read_municipality", {
            "CODE": uf_sigla, "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT",
        })
        layer = res["OUTPUT"]
        if isinstance(layer, str):
            from qgis.core import QgsVectorLayer
            layer = QgsProject.instance().mapLayer(layer) or QgsVectorLayer(layer, "m", "ogr")
        munis = {}
        for f in layer.getFeatures():
            code = str(f["code_muni"]).split(".")[0]
            nome = f["name_muni"]
            bb = f.geometry().boundingBox()
            munis[code] = (nome, (bb.xMinimum(), bb.yMinimum(),
                                  bb.xMaximum(), bb.yMaximum()))
        return munis

    def _on_uf_changed(self):
        uf = self.cmb_uf.currentData()
        self.cmb_muni.blockSignals(True)
        self.cmb_muni.clear()
        if not uf:
            self.cmb_muni.blockSignals(False)
            return
        self._log(self.tr("Loading municipalities of {uf}...").format(uf=uf))
        try:
            self._munis = self._listar_municipios(uf)
        except Exception as exc:
            self._log(self.tr("Failed to list municipalities: {error}").format(error=exc), focar=True)
            self.cmb_muni.blockSignals(False)
            return
        for code in sorted(self._munis, key=lambda c: self._munis[c][0]):
            self.cmb_muni.addItem(self._munis[code][0], code)
        self.cmb_muni.setCurrentIndex(-1)
        self.cmb_muni.blockSignals(False)
        self._log(self.tr("{count} municipalities loaded.").format(count=len(self._munis)))

    def _on_muni_changed(self):
        code = self.cmb_muni.currentData()
        if code:
            self.ed_muni.setText(str(code))

    def _info_municipio(self, code_muni):
        """Retorna (nome, bbox) do municipio via geobr read_municipality.
        bbox = (xmin, ymin, xmax, ymax) em EPSG:4674. Pode levantar excecao."""
        import processing
        res = processing.run("gisbr:read_municipality", {
            "CODE": str(code_muni), "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT",
        })
        layer = res["OUTPUT"]
        if isinstance(layer, str):
            from qgis.core import QgsVectorLayer
            layer = QgsProject.instance().mapLayer(layer) or QgsVectorLayer(layer, "muni", "ogr")
        feats = list(layer.getFeatures())
        if not feats:
            raise ValueError(self.tr("Municipality {code} not found in geobr.").format(code=code_muni))
        nome = feats[0]["name_muni"]
        ext = layer.extent()
        return nome, (ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum())

    def _init_censo_ui(self):
        self._censo_datasets_by_year = {}
        years = []
        try:
            years = catalog_censo.available_years()
            self._censo_datasets_by_year = catalog_censo.available_datasets_por_ano()
        except Exception as exc:
            years = [2000, 2010, 2022]
            fallback_ds = list(censo_join.DATASETS_FALLBACK)
            self._censo_datasets_by_year = {y: fallback_ds for y in years}
            self._log(
                self.tr("Failed to load censobr catalog ({error}); using fallback datasets.").format(error=exc)
            )

        if not years:
            years = [2000, 2010, 2022]
            fallback_ds = list(censo_join.DATASETS_FALLBACK)
            self._censo_datasets_by_year = {y: fallback_ds for y in years}

        years = sorted(list(years))

        qs = QSettings()
        saved_ano = qs.value("gisbr/censo_ano", None)
        saved_ds = qs.value("gisbr/censo_datasets", None)

        if saved_ds is None:
            self._saved_checked_ds = {"Basico"}
        elif isinstance(saved_ds, str):
            # QSettings (IniFormat) devolve lista como string "A, B"
            self._saved_checked_ds = {
                p.strip() for p in saved_ds.split(",") if p.strip()}
        else:
            try:
                self._saved_checked_ds = {str(p) for p in saved_ds}
            except TypeError:
                self._saved_checked_ds = set()

        default_ano = years[-1]
        try:
            saved_ano_int = int(saved_ano) if saved_ano is not None else None
        except (ValueError, TypeError):
            saved_ano_int = None

        target_ano = saved_ano_int if (saved_ano_int is not None and saved_ano_int in years) else default_ano

        self.cmb_censo_ano.blockSignals(True)
        self.cmb_censo_ano.clear()
        target_idx = 0
        for idx, y in enumerate(years):
            self.cmb_censo_ano.addItem(str(y), y)
            if y == target_ano:
                target_idx = idx

        self.cmb_censo_ano.setCurrentIndex(target_idx)
        self.cmb_censo_ano.blockSignals(False)

        self._repopular_censo_datasets(self._saved_checked_ds)

        self.cmb_censo_ano.currentIndexChanged.connect(self._on_censo_ano_changed)
        self.lst_censo_datasets.itemChanged.connect(self._on_censo_item_changed)

    def _get_checked_censo_datasets(self):
        checked = []
        for i in range(self.lst_censo_datasets.count()):
            item = self.lst_censo_datasets.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(item.text())
        return checked

    def _repopular_censo_datasets(self, initial_checked):
        self.lst_censo_datasets.blockSignals(True)
        self.lst_censo_datasets.clear()
        ano = self.cmb_censo_ano.currentData()
        ds_list = self._censo_datasets_by_year.get(ano, [])
        for ds in ds_list:
            item = QListWidgetItem(ds, self.lst_censo_datasets)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            if ds in initial_checked:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.lst_censo_datasets.blockSignals(False)

    def _save_censo_settings(self):
        qs = QSettings()
        ano = self.cmb_censo_ano.currentData()
        if ano is not None:
            qs.setValue("gisbr/censo_ano", int(ano))
        datasets = self._get_checked_censo_datasets()
        qs.setValue("gisbr/censo_datasets", datasets)

    def _on_censo_ano_changed(self):
        checked_prev = set(self._get_checked_censo_datasets())
        self._repopular_censo_datasets(checked_prev)
        self._save_censo_settings()

    def _on_censo_item_changed(self, item):
        self._save_censo_settings()

    def _on_carregar(self):
        self.txt_log.clear()
        code = self.ed_muni.text().strip()
        gpkg = self.ed_gpkg.text().strip()
        ids = self._selected_source_ids()
        if not code or not gpkg or not ids:
            self._log(self.tr("Specify municipality, GeoPackage and at least 1 source."), focar=True)
            return
        # Mesma normalização que `diagnostico.carregar_fontes` faz por
        # dentro — precisa acontecer aqui também porque `osm_vias` (Passo 3
        # do plano `osm_qgstask`) não passa mais por `carregar_fontes`, e as
        # duas trilhas têm de gravar no MESMO arquivo .gpkg.
        if not gpkg.lower().endswith(".gpkg"):
            gpkg = gpkg + ".gpkg"
        # Passo 3 do plano `osm_qgstask`: `osm_vias` sai do carregamento
        # síncrono e vira `OsmNetworkTask` (QgsTask) — as demais fontes
        # continuam por `diagnostico.carregar_fontes` como sempre.
        osm_vias_selecionada = "osm_vias" in ids
        ids_sincronas = [sid for sid in ids if sid != "osm_vias"]
        censo_ano = None
        censo_datasets = ()
        if self.grp_censo.isChecked():
            if "geobr_setores" not in ids:
                self._log(
                    self.tr("Notice: the Census option only applies to census tracts ('geobr_setores').")
                )
            censo_ano = self.cmb_censo_ano.currentData()
            censo_datasets = tuple(self._get_checked_censo_datasets())
        mapbiomas_ano = None
        if "mapbiomas_cobertura" in ids:
            mapbiomas_ano = self.cmb_mapbiomas_ano.currentData()
        try:
            if getattr(self, "_munis", None) and code in self._munis:
                nome, bbox = self._munis[code]
            else:
                nome, bbox = self._info_municipio(code)
        except Exception as exc:
            self._log(self.tr("Failed to resolve municipality: {error}").format(error=exc), focar=True)
            return
        self._log(self.tr("Municipality: {name} ({code})").format(name=nome, code=code), focar=True)

        feedback = _LogFeedback(self.txt_log, progress_bar=self.progress_bar)
        self._feedback_atual = feedback
        self.btn_carregar.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.btn_cancelar.setEnabled(True)
        self.btn_cancelar.setVisible(True)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if ids_sincronas:
                res = diagnostico.carregar_fontes(
                    ids_sincronas, code_muni=code, nome_muni=nome, bbox=bbox, gpkg_path=gpkg,
                    add_basemap=self.chk_satelite.isChecked(),
                    force=self.chk_atualizar.isChecked(),
                    feedback=feedback,
                    censo_ano=censo_ano, censo_datasets=censo_datasets,
                    mapbiomas_ano=mapbiomas_ano)
            else:
                res = {"ok": [], "falhou": [], "pulou": []}
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_carregar.setEnabled(True)
            self._feedback_atual = None
            # Barra/botão só somem aqui quando NÃO houver OSM para rodar em
            # segundo plano — senão sumiriam com a task ainda no ar. Quando
            # há, ficam visíveis e só somem em `_on_osm_concluida`.
            if not osm_vias_selecionada:
                self.progress_bar.setVisible(False)
                self.btn_cancelar.setVisible(False)

        self._log(self.tr("OK: {layers}").format(layers=", ".join(res["ok"]) or "-"))
        for sid, msg in res["falhou"]:
            self._log(self.tr("FAILED {id}: {error}").format(id=sid, error=msg))
        for sid, msg in res["pulou"]:
            self._log(self.tr("SKIPPED {id}: {reason}").format(id=sid, reason=msg))

        if osm_vias_selecionada:
            self._iniciar_osm_vias(code, nome, gpkg, force=self.chk_atualizar.isChecked())

    def _iniciar_osm_vias(self, code, nome, gpkg, force):
        """Resolve o município na thread principal e despacha
        `OsmNetworkTask` — Passo 3 do plano `osm_qgstask`."""
        if self._task_osm is not None:
            # Guarda contra clique duplo em "Load selected": o botão volta a
            # ficar habilitado no `finally` do trecho síncrono antes da task
            # de OSM terminar. Sem esta checagem, despachar uma segunda task
            # aqui sobrescreveria `self._task_osm`, deixando a primeira
            # órfã (ninguém recebe `concluida`) e as duas gravando no MESMO
            # GeoPackage ao mesmo tempo.
            self._log(self.tr("SKIPPED osm_vias: a road network load is already in progress"))
            return

        municipio, bbox, mun_geom = osm_pipeline.resolve_municipio(code, nome)
        if municipio is None:
            self._log(self.tr("FAILED osm_vias: {error}").format(
                error=self.tr("could not resolve the municipality")), focar=True)
            self.progress_bar.setVisible(False)
            self.btn_cancelar.setVisible(False)
            return

        existentes = diagnostico._layers_existentes(gpkg)
        if (not force) and osm_pipeline.osm_vias_ja_existe(existentes, code):
            self._log(self.tr(
                "SKIPPED osm_vias: already in the GeoPackage (osm_links_{code}/osm_nodes_{code})"
            ).format(code=code))
            self.progress_bar.setVisible(False)
            self.btn_cancelar.setVisible(False)
            return

        self._log(self.tr("OSM: downloading road network in the background..."))
        self._osm_code, self._osm_nome, self._osm_gpkg = code, nome, gpkg
        cache_dir = os.path.dirname(gpkg) or "."

        task = OsmNetworkTask(
            self.tr("OSM road network - {code}").format(code=code),
            code, nome, bbox, mun_geom, cache_dir=cache_dir, force=force)
        task.mensagem.connect(self._log)
        task.progressChanged.connect(self._on_osm_progress)
        task.concluida.connect(self._on_osm_concluida)
        self._task_osm = task
        QgsApplication.taskManager().addTask(task)

    def _on_osm_progress(self, pct):
        self.progress_bar.setValue(int(pct))

    def _on_osm_concluida(self, dados):
        """Roda na thread principal (sinal `concluida` de `OsmNetworkTask`,
        emitido por `finished()`): monta as camadas, grava no GeoPackage,
        adiciona ao projeto e loga — o mesmo que o ramo `osm_vias` de
        `carregar_fontes` faz hoje no caminho síncrono."""
        self.progress_bar.setVisible(False)
        self.btn_cancelar.setVisible(False)
        task = self._task_osm
        self._task_osm = None
        code, nome, gpkg = self._osm_code, self._osm_nome, self._osm_gpkg

        if dados is None:
            if task is not None and task.isCanceled():
                self._log(self.tr("SKIPPED osm_vias: cancelled by the user"))
            elif task is not None and getattr(task, "sem_vias", False):
                # Paridade com o caminho síncrono de `carregar_fontes`:
                # "nenhuma via no bbox" é SKIPPED, não FAILED, não importa
                # qual trilha rodou.
                self._log(self.tr("SKIPPED osm_vias: {reason}").format(reason=task.erro))
            else:
                erro = getattr(task, "erro", None) if task is not None else None
                self._log(self.tr("FAILED osm_vias: {error}").format(
                    error=erro or self.tr("unknown error")), focar=True)
            return

        layers = osm_pipeline.montar_camadas(dados)
        osm_links = layers.get("osm_links")
        osm_nodes = layers.get("osm_nodes")
        osm_problemas = layers.get("osm_problemas")
        if osm_links is None or osm_nodes is None:
            metadata = dados.get("metadata", {})
            self._log(self.tr("FAILED osm_vias: {error}").format(
                error=metadata.get("erro") or self.tr("unknown error")), focar=True)
            return

        ok_links, _ = diagnostico._grava_gpkg(osm_links, gpkg, "osm_links_{}".format(code))
        ok_nodes, _ = diagnostico._grava_gpkg(osm_nodes, gpkg, "osm_nodes_{}".format(code))
        ok_problemas = True
        if osm_problemas is not None:
            ok_problemas, _ = diagnostico._grava_gpkg(osm_problemas, gpkg, "osm_problemas_{}".format(code))
        if not (ok_links and ok_nodes and ok_problemas):
            self._log(self.tr("FAILED osm_vias: {error}").format(
                error=self.tr("failed to write to the GeoPackage")), focar=True)
            return

        # Carregar DO GPKG, não da memory — mesma disciplina de `carregar_fontes`.
        osm_links_gpkg = QgsVectorLayer(
            "{}|layername=osm_links_{}".format(gpkg, code), "osm_links - {}".format(nome or code), "ogr")
        osm_nodes_gpkg = QgsVectorLayer(
            "{}|layername=osm_nodes_{}".format(gpkg, code), "osm_nodes - {}".format(nome or code), "ogr")
        if osm_links_gpkg.isValid():
            QgsProject.instance().addMapLayer(osm_links_gpkg)
            self._log("OK: osm_links (GPKG)")
        if osm_nodes_gpkg.isValid():
            QgsProject.instance().addMapLayer(osm_nodes_gpkg)
            self._log("OK: osm_nodes (GPKG)")
        if osm_problemas is not None:
            osm_problemas_gpkg = QgsVectorLayer(
                "{}|layername=osm_problemas_{}".format(gpkg, code), "osm_problemas - {}".format(nome or code), "ogr")
            if osm_problemas_gpkg.isValid():
                QgsProject.instance().addMapLayer(osm_problemas_gpkg)
                self._log("OK: osm_problemas (GPKG)")

    def _on_cancelar(self):
        if self._feedback_atual is not None:
            self._feedback_atual.cancel()
        if self._task_osm is not None:
            self._task_osm.cancel()
        self.btn_cancelar.setEnabled(False)
