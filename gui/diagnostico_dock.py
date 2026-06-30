# -*- coding: utf-8 -*-
"""Painel (dock) do diagnostico (ARQUITETURA.md §3.4).

Permite ao usuario escolher o municipio, selecionar as fontes de dados ativas,
definir o caminho de destino do GeoPackage e carregar os dados.
"""
from qgis.gui import QgsDockWidget
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QPushButton, QFileDialog,
    QLabel, QPlainTextEdit, QComboBox, QCompleter)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject
from ..core.sources import SOURCES
from ..core import diagnostico

_EIXO_NOMES = {
    "transportes": "1. Transportes",
    "saneamento": "2. Drenagem e Saneamento",
    "demografia": "3. Demografia",
    "ambiental": "4. Ambiental",
    "educacao": "5. Educacao",
    "saude": "6. Saude",
    "urbano": "7. Urbano",
    "pol-admin": "8. Politico-administrativo",
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
        super().__init__("GisBR — Diagnostico", parent)
        self.iface = iface
        self._munis = {}
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

        # 1.1) Estado (UF)
        layout.addWidget(QLabel("Estado (UF):"))
        self.cmb_uf = QComboBox()
        self.cmb_uf.addItem("— selecione —", "")
        for sig, nom in _UFS:
            self.cmb_uf.addItem("{} - {}".format(sig, nom), sig)
        self.cmb_uf.currentIndexChanged.connect(self._on_uf_changed)
        layout.addWidget(self.cmb_uf)

        # 1.2) Municipio
        layout.addWidget(QLabel("Municipio:"))
        self.cmb_muni = QComboBox()
        self.cmb_muni.currentIndexChanged.connect(self._on_muni_changed)
        self.cmb_muni.setEditable(True)
        self.cmb_muni.setInsertPolicy(QComboBox.NoInsert)
        _comp = self.cmb_muni.completer()
        _comp.setCompletionMode(QCompleter.PopupCompletion)
        _comp.setFilterMode(Qt.MatchContains)
        _comp.setCaseSensitivity(Qt.CaseInsensitive)
        layout.addWidget(self.cmb_muni)

        # 1.3) Codigo do Municipio (IBGE 7 digitos)
        layout.addWidget(QLabel("Codigo IBGE (opcional / preenchido pela selecao):"))
        self.ed_muni = QLineEdit()
        self.ed_muni.setPlaceholderText("Ex: 3106200")
        layout.addWidget(self.ed_muni)

        # 2) Arvore de fontes
        layout.addWidget(QLabel("Fontes de Dados:"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Eixos e Camadas")
        
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
                child_item.setFlags(child_item.flags() | Qt.ItemIsUserCheckable)
                child_item.setCheckState(0, Qt.Unchecked)
                child_item.setData(0, Qt.UserRole, s["id"])

        self.tree.expandAll()
        layout.addWidget(self.tree)

        # 3) Destino GeoPackage
        layout.addWidget(QLabel("Destino do GeoPackage:"))
        gpkg_layout = QHBoxLayout()
        self.ed_gpkg = QLineEdit()
        self.ed_gpkg.setPlaceholderText("Caminho para arquivo .gpkg")
        gpkg_layout.addWidget(self.ed_gpkg)
        btn_gpkg = QPushButton("...")
        btn_gpkg.clicked.connect(self._on_choose_gpkg)
        gpkg_layout.addWidget(btn_gpkg)
        layout.addLayout(gpkg_layout)

        # 4) Basemap satelite
        self.chk_satelite = QCheckBox("Adicionar imagem de satelite ao fundo")
        layout.addWidget(self.chk_satelite)

        self.chk_atualizar = QCheckBox("Atualizar bases ja baixadas (rebaixar)")
        layout.addWidget(self.chk_atualizar)

        # 5) Botao Carregar
        self.btn_carregar = QPushButton("Carregar selecionadas")
        self.btn_carregar.clicked.connect(self._on_carregar)
        layout.addWidget(self.btn_carregar)

        # 6) PlainTextEdit para log
        layout.addWidget(QLabel("Log de Execucao:"))
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        layout.addWidget(self.txt_log)

        self.setWidget(central)

    def _on_choose_gpkg(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Selecionar GeoPackage", "", "GeoPackage (*.gpkg)"
        )
        if path:
            self.ed_gpkg.setText(path)

    def _selected_source_ids(self):
        ids = []
        for i in range(self.tree.topLevelItemCount()):
            parent_item = self.tree.topLevelItem(i)
            for j in range(parent_item.childCount()):
                child = parent_item.child(j)
                if child.checkState(0) == Qt.Checked:
                    source_id = child.data(0, Qt.UserRole)
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
        self.txt_log.appendPlainText("Carregando municipios de {}...".format(uf))
        try:
            self._munis = self._listar_municipios(uf)
        except Exception as exc:
            self.txt_log.appendPlainText("Falha ao listar municipios: {}".format(exc))
            self.cmb_muni.blockSignals(False)
            return
        for code in sorted(self._munis, key=lambda c: self._munis[c][0]):
            self.cmb_muni.addItem(self._munis[code][0], code)
        self.cmb_muni.setCurrentIndex(-1)
        self.cmb_muni.blockSignals(False)
        self.txt_log.appendPlainText("{} municipios carregados.".format(len(self._munis)))

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
            raise ValueError("Municipio {} nao encontrado no geobr.".format(code_muni))
        nome = feats[0]["name_muni"]
        ext = layer.extent()
        return nome, (ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum())

    def _on_carregar(self):
        self.txt_log.clear()
        code = self.ed_muni.text().strip()
        gpkg = self.ed_gpkg.text().strip()
        ids = self._selected_source_ids()
        if not code or not gpkg or not ids:
            self.txt_log.appendPlainText("Informe municipio, GeoPackage e ao menos 1 fonte.")
            return
        try:
            if getattr(self, "_munis", None) and code in self._munis:
                nome, bbox = self._munis[code]
            else:
                nome, bbox = self._info_municipio(code)
        except Exception as exc:
            self.txt_log.appendPlainText("Falha ao resolver o municipio: {}".format(exc))
            return
        self.txt_log.appendPlainText("Municipio: {} ({})".format(nome, code))
        res = diagnostico.carregar_fontes(
            ids, code_muni=code, nome_muni=nome, bbox=bbox, gpkg_path=gpkg,
            add_basemap=self.chk_satelite.isChecked(),
            force=self.chk_atualizar.isChecked(), feedback=None)
        self.txt_log.appendPlainText("OK: {}".format(", ".join(res["ok"]) or "-"))
        for sid, msg in res["falhou"]:
            self.txt_log.appendPlainText("FALHOU {}: {}".format(sid, msg))
        for sid, msg in res["pulou"]:
            self.txt_log.appendPlainText("PULOU {}: {}".format(sid, msg))
