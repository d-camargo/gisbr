# -*- coding: utf-8 -*-
"""Painel (dock) do diagnostico (ARQUITETURA.md §3.4).

Permite ao usuario escolher o municipio, selecionar as fontes de dados ativas,
definir o caminho de destino do GeoPackage e carregar os dados.
"""
from qgis.gui import QgsDockWidget
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QPushButton, QFileDialog,
    QLabel, QPlainTextEdit, QComboBox, QCompleter, QGroupBox, QListWidget,
    QListWidgetItem)
from qgis.PyQt.QtCore import Qt, QCoreApplication, QSettings
from qgis.core import QgsProject, QgsProcessingFeedback
from ..core.sources import SOURCES
from ..core import diagnostico, catalog_censo, censo_join


class _LogFeedback(QgsProcessingFeedback):
    """Feedback que espelha as mensagens do motor no log do painel.

    Sem isso o motor roda com feedback=None e avisos importantes (tamanho dos
    downloads do censobr, backend Parquet ausente, join que casou 0 setores)
    nunca chegam ao usuario do painel.
    """

    def __init__(self, log_widget):
        super().__init__()
        self._log = log_widget

    def pushInfo(self, message):
        self._log.appendPlainText(message)

    def pushWarning(self, message):
        self._log.appendPlainText(self.tr("Warning: {message}").format(message=message))

_EIXO_NOMES = {
    "transportes": QCoreApplication.translate("GisBR", "1. Transport"),
    "saneamento": QCoreApplication.translate("GisBR", "2. Drainage & Sanitation"),
    "demografia": QCoreApplication.translate("GisBR", "3. Demography"),
    "ambiental": QCoreApplication.translate("GisBR", "4. Environment"),
    "educacao": QCoreApplication.translate("GisBR", "5. Education"),
    "saude": QCoreApplication.translate("GisBR", "6. Health"),
    "urbano": QCoreApplication.translate("GisBR", "7. Urban"),
    "pol-admin": QCoreApplication.translate("GisBR", "8. Administrative"),
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


class DiagnosticoDock(QgsDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__(QCoreApplication.translate("GisBR", "GisBR — Diagnostic"), parent)
        self.iface = iface
        self._munis = {}
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

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

        # 5) Botao Carregar
        self.btn_carregar = QPushButton(self.tr("Load selected"))
        self.btn_carregar.clicked.connect(self._on_carregar)
        layout.addWidget(self.btn_carregar)

        # 6) PlainTextEdit para log
        layout.addWidget(QLabel(self.tr("Execution log:")))
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        layout.addWidget(self.txt_log)

        self._init_censo_ui()

        self.setWidget(central)

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
        self.txt_log.appendPlainText(self.tr("Loading municipalities of {uf}...").format(uf=uf))
        try:
            self._munis = self._listar_municipios(uf)
        except Exception as exc:
            self.txt_log.appendPlainText(self.tr("Failed to list municipalities: {error}").format(error=exc))
            self.cmb_muni.blockSignals(False)
            return
        for code in sorted(self._munis, key=lambda c: self._munis[c][0]):
            self.cmb_muni.addItem(self._munis[code][0], code)
        self.cmb_muni.setCurrentIndex(-1)
        self.cmb_muni.blockSignals(False)
        self.txt_log.appendPlainText(self.tr("{count} municipalities loaded.").format(count=len(self._munis)))

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
            self.txt_log.appendPlainText(
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
            self.txt_log.appendPlainText(self.tr("Specify municipality, GeoPackage and at least 1 source."))
            return
        censo_ano = None
        censo_datasets = ()
        if self.grp_censo.isChecked():
            if "geobr_setores" not in ids:
                self.txt_log.appendPlainText(
                    self.tr("Notice: the Census option only applies to census tracts ('geobr_setores').")
                )
            censo_ano = self.cmb_censo_ano.currentData()
            censo_datasets = tuple(self._get_checked_censo_datasets())
        try:
            if getattr(self, "_munis", None) and code in self._munis:
                nome, bbox = self._munis[code]
            else:
                nome, bbox = self._info_municipio(code)
        except Exception as exc:
            self.txt_log.appendPlainText(self.tr("Failed to resolve municipality: {error}").format(error=exc))
            return
        self.txt_log.appendPlainText(self.tr("Municipality: {name} ({code})").format(name=nome, code=code))
        res = diagnostico.carregar_fontes(
            ids, code_muni=code, nome_muni=nome, bbox=bbox, gpkg_path=gpkg,
            add_basemap=self.chk_satelite.isChecked(),
            force=self.chk_atualizar.isChecked(),
            feedback=_LogFeedback(self.txt_log),
            censo_ano=censo_ano, censo_datasets=censo_datasets)
        self.txt_log.appendPlainText(self.tr("OK: {layers}").format(layers=", ".join(res["ok"]) or "-"))
        for sid, msg in res["falhou"]:
            self.txt_log.appendPlainText(self.tr("FAILED {id}: {error}").format(id=sid, error=msg))
        for sid, msg in res["pulou"]:
            self.txt_log.appendPlainText(self.tr("SKIPPED {id}: {reason}").format(id=sid, reason=msg))
