# -*- coding: utf-8 -*-
"""Classe-base dos algoritmos read_*_v2 (backend Parquet / v2.0.0).

Diferencas em relacao ao v1.7.0 (GPKG):
  * dados em .parquet (lidos via driver GDAL nativo OU pyarrow — ver loader_v2);
  * arquivos NACIONAIS unicos (nao fatiados por UF) -> filtro por codigo e
    sempre pos-load;
  * catalogo via API de releases do GitHub (catalog_v2).

Gated: se nenhum backend Parquet estiver disponivel, o algoritmo aborta com a
mensagem de instalacao (capabilities.install_hint()).
"""

from qgis.core import (
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeatureSink,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterString,
    QgsProcessingParameterFeatureSink,
)

from ..core import capabilities, catalog_v2, downloader, loader_v2
from ..core.constants import normalize_uf
from .base_read_algorithm import _DISPLAY_NAMES, _HELPS


class BaseReadV2Algorithm(QgsProcessingAlgorithm):
    def tr(self, string):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("GisBR", string)

    YEAR = "YEAR"
    CODE = "CODE"
    SIMPLIFIED = "SIMPLIFIED"
    OUTPUT = "OUTPUT"

    # --- definido pelas subclasses ---
    GEO = None                 # token v2 (plural): "states", "municipalities"...
    FUNCTION_NAME = None        # id do algoritmo, ex.: "read_state_v2"
    DISPLAY_NAME = None
    CODE_COLUMN = None          # coluna numerica p/ filtro (national, pos-load)
    ABBREV_COLUMN = None        # coluna de sigla (ex.: "abbrev_state")
    SUPPORTS_CODE = True
    HELP = ""

    _years_cache = None

    def years(self):
        if self._years_cache is None:
            try:
                self._years_cache = catalog_v2.available_years(self.GEO)
            except Exception:
                self._years_cache = []
        return self._years_cache

    def initAlgorithm(self, config=None):
        years = self.years()
        labels = [str(y) for y in years] if years else [self.tr("(catalog v2 unavailable)")]
        self.addParameter(
            QgsProcessingParameterEnum(
                self.YEAR, self.tr("Year"), options=labels,
                defaultValue=(len(years) - 1 if years else 0),
            )
        )
        if self.SUPPORTS_CODE:
            self.addParameter(
                QgsProcessingParameterString(
                    self.CODE, self.tr('Code / abbreviation ("all", "MG", 31, 3106200)'),
                    defaultValue="all", optional=True,
                )
            )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SIMPLIFIED, self.tr("Simplified geometry"), defaultValue=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Output"))
        )

    # ------------------------------------------------------------- filtro
    def _filter_expression(self, fields, code):
        """Monta expressao de filtro (national, pos-load) ou None.

        ``fields`` e o QgsFields da camada (usado p/ checar tipo e quotar).
        """
        if not code or str(code).strip().lower() == "all":
            return None
        s = str(code).strip()
        digits = "".join(ch for ch in s if ch.isdigit())
        is_alpha = not digits and s.isalpha()
        names = [f.name() for f in fields]

        def eq(col, value):
            if fields.field(col).isNumeric():
                return f'"{col}" = {int(value)}'
            return f"\"{col}\" = '{value}'"

        if is_alpha and self.ABBREV_COLUMN in names:
            return f"\"{self.ABBREV_COLUMN}\" = '{s.upper()}'"
        if digits:
            # codigo de 2 digitos (UF) -> filtra estado pela sigla
            if len(digits) <= 2 and self.ABBREV_COLUMN in names:
                uf_code, uf_abbrev = normalize_uf(s)
                if uf_abbrev:
                    return f"\"{self.ABBREV_COLUMN}\" = '{uf_abbrev}'"
            # 7 digitos = municipio -> filtra code_muni (ex.: setores de BH)
            if len(digits) == 7 and "code_muni" in names:
                return eq("code_muni", digits)
            if self.CODE_COLUMN in names:
                return eq(self.CODE_COLUMN, digits)
        return None

    # ------------------------------------------------------------- processamento
    def processAlgorithm(self, parameters, context, feedback):
        backend = capabilities.parquet_backend()
        if backend is None:
            raise QgsProcessingException(capabilities.install_hint())
        feedback.pushInfo(self.tr("Parquet backend: {backend}").format(backend=backend))

        years = self.years()
        if not years:
            raise QgsProcessingException(
                self.tr("v2 catalog unavailable (geobr_prep_data releases on GitHub).")
            )
        year = years[self.parameterAsEnum(parameters, self.YEAR, context)]
        simplified = self.parameterAsBool(parameters, self.SIMPLIFIED, context)
        code = "all"
        if self.SUPPORTS_CODE:
            code = (self.parameterAsString(parameters, self.CODE, context) or "all").strip()

        try:
            rows = catalog_v2.select(self.GEO, year=year, simplified=simplified)
        except ValueError as exc:
            raise QgsProcessingException(str(exc))
        feedback.pushInfo(
            self.tr("{geo} {year} | simplified={simplified} | {count} file(s)").format(
                geo=self.GEO, year=year, simplified=simplified, count=len(rows)
            )
        )

        # download + carga
        layers = []
        for i, row in enumerate(rows):
            if feedback.isCanceled():
                break
            try:
                path = downloader.fetch_v2(
                    row["file_name"], row["download_url"], feedback=feedback
                )
            except Exception as exc:
                raise QgsProcessingException(
                    self.tr("Download failed for {url}: {error}").format(
                        url=row["file_name"], error=exc
                    )
                )
            layers.append(loader_v2.read_parquet_layer(path, f"{self.GEO}_{i}"))
            feedback.setProgress(int((i + 1) / len(rows) * 60))

        if not layers:
            raise QgsProcessingException(self.tr("No layers loaded."))

        from ..core.loader import merge_layers
        merged = merge_layers(layers, context, feedback)
        feedback.setProgress(70)

        # filtro pos-load por expressao (funciona em camada ogr e em memoria)
        expr_str = None
        if self.SUPPORTS_CODE and self.CODE_COLUMN:
            expr_str = self._filter_expression(merged.fields(), code)
        expression = QgsExpression(expr_str) if expr_str else None
        exp_ctx = QgsExpressionContext()
        if expression is not None:
            feedback.pushInfo(self.tr("Filter: {expr}").format(expr=expr_str))
            exp_ctx.appendScopes(
                QgsExpressionContextUtils.globalProjectLayerScopes(merged)
            )
            expression.prepare(exp_ctx)

        sink, dest_id = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            merged.fields(), merged.wkbType(), merged.crs(),
        )
        if sink is None:
            raise QgsProcessingException(self.tr("Could not create output."))

        total = merged.featureCount() or 0
        kept = 0
        for j, feature in enumerate(merged.getFeatures()):
            if feedback.isCanceled():
                break
            if expression is not None:
                exp_ctx.setFeature(feature)
                if not expression.evaluate(exp_ctx):
                    continue
            sink.addFeature(feature, QgsFeatureSink.FastInsert)
            kept += 1
            if total:
                feedback.setProgress(70 + int((j + 1) / total * 30))

        feedback.pushInfo(self.tr("Completed: {count} feature(s).").format(count=kept))
        return {self.OUTPUT: dest_id}

    # ------------------------------------------------------------------ metadata
    def name(self):
        return self.FUNCTION_NAME

    def displayName(self):
        base_name = self.FUNCTION_NAME.replace("_v2", "")
        translated_base = _DISPLAY_NAMES.get(base_name, self.DISPLAY_NAME or self.FUNCTION_NAME)
        return f"{translated_base} (v2)"

    def group(self):
        return self.tr("Geographies (Parquet / v2.0.0)")

    def groupId(self):
        return "geobr_parquet_v2"

    def shortHelpString(self):
        base = self.tr(
            "Parquet backend (v2.0.0): newer geobr catalog (ipea/geobr_prep_data), "
            "in SIRGAS 2000 / EPSG:4674. Reads via native GDAL Parquet driver OR pyarrow. "
            "National files (filtered by code and post-download).\n\n"
        )
        base_name = self.FUNCTION_NAME.replace("_v2", "")
        help_text = _HELPS.get(base_name, self.HELP or "")
        return base + help_text

    def createInstance(self):
        return type(self)()
