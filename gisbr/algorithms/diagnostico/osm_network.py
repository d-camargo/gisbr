# -*- coding: utf-8 -*-
"""Algoritmo `gisbr:osm_network`: rede viária municipal OSM (links/nós/problemas).

Expõe `build_osm_network_layers` (o núcleo do motor de diagnóstico, ver
`core/osm_pipeline.py`) como algoritmo do Processing Provider — a porta que
faltava para outro plugin (ex.: o logis) consumir a mesma rede/topologia via
`processing.run("gisbr:osm_network", {...})` em vez de copiar o pipeline
inteiro (ver Plano — Por que).

Espelha `export_poi_gmns.py` (tr/createInstance/name/displayName/group/
groupId/shortHelpString), o modelo de algoritmo do grupo Diagnóstico.
"""
from pathlib import Path

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeatureSink,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QCoreApplication

from ...core import osm_pipeline
from ...core.osm_pipeline import _LINK_FIELDS, _NODE_FIELDS, _PROBLEMA_FIELDS, _fields

_WKB_POR_GEOMETRIA = {
    "LineString": QgsWkbTypes.Type.LineString,
    "Point": QgsWkbTypes.Type.Point,
}


class OsmNetwork(QgsProcessingAlgorithm):
    """Rede viária municipal OSM: arcos com topologia real, nós e a
    verificação geométrica/topológica (`osm_problemas`), sem gravar GPKG."""

    CODE = "CODE"
    FORCE = "FORCE"
    CACHE_DIR = "CACHE_DIR"
    LINKS = "LINKS"
    NODES = "NODES"
    PROBLEMAS = "PROBLEMAS"

    def tr(self, string):
        return QCoreApplication.translate("OsmNetwork", string)

    def createInstance(self):
        return OsmNetwork()

    def name(self):
        return "osm_network"

    def displayName(self):
        return self.tr("OSM road network (municipality)")

    def group(self):
        return self.tr("Diagnóstico")

    def groupId(self):
        return "diagnostico"

    def shortHelpString(self):
        return self.tr(
            "Downloads the OSM road network of a Brazilian municipality via "
            "Overpass and builds the links/nodes/problems layers with the "
            "real OSM topology (same core as the diagnostic panel, "
            "gisbr/core/osm_pipeline.py), without writing to a GeoPackage. "
            "Links carry cost attributes (maxspeed, velocidade_kmh, "
            "comprimento_m) for routing consumers such as the logis plugin."
        )

    def flags(self):
        # O nucleo chama processing.run("gisbr:read_municipality") e mexe
        # em objetos QGIS (QgsVectorLayer, QgsGeometry) fora de uma thread
        # de fundo segura — rodar isto numa QgsTask nao e seguro hoje (Passo
        # 6, DECISAO de nao usar QgsTask agora). FlagNoThreading mantem o
        # algoritmo na thread principal do Processing.
        return QgsProcessingAlgorithm.flags(self) | QgsProcessingAlgorithm.Flag.FlagNoThreading

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(
                self.CODE,
                self.tr("Municipality IBGE code (7 digits)"),
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.FORCE,
                self.tr("Force refresh (ignore Overpass cache)"),
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                self.CACHE_DIR,
                self.tr("Overpass cache folder (optional; default: ~/.cache/gisbr-diagnostico)"),
                behavior=QgsProcessingParameterFile.Behavior.Folder,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.LINKS, self.tr("Links (osm_links)"))
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.NODES, self.tr("Nodes (osm_nodes)"))
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.PROBLEMAS, self.tr("Problems (osm_problemas)"))
        )

    def _cria_sink(self, parameters, param_name, context, campos, geometria):
        fields = _fields(campos)
        wkb_type = _WKB_POR_GEOMETRIA[geometria]
        crs = QgsCoordinateReferenceSystem("EPSG:4674")
        sink, dest_id = self.parameterAsSink(parameters, param_name, context, fields, wkb_type, crs)
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, param_name))
        return sink, dest_id

    def _copia_para_sink(self, layer, sink, feedback):
        if layer is None:
            return 0
        copiadas = 0
        for feat in layer.getFeatures():
            if feedback is not None and feedback.isCanceled():
                break
            sink.addFeature(feat, QgsFeatureSink.Flag.FastInsert)
            copiadas += 1
        return copiadas

    def processAlgorithm(self, parameters, context, feedback):
        code = (self.parameterAsString(parameters, self.CODE, context) or "").strip()
        if not code:
            raise QgsProcessingException(self.tr("Municipality IBGE code is required."))
        force = self.parameterAsBool(parameters, self.FORCE, context)
        cache_dir_str = self.parameterAsFile(parameters, self.CACHE_DIR, context)
        cache_dir = Path(cache_dir_str) if cache_dir_str else None

        result = osm_pipeline.build_osm_network_layers(
            code, cache_dir=cache_dir, force=force, feedback=feedback
        )
        metadata = result.get("metadata", {})
        layers = result.get("layers", {})

        erro = metadata.get("erro")
        if erro and not metadata.get("sem_vias"):
            # Nunca engolir: propaga a causa (Overpass ou município não
            # resolvido) como falha do algoritmo.
            raise QgsProcessingException(erro)
        if metadata.get("sem_vias"):
            feedback.pushWarning(erro or self.tr("No ways found for this municipality."))
        if metadata.get("cancelado"):
            feedback.pushInfo(self.tr("Cancelled by the user."))

        links_sink, links_id = self._cria_sink(parameters, self.LINKS, context, _LINK_FIELDS, "LineString")
        nodes_sink, nodes_id = self._cria_sink(parameters, self.NODES, context, _NODE_FIELDS, "Point")
        problemas_sink, problemas_id = self._cria_sink(parameters, self.PROBLEMAS, context, _PROBLEMA_FIELDS, "Point")

        n_links = self._copia_para_sink(layers.get("osm_links"), links_sink, feedback)
        n_nodes = self._copia_para_sink(layers.get("osm_nodes"), nodes_sink, feedback)
        n_problemas = self._copia_para_sink(layers.get("osm_problemas"), problemas_sink, feedback)

        # mesmo resumo por rede que o motor do diagnostico ja loga
        verificacao = metadata.get("verificacao") or {}
        for rede_nome in ("veicular", "pedestre"):
            contagem = verificacao.get(rede_nome)
            if contagem:
                feedback.pushInfo(self.tr("Verification ({rede}) — {resumo}").format(
                    rede=rede_nome,
                    resumo=", ".join("{}: {}".format(k, v) for k, v in sorted(contagem.items()))))
            elif contagem is not None:
                feedback.pushInfo(self.tr("Verification ({rede}) — no issues found").format(rede=rede_nome))

        feedback.pushInfo(self.tr("Done: {links} link(s), {nodes} node(s), {problemas} problem(s).").format(
            links=n_links, nodes=n_nodes, problemas=n_problemas))

        return {self.LINKS: links_id, self.NODES: nodes_id, self.PROBLEMAS: problemas_id}
