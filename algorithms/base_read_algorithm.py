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

from ..core import catalog
from ..core import loader
from ..core.constants import EPSG_GEOBR, normalize_uf


class BaseReadAlgorithm(QgsProcessingAlgorithm):
    """Base para os algoritmos de leitura do geobr (backend GPKG v1.7.0)."""

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

    # ------------------------------------------------------------------ infra
    def years(self):
        if self._years_cache is None:
            try:
                self._years_cache = catalog.available_years(self.GEO)
            except Exception:
                self._years_cache = []
        return self._years_cache

    def initAlgorithm(self, config=None):
        years = self.years()
        year_labels = [str(y) for y in years] if years else ["(catalogo indisponivel)"]
        default_idx = len(years) - 1 if years else 0  # ano mais recente

        self.addParameter(
            QgsProcessingParameterEnum(
                self.YEAR,
                "Ano",
                options=year_labels,
                defaultValue=default_idx,
            )
        )
        if self.SUPPORTS_CODE:
            self.addParameter(
                QgsProcessingParameterString(
                    self.CODE,
                    'Codigo / sigla ("all", "MG", 31, 3106200)',
                    defaultValue="all",
                    optional=True,
                )
            )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SIMPLIFIED,
                "Geometria simplificada (renderizacao rapida)",
                defaultValue=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, "Saida")
        )

    # ------------------------------------------------------------- processamento
    def processAlgorithm(self, parameters, context, feedback):
        years = self.years()
        if not years:
            raise QgsProcessingException(
                "Catalogo do geobr indisponivel. Verifique a conexao com a "
                "internet (metadado IPEA / mirror GitHub)."
            )

        year_idx = self.parameterAsEnum(parameters, self.YEAR, context)
        year = years[year_idx]
        simplified = self.parameterAsBool(parameters, self.SIMPLIFIED, context)
        code = "all"
        if self.SUPPORTS_CODE:
            code = (self.parameterAsString(parameters, self.CODE, context) or "all").strip()

        # 1) selecionar rows do metadado
        try:
            rows = catalog.select(self.GEO, year=year, simplified=simplified)
        except ValueError as exc:
            raise QgsProcessingException(str(exc))

        # 2) recorte por UF (quando a geografia e fatiada no metadado)
        uf_code, uf_abbrev = normalize_uf(code) if self.SUPPORTS_CODE else (None, None)
        rows = catalog.narrow_by_uf(rows, uf_code, uf_abbrev)
        feedback.pushInfo(
            f"{self.GEO} {year} | simplified={simplified} | "
            f"{len(rows)} arquivo(s) a baixar"
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
                    f"Falha no download de {row['download_path']}: {exc}"
                )
            layers.append(loader.load_layer(path, f"{self.GEO}_{i}"))
            feedback.setProgress(int((i + 1) / total * 70))

        if not layers:
            raise QgsProcessingException("Nenhuma camada carregada.")

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
            raise QgsProcessingException("Nao foi possivel criar a saida.")

        from qgis.core import QgsFeatureSink
        count = merged.featureCount()
        for j, feature in enumerate(merged.getFeatures()):
            if feedback.isCanceled():
                break
            sink.addFeature(feature, QgsFeatureSink.FastInsert)
            if count:
                feedback.setProgress(80 + int((j + 1) / count * 20))

        feedback.pushInfo(f"Concluido: {count} feicao(oes).")
        return {self.OUTPUT: dest_id}

    # ------------------------------------------------------------------ metadata
    def name(self):
        return self.FUNCTION_NAME

    def displayName(self):
        return self.DISPLAY_NAME or self.FUNCTION_NAME

    def group(self):
        return "Geografias (GPKG / v1.7.0)"

    def groupId(self):
        return "geobr_gpkg"

    def shortHelpString(self):
        base = (
            "Baixa dados espaciais oficiais do Brasil via geobr (IPEA), "
            "backend GPKG legacy (v1.7.0), em SIRGAS 2000 / EPSG:4674.\n\n"
        )
        return base + (self.HELP or "")

    def createInstance(self):
        return type(self)()
