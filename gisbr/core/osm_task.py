# -*- coding: utf-8 -*-
"""`OsmNetworkTask`: calcula a rede viária OSM em segundo plano (`QgsTask`).

`run()` chama `compute_osm_network` (`core/osm_pipeline.py`) — dados puros,
nenhuma `QgsVectorLayer`/`QgsProject` aqui dentro, porque nenhuma das duas
é segura fora da thread principal do Qt. `bbox`/`mun_geom` chegam JÁ
resolvidos pela thread principal (`osm_pipeline.resolve_municipio`, chamado
pelo painel ANTES de despachar a task — ver `gui/diagnostico_dock.py`).
Quem monta as camadas é o painel, na thread principal, depois que
`finished()` emite o sinal `concluida`.
"""
from qgis.core import QgsProcessingFeedback, QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from .osm_pipeline import compute_osm_network


class _TaskFeedback(QgsProcessingFeedback):
    """Adapta a task para a interface de `QgsProcessingFeedback` que
    `compute_osm_network` espera — sem tocar GUI: `setProgress` vira
    `self._task.setProgress` (dispara `progressChanged`, thread-safe via
    sinal Qt), `pushInfo`/`pushWarning` emitem `mensagem` (para o painel
    logar) e `isCanceled()` repassa para `self._task.isCanceled()`.
    """

    def __init__(self, task):
        super().__init__()
        self._task = task

    def setProgress(self, pct):
        super().setProgress(pct)
        self._task.setProgress(pct)

    def pushInfo(self, message):
        self._task.mensagem.emit(message)

    def pushWarning(self, message):
        self._task.mensagem.emit(message)

    def isCanceled(self):
        return self._task.isCanceled()


class OsmNetworkTask(QgsTask):
    """Roda `compute_osm_network` fora da thread principal.

    `self.dados` guarda o dict de dados puros devolvido por
    `compute_osm_network` no caminho feliz (`None` em falha ou
    cancelamento); `self.erro` guarda a mensagem de erro, quando houver
    (`metadata["erro"]`). `self.sem_vias` marca o caso "nenhuma via no bbox"
    (`metadata["sem_vias"]`) — paridade com o caminho síncrono de
    `carregar_fontes`, onde isso é "pulou", não "falhou": o painel usa esse
    sinal em `_on_osm_concluida` para logar SKIPPED em vez de FAILED.
    """

    mensagem = pyqtSignal(str)
    concluida = pyqtSignal(object)

    def __init__(self, descricao, code_muni, nome_muni, bbox, mun_geom,
                 cache_dir=None, force=False):
        super().__init__(descricao, QgsTask.Flag.CanCancel)
        self._code_muni = code_muni
        self._nome_muni = nome_muni
        self._bbox = bbox
        self._mun_geom = mun_geom
        self._cache_dir = cache_dir
        self._force = force
        self.dados = None
        self.erro = None
        self.sem_vias = False

    def run(self):
        if self.isCanceled():
            return False

        feedback = _TaskFeedback(self)
        dados = compute_osm_network(
            self._code_muni, self._nome_muni, self._bbox, self._mun_geom,
            cache_dir=self._cache_dir, force=self._force, feedback=feedback)

        if self.isCanceled():
            return False

        metadata = dados.get("metadata", {})
        if metadata.get("erro"):
            self.erro = metadata["erro"]
            if metadata.get("sem_vias"):
                self.sem_vias = True
            return False

        self.dados = dados
        return True

    def finished(self, result):
        # Roda na thread principal — é aqui, e só aqui, que o painel pode
        # seguramente montar QgsVectorLayer/QgsProject a partir de
        # `self.dados` (ver `osm_pipeline.montar_camadas`).
        self.concluida.emit(self.dados if result else None)
