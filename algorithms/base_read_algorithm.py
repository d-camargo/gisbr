# -*- coding: utf-8 -*-
"""Classe-base dos algoritmos read_* (Processing Provider).

Cada geografia subclassa BaseReadAlgorithm definindo, no minimo, GEO e os
metadados de identificacao. Parametros comuns: YEAR, CODE, SIMPLIFIED, OUTPUT.
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterString,
    QgsProcessingParameterFeatureSink,
    QgsCoordinateReferenceSystem,
)
from qgis.PyQt.QtCore import QCoreApplication

from ..core import catalog
from ..core import loader
from ..core.constants import EPSG_GEOBR, normalize_uf

_DISPLAY_NAMES = {
    "read_country": QCoreApplication.translate("GisBR", "Country (Brazil)"),
    "read_region": QCoreApplication.translate("GisBR", "Large regions"),
    "read_state": QCoreApplication.translate("GisBR", "States (UF)"),
    "read_meso_region": QCoreApplication.translate("GisBR", "Mesoregions"),
    "read_micro_region": QCoreApplication.translate("GisBR", "Microregions"),
    "read_immediate_region": QCoreApplication.translate("GisBR", "Immediate regions"),
    "read_intermediate_region": QCoreApplication.translate("GisBR", "Intermediate regions"),
    "read_municipality": QCoreApplication.translate("GisBR", "Municipalities"),
    "read_municipal_seat": QCoreApplication.translate("GisBR", "Municipal seats"),
    "read_census_tract": QCoreApplication.translate("GisBR", "Census tracts"),
    "read_weighting_area": QCoreApplication.translate("GisBR", "Weighting areas"),
    "read_statistical_grid": QCoreApplication.translate("GisBR", "Statistical grid"),
    "read_neighborhood": QCoreApplication.translate("GisBR", "Neighborhoods"),
    "read_metro_area": QCoreApplication.translate("GisBR", "Metropolitan areas"),
    "read_urban_area": QCoreApplication.translate("GisBR", "Urbanized areas"),
    "read_pop_arrangements": QCoreApplication.translate("GisBR", "Population arrangements"),
    "read_biomes": QCoreApplication.translate("GisBR", "Biomes"),
    "read_amazon": QCoreApplication.translate("GisBR", "Legal Amazon"),
    "read_semiarid": QCoreApplication.translate("GisBR", "Semiarid"),
    "read_conservation_units": QCoreApplication.translate("GisBR", "Conservation units"),
    "read_indigenous_land": QCoreApplication.translate("GisBR", "Indigenous lands"),
    "read_disaster_risk_area": QCoreApplication.translate("GisBR", "Disaster risk areas"),
    "read_health_region": QCoreApplication.translate("GisBR", "Health regions"),
    "read_health_facilities": QCoreApplication.translate("GisBR", "Health facilities"),
    "read_schools": QCoreApplication.translate("GisBR", "Schools"),
    # so-v2 (used by base_read_v2_algorithm.py)
    "read_favela": QCoreApplication.translate("GisBR", "Favelas / communities"),
    "read_polling_places": QCoreApplication.translate("GisBR", "Polling places"),
    "read_quilombola_land": QCoreApplication.translate("GisBR", "Quilombola lands"),
}

_HELPS = {
    "read_country": QCoreApplication.translate("GisBR", "National boundary."),
    "read_region": QCoreApplication.translate("GisBR", "5 large regions of Brazil."),
    "read_state": QCoreApplication.translate("GisBR", "States / Federative Units. Filter by abbreviation (\"MG\"), code (31) or \"all\"."),
    "read_meso_region": QCoreApplication.translate("GisBR", "Mesoregions. Filter by state (abbreviation/code) or mesoregion code."),
    "read_micro_region": QCoreApplication.translate("GisBR", "Microregions. Filter by state (abbreviation/code) or microregion code."),
    "read_immediate_region": QCoreApplication.translate("GisBR", "Immediate geographic regions (IBGE)."),
    "read_intermediate_region": QCoreApplication.translate("GisBR", "Intermediate geographic regions (IBGE)."),
    "read_municipality": QCoreApplication.translate("GisBR", "Brazilian municipalities. Filter by state (abbreviation/code) or 7-digit municipality code."),
    "read_municipal_seat": QCoreApplication.translate("GisBR", "Municipal seats (points)."),
    "read_census_tract": QCoreApplication.translate("GisBR", "Census tracts. Filter by state (abbreviation/code) or 7-digit municipality code."),
    "read_weighting_area": QCoreApplication.translate("GisBR", "Weighting areas of the Census."),
    "read_statistical_grid": QCoreApplication.translate("GisBR", "Statistical grid (IBGE)."),
    "read_neighborhood": QCoreApplication.translate("GisBR", "Neighborhoods. Filter by 7-digit municipality code."),
    "read_metro_area": QCoreApplication.translate("GisBR", "Metropolitan areas."),
    "read_urban_area": QCoreApplication.translate("GisBR", "Urbanized areas (IBGE)."),
    "read_pop_arrangements": QCoreApplication.translate("GisBR", "Population arrangements (IBGE)."),
    "read_biomes": QCoreApplication.translate("GisBR", "Brazilian biomes."),
    "read_amazon": QCoreApplication.translate("GisBR", "Legal Amazon boundary."),
    "read_semiarid": QCoreApplication.translate("GisBR", "Semiarid boundary."),
    "read_conservation_units": QCoreApplication.translate("GisBR", "Conservation units (MMA)."),
    "read_indigenous_land": QCoreApplication.translate("GisBR", "Indigenous lands (FUNAI)."),
    "read_disaster_risk_area": QCoreApplication.translate("GisBR", "Disaster risk areas."),
    "read_health_region": QCoreApplication.translate("GisBR", "Health regions (DataSUS)."),
    "read_health_facilities": QCoreApplication.translate("GisBR", "Health facilities (CNES, points)."),
    "read_schools": QCoreApplication.translate("GisBR", "Schools (INEP, points). Filter by 7-digit municipality code."),
    # so-v2 (used by base_read_v2_algorithm.py)
    "read_favela": QCoreApplication.translate("GisBR", "Favelas and urban communities (IBGE 2022). v2 only."),
    "read_polling_places": QCoreApplication.translate("GisBR", "Polling places (TSE, points). v2 only."),
    "read_quilombola_land": QCoreApplication.translate("GisBR", "Quilombola territories (INCRA). v2 only."),
}


class BaseReadAlgorithm(QgsProcessingAlgorithm):
    """Base para os algoritmos de leitura do geobr (backend GPKG v1.7.0)."""

    def tr(self, string):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("BaseReadAlgorithm", string)

    YEAR = "YEAR"
    CODE = "CODE"
    SIMPLIFIED = "SIMPLIFIED"
    OUTPUT = "OUTPUT"

    # --- a ser definido pelas subclasses ---
    GEO = None                # valor da coluna `geo` no metadado
    FUNCTION_NAME = None       # ex.: "read_state" -> id "read_state"
    DISPLAY_NAME = None        # nome amigavel exibido
    CODE_COLUMN = None         # coluna numerica no gpkg p/ filtro (ex.: "code_muni")
    ABBREV_COLUMN = None       # coluna de sigla no gpkg (ex.: "abbrev_state")
    UF_SLICED = False          # metadado fatiado por UF (municipality, tract...)
    SUPPORTS_CODE = True       # se aceita filtro por UF/codigo
    HELP = ""                  # texto curto de ajuda

    # cache dos anos (preenchido sob demanda)
    _years_cache = None
    _years_error = None

    # ------------------------------------------------------------------ infra
    def years(self):
        if self._years_cache is None:
            try:
                self._years_cache = catalog.available_years(self.GEO)
            except Exception as exc:
                self._years_cache = []
                self._years_error = str(exc)
        return self._years_cache

    def initAlgorithm(self, config=None):
        years = self.years()
        year_labels = [str(y) for y in years] if years else [self.tr("(catalog unavailable)")]
        default_idx = len(years) - 1 if years else 0  # ano mais recente

        self.addParameter(
            QgsProcessingParameterEnum(
                self.YEAR,
                self.tr("Year"),
                options=year_labels,
                defaultValue=default_idx,
            )
        )
        if self.SUPPORTS_CODE:
            self.addParameter(
                QgsProcessingParameterString(
                    self.CODE,
                    self.tr('Code / abbreviation ("all", "MG", 31, 3106200)'),
                    defaultValue="all",
                    optional=True,
                )
            )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SIMPLIFIED,
                self.tr("Simplified geometry (faster rendering)"),
                defaultValue=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Output"))
        )

    # ------------------------------------------------------------- processamento
    def processAlgorithm(self, parameters, context, feedback):
        years = self.years()
        if not years:
            message = self.tr(
                "geobr catalog unavailable. Verify your internet connection "
                "(IPEA metadata / GitHub mirror)."
            )
            if self._years_error:
                message = "{message} (causa: {cause})".format(
                    message=message, cause=self._years_error
                )
            raise QgsProcessingException(message)

        year_idx = self.parameterAsEnum(parameters, self.YEAR, context)
        year = years[year_idx]
        simplified = self.parameterAsBool(parameters, self.SIMPLIFIED, context)
        code = "all"
        if self.SUPPORTS_CODE:
            code = (self.parameterAsString(parameters, self.CODE, context) or "all").strip()

        # 1) selecionar rows do metadado
        try:
            rows = catalog.select(self.GEO, year=year, simplified=simplified, feedback=feedback)
        except ValueError as exc:
            raise QgsProcessingException(str(exc))

        # 2) recorte por UF (quando a geografia e fatiada no metadado)
        uf_code, uf_abbrev = normalize_uf(code) if self.SUPPORTS_CODE else (None, None)
        rows = catalog.narrow_by_uf(rows, uf_code, uf_abbrev)
        feedback.pushInfo(
            self.tr("{geo} {year} | simplified={simplified} | {count} file(s) to download").format(
                geo=self.GEO, year=year, simplified=simplified, count=len(rows)
            )
        )

        # 3) baixar (cache + mirrors) e carregar cada arquivo
        from ..core import downloader
        layers = []
        total = len(rows)
        for i, row in enumerate(rows):
            if feedback.isCanceled():
                break
            try:
                path = downloader.fetch(row["download_path"], feedback=feedback)
            except Exception as exc:
                raise QgsProcessingException(
                    self.tr("Download failed for {url}: {error}").format(
                        url=row["download_path"], error=exc
                    )
                )
            layers.append(loader.load_layer(path, f"{self.GEO}_{i}"))
            feedback.setProgress(int((i + 1) / total * 70))

        if not layers:
            raise QgsProcessingException(self.tr("No layers loaded."))

        # 4) concatenar
        merged = loader.merge_layers(layers, context, feedback)
        feedback.setProgress(80)

        # 5) filtro fino por codigo/sigla (ex.: municipio de 7 digitos, UF...)
        if self.SUPPORTS_CODE and self.CODE_COLUMN:
            merged = loader.apply_code_filter(
                merged,
                code,
                self.CODE_COLUMN,
                abbrev_column=self.ABBREV_COLUMN,
                uf_sliced=self.UF_SLICED,
            )

        # 6) materializar no sink
        crs = QgsCoordinateReferenceSystem.fromEpsgId(EPSG_GEOBR)
        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            merged.fields(),
            merged.wkbType(),
            crs if not merged.crs().isValid() else merged.crs(),
        )
        if sink is None:
            raise QgsProcessingException(self.tr("Could not create output."))

        from qgis.core import QgsFeatureSink
        count = merged.featureCount()
        for j, feature in enumerate(merged.getFeatures()):
            if feedback.isCanceled():
                break
            sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)
            if count:
                feedback.setProgress(80 + int((j + 1) / count * 20))

        feedback.pushInfo(self.tr("Completed: {count} feature(s).").format(count=count))
        return {self.OUTPUT: dest_id}

    # ------------------------------------------------------------------ metadata
    def name(self):
        return self.FUNCTION_NAME

    def displayName(self):
        return _DISPLAY_NAMES.get(self.FUNCTION_NAME, self.DISPLAY_NAME or self.FUNCTION_NAME)

    def group(self):
        return self.tr("Geographies (GPKG / v1.7.0)")

    def groupId(self):
        return "geobr_gpkg"

    def shortHelpString(self):
        base = self.tr(
            "Downloads official spatial data of Brazil via geobr (IPEA), "
            "legacy GPKG backend (v1.7.0), in SIRGAS 2000 / EPSG:4674.\n\n"
        )
        help_text = _HELPS.get(self.FUNCTION_NAME, self.HELP or "")
        return base + help_text

    def createInstance(self):
        return type(self)()
