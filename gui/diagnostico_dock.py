# -*- coding: utf-8 -*-
"""Painel (dock) do diagnostico (ARQUITETURA.md §3.4).

Permite ao usuario escolher o municipio, selecionar as fontes de dados ativas,
definir o caminho de destino do GeoPackage e carregar os dados.
"""
from qgis.gui import QgsDockWidget
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QPushButton, QFileDialog,
    QLabel, QPlainTextEdit)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject
from ..core.sources import SOURCES
from ..core import diagnostico

_EIXO_NOMES = {
    "transportes": "1. Transportes",
    "saneamento": "2. Drenagem e Saneamento",
    "ambiental": "4. Ambiental"
}


class DiagnosticoDock(QgsDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__("GisBR — Diagnostico", parent)
        self.iface = iface
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

        # 1) Codigo do Municipio
        layout.addWidget(QLabel("Codigo do Municipio (IBGE 7 digitos):"))
        self.ed_muni = QLineEdit()
        self.ed_muni.setPlaceholderText("Ex: 3106200")
        layout.addWidget(self.ed_muni)

        # 2) Arvore de fontes
        layout.addWidget(QLabel("Fontes de Dados:"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Eixos e Camadas")
        
        # Agrupar fontes por eixo
        eixos_items = {}
        for s in SOURCES:
            if s.get("protocolo") == "basemap":
                continue
            eixo_id = s.get("eixo", "outros")
            if eixo_id not in eixos_items:
                eixo_nome = _EIXO_NOMES.get(eixo_id, eixo_id.capitalize())
                parent_item = QTreeWidgetItem(self.tree, [eixo_nome])
                eixos_items[eixo_id] = parent_item
            
            parent_item = eixos_items[eixo_id]
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
            nome, bbox = self._info_municipio(code)
        except Exception as exc:
            self.txt_log.appendPlainText("Falha ao resolver o municipio: {}".format(exc))
            return
        self.txt_log.appendPlainText("Municipio: {} ({})".format(nome, code))
        res = diagnostico.carregar_fontes(
            ids, code_muni=code, nome_muni=nome, bbox=bbox, gpkg_path=gpkg,
            add_basemap=self.chk_satelite.isChecked(), feedback=None)
        self.txt_log.appendPlainText("OK: {}".format(", ".join(res["ok"]) or "-"))
        for sid, msg in res["falhou"]:
            self.txt_log.appendPlainText("FALHOU {}: {}".format(sid, msg))
        for sid, msg in res["pulou"]:
            self.txt_log.appendPlainText("PULOU {}: {}".format(sid, msg))
