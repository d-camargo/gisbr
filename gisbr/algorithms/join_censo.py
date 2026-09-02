# -*- coding: utf-8 -*-
"""join_censo — junta variaveis do censo (censobr) a uma camada de setores.

Recebe uma camada de setores censitarios do geobr (com `code_tract`) e um
dataset de setor do censobr (ano + dataset, ex.: 2010 / DomicilioRenda), baixa
o .parquet do censobr, le como tabela (loader_v2) e faz o join pela chave
`code_tract` chamando censo_join.anexar_censo.

Criterio de pronto da Fase 2: setor do geobr + read_tracts(DomicilioRenda) ->
mapa coropletico de renda por setor, tudo dentro do QGIS.
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingUtils,
    QgsVectorLayer,
)

from ..core import capabilities, catalog_censo, censo_join
from ..core.censo_join import CensoJoinError
from ..core.constants import EPSG_GEOBR


class JoinCenso(QgsProcessingAlgorithm):
    def tr(self, string):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("JoinCenso", string)

    INPUT = "INPUT"
    YEAR = "YEAR"
    DATASET = "DATASET"
    JOIN_FIELD = "JOIN_FIELD"
    PREFIX = "PREFIX"
    OUTPUT = "OUTPUT"

    _years = None
    _datasets = None

    def _catalog(self):
        if self._years is None:
            try:
                self._years = catalog_censo.available_years()
                ds = set()
                for y in self._years:
                    ds.update(catalog_censo.available_datasets(y))
                self._datasets = sorted(ds)
            except Exception:
                self._years = []
                self._datasets = list(censo_join.DATASETS_FALLBACK)
        return self._years, self._datasets

    def initAlgorithm(self, config=None):
        years, datasets = self._catalog()
        year_labels = [str(y) for y in years] if years else [self.tr("(censobr unavailable)")]

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT, self.tr("Census tracts (geobr)")
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.YEAR, self.tr("Census year"), options=year_labels,
                defaultValue=(year_labels.index("2010") if "2010" in year_labels else 0),
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DATASET, self.tr("censobr dataset"), options=datasets,
                defaultValue=(datasets.index("DomicilioRenda")
                              if "DomicilioRenda" in datasets else 0),
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.JOIN_FIELD, self.tr("Join field (tract)"),
                parentLayerParameterName=self.INPUT, defaultValue="code_tract",
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.PREFIX, self.tr("Prefix for census fields"), defaultValue="censo_",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(self.OUTPUT, self.tr("Tracts + census"))
        )

    def processAlgorithm(self, parameters, context, feedback):
        if capabilities.parquet_backend() is None:
            raise QgsProcessingException(capabilities.install_hint())

        years, datasets = self._catalog()
        if not years:
            raise QgsProcessingException(self.tr("censobr catalog unavailable."))

        year = years[self.parameterAsEnum(parameters, self.YEAR, context)]
        dataset = datasets[self.parameterAsEnum(parameters, self.DATASET, context)]
        prefix = self.parameterAsString(parameters, self.PREFIX, context) or "censo_"

        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.tr("Invalid tracts layer."))

        try:
            res_layer, relatorio = censo_join.anexar_censo(
                layer,
                year,
                [dataset],
                code_muni=None,
                prefixo=prefix,
                descartar_join_vazio=False,
                context=context,
                feedback=feedback,
            )
        except CensoJoinError as exc:
            raise QgsProcessingException(str(exc))
        except Exception as exc:
            raise QgsProcessingException(str(exc))

        for info in relatorio.get("infos", []):
            feedback.pushInfo(info)
        for aviso in relatorio.get("avisos", []):
            feedback.pushWarning(aviso)

        if not relatorio.get("datasets_ok"):
            detalhe = relatorio["avisos"][-1] if relatorio["avisos"] else ""
            raise QgsProcessingException(
                self.tr("Census data could not be joined.") + (" " + detalhe if detalhe else "")
            )

        joined = relatorio.get("casados", 0)
        unjoin = relatorio.get("sem_par", 0)
        feedback.pushInfo(
            self.tr("Tracts with census: {joined} | without match: {unjoin}").format(
                joined=joined, unjoin=unjoin)
        )
        if joined == 0:
            feedback.pushWarning(
                self.tr(
                    "No tracts matched with the census even after normalizing the "
                    "key — check if the join field is the correct code_tract."
                )
            )

        if not isinstance(res_layer, QgsVectorLayer):
            res_layer = QgsProcessingUtils.mapLayerFromString(res_layer, context)
        if res_layer is None:
            raise QgsProcessingException(self.tr("Failed to join census data."))

        # materializa no sink (mesmo padrao do base_read_algorithm: aceita
        # memory:, TEMPORARY_OUTPUT, arquivo e definicao de saida do dialog)
        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            res_layer.fields(),
            res_layer.wkbType(),
            res_layer.crs() if res_layer.crs().isValid()
            else QgsCoordinateReferenceSystem.fromEpsgId(EPSG_GEOBR),
        )
        if sink is None:
            raise QgsProcessingException(self.tr("Could not create output."))

        from qgis.core import QgsFeatureSink
        for feature in res_layer.getFeatures():
            sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)
        return {self.OUTPUT: dest_id}

    # ------------------------------------------------------------------ metadata
    def name(self):
        return "join_censo"

    def displayName(self):
        return self.tr("Join census data (censobr) to tracts")

    def group(self):
        return self.tr("Census (censobr)")

    def groupId(self):
        return "censobr"

    def shortHelpString(self):
        return self.tr(
            "Joins Census variables (censobr) to a census tracts layer from geobr, "
            "using the 'code_tract' key.\n\n"
            "Typical workflow: read_census_tract (geobr) -> this tool with "
            "the desired table (e.g. DomicilioRenda)."
        )

    def createInstance(self):
        return JoinCenso()
