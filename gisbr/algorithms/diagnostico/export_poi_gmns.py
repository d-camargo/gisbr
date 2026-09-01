# -*- coding: utf-8 -*-
"""Algoritmo `gisbr:export_poi_gmns`: camada osm_pois_* → poi.csv (GMNS).

Escreve o CSV com o cabeçalho EXATO do osm2gmns (io/writefile.py:122) — é a
porta para rodar o grid2demand sobre a saída do GisBR (Rodada 10, D8/D10).
"""

import csv

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFileDestination,
)
from qgis.PyQt.QtCore import QCoreApplication

from ...core.poi_parser import POI_CSV_COLUNAS, linha_poi_csv

# campos que a camada osm_pois_* precisa ter para o export sair correto
CAMPOS_OBRIGATORIOS = ("poi_id", "osm_type", "osm_id", "name", "building",
                       "amenity", "way", "area", "area_ft2",
                       "centroid_lon", "centroid_lat")


class ExportPoiGmns(QgsProcessingAlgorithm):
    """Exporta a camada osm_pois_* no formato poi.csv do osm2gmns/grid2demand."""

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    def tr(self, string):
        return QCoreApplication.translate("ExportPoiGmns", string)

    def createInstance(self):
        return ExportPoiGmns()

    def name(self):
        return "export_poi_gmns"

    def displayName(self):
        return self.tr("Export POIs to GMNS / grid2demand poi.csv")

    def group(self):
        return self.tr("Diagnóstico")

    def groupId(self):
        return "diagnostico"

    def shortHelpString(self):
        return self.tr(
            "Exports an osm_pois_* layer to a poi.csv file with the exact "
            "column layout produced by osm2gmns, which grid2demand reads via "
            "load_network(). Columns: name, poi_id, osm_way_id, "
            "osm_relation_id, building, amenity, way, geometry, centroid, "
            "area, area_ft2 (area in m2, area_ft2 in square feet)."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("POI layer (osm_pois)"),
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr("poi.csv (GMNS)"),
                fileFilter="CSV (*.csv)",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        output_file = self.parameterAsFileOutput(parameters, self.OUTPUT, context)
        if not output_file:
            raise QgsProcessingException(self.tr("Invalid output file path."))

        nomes = [f.name() for f in source.fields()]
        faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in nomes]
        if faltando:
            raise QgsProcessingException(
                self.tr("Missing required field(s): {}. The input must be an "
                        "osm_pois_* layer from the GisBR diagnostic.").format(", ".join(faltando)))

        total = source.featureCount()
        if feedback:
            feedback.pushInfo(self.tr("Exporting {} POIs to {}...").format(total, output_file))

        escritas = 0
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=list(POI_CSV_COLUNAS))
            writer.writeheader()
            for i, feat in enumerate(source.getFeatures()):
                if feedback is not None:
                    if feedback.isCanceled():
                        break
                    if total and i % 100 == 0:
                        feedback.setProgress(int(i / total * 100))
                geom = feat.geometry()
                geometry_wkt = geom.asWkt() if geom and not geom.isEmpty() else ""
                attrs = {f.name(): feat[f.name()] for f in feat.fields()}
                writer.writerow(linha_poi_csv(attrs, geometry_wkt))
                escritas += 1

        if feedback:
            feedback.pushInfo(self.tr("Done: {} rows written to {}.").format(escritas, output_file))
        return {self.OUTPUT: output_file}
