# -*- coding: utf-8 -*-
"""join_censo — junta variaveis do censo (censobr) a uma camada de setores.

Recebe uma camada de setores censitarios do geobr (com `code_tract`) e um
dataset de setor do censobr (ano + dataset, ex.: 2010 / DomicilioRenda), baixa
o .parquet do censobr, le como tabela (loader_v2) e faz o join pela chave
`code_tract` via native:joinattributestable.

Criterio de pronto da Fase 2: setor do geobr + read_tracts(DomicilioRenda) ->
mapa coropletico de renda por setor, tudo dentro do QGIS.
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
)

from ..core import capabilities, catalog_censo, downloader, loader_v2

# fallback estatico (uniao de datasets) se o catalogo estiver offline
_FALLBACK_DATASETS = [
    "Basico", "Domicilio", "DomicilioRenda", "Entorno", "Instrucao",
    "Morador", "Pessoa", "PessoaRenda", "Pessoas", "Responsavel",
    "ResponsavelRenda", "Obitos", "Preliminares", "Indigenas", "Quilombolas",
]


class JoinCenso(QgsProcessingAlgorithm):
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
                self._datasets = list(_FALLBACK_DATASETS)
        return self._years, self._datasets

    def initAlgorithm(self, config=None):
        years, datasets = self._catalog()
        year_labels = [str(y) for y in years] if years else ["(censobr indisponivel)"]

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT, "Setores censitarios (geobr)"
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.YEAR, "Ano do censo", options=year_labels,
                defaultValue=(year_labels.index("2010") if "2010" in year_labels else 0),
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DATASET, "Dataset do censobr", options=datasets,
                defaultValue=(datasets.index("DomicilioRenda")
                              if "DomicilioRenda" in datasets else 0),
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.JOIN_FIELD, "Campo-chave (setor)",
                parentLayerParameterName=self.INPUT, defaultValue="code_tract",
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.PREFIX, "Prefixo nos campos do censo", defaultValue="censo_",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(self.OUTPUT, "Setores + censo")
        )

    def processAlgorithm(self, parameters, context, feedback):
        if capabilities.parquet_backend() is None:
            raise QgsProcessingException(capabilities.install_hint())

        years, datasets = self._catalog()
        if not years:
            raise QgsProcessingException("Catalogo do censobr indisponivel.")

        year = years[self.parameterAsEnum(parameters, self.YEAR, context)]
        dataset = datasets[self.parameterAsEnum(parameters, self.DATASET, context)]
        join_field = self.parameterAsString(parameters, self.JOIN_FIELD, context)
        prefix = self.parameterAsString(parameters, self.PREFIX, context) or ""

        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException("Camada de setores invalida.")
        if join_field not in [f.name() for f in source.fields()]:
            raise QgsProcessingException(
                f"Campo '{join_field}' nao existe na camada de setores."
            )

        # 1) resolver + baixar o dataset do censobr
        try:
            row = catalog_censo.select(year, dataset)
        except ValueError as exc:
            raise QgsProcessingException(str(exc))
        feedback.pushInfo(f"censobr: {row['file_name']}")
        try:
            path = downloader.fetch_asset(
                row["file_name"], row["download_url"], feedback=feedback
            )
        except Exception as exc:
            raise QgsProcessingException(f"Falha no download do censobr: {exc}")
        feedback.setProgress(40)

        # 2) ler como tabela (sem geometria)
        censo = loader_v2.read_parquet_layer(path, f"censo_{year}_{dataset}")
        if join_field not in [f.name() for f in censo.fields()]:
            raise QgsProcessingException(
                f"O dataset do censobr nao tem o campo-chave '{join_field}'. "
                f"Campos: {', '.join(f.name() for f in censo.fields())[:200]}..."
            )
        feedback.setProgress(55)

        # 3) normalizar a chave para TEXTO nos dois lados.
        # A chave do geobr costuma ser numerica (double) e a do censobr texto;
        # to_string(to_int(...)) leva ambos a "310620005000001" e elimina o
        # mismatch de tipo (e o ".0" do double) que zera o join.
        import processing  # lazy: plugin 'processing' so existe em runtime
        t_in = source.fields().field(join_field).typeName()
        t_ce = censo.fields().field(join_field).typeName()
        feedback.pushInfo(
            f"Normalizando chave para texto (setor={t_in}, censo={t_ce})..."
        )
        key = "__geobr_jk"
        formula = f'to_string(to_int("{join_field}"))'
        fc_params = {
            "FIELD_NAME": key, "FIELD_TYPE": 2,  # 2 = Texto (string)
            "FIELD_LENGTH": 40, "FIELD_PRECISION": 0,
            "FORMULA": formula, "OUTPUT": "memory:",
        }
        inp_norm = processing.run(
            "native:fieldcalculator",
            dict(fc_params, INPUT=parameters[self.INPUT]),
            context=context, feedback=feedback, is_child_algorithm=True,
        )["OUTPUT"]
        censo_norm = processing.run(
            "native:fieldcalculator",
            dict(fc_params, INPUT=censo),
            context=context, feedback=feedback, is_child_algorithm=True,
        )["OUTPUT"]

        # campos do censo a copiar (exclui a chave original e a auxiliar)
        from qgis.core import QgsProcessingUtils
        censo_lyr = QgsProcessingUtils.mapLayerFromString(censo_norm, context) \
            if isinstance(censo_norm, str) else censo_norm
        copy_fields = [
            f.name() for f in censo_lyr.fields()
            if f.name() not in (key, join_field)
        ]

        # 4) join pela chave normalizada
        feedback.pushInfo(f"Join por '{join_field}' (prefixo '{prefix}')...")
        res = processing.run(
            "native:joinattributestable",
            {
                "INPUT": inp_norm, "FIELD": key,
                "INPUT_2": censo_norm, "FIELD_2": key,
                "FIELDS_TO_COPY": copy_fields, "METHOD": 1,
                "DISCARD_NONMATCHING": False, "PREFIX": prefix,
                "OUTPUT": "memory:",
            },
            context=context, feedback=feedback, is_child_algorithm=True,
        )
        joined = res.get("JOINED_COUNT")
        unjoin = res.get("UNJOINABLE_COUNT")
        if joined is not None:
            feedback.pushInfo(f"Setores com censo: {joined} | sem match: {unjoin}")
            if joined == 0:
                feedback.pushWarning(
                    "Nenhum setor casou com o censo mesmo apos normalizar a "
                    "chave — confira se o campo-chave e o code_tract correto."
                )

        # 5) remove a coluna auxiliar e materializa no OUTPUT
        out = processing.run(
            "native:deletecolumn",
            {"INPUT": res["OUTPUT"], "COLUMN": [key],
             "OUTPUT": parameters[self.OUTPUT]},
            context=context, feedback=feedback, is_child_algorithm=True,
        )
        return {self.OUTPUT: out["OUTPUT"]}

    # ------------------------------------------------------------------ metadata
    def name(self):
        return "join_censo"

    def displayName(self):
        return "Juntar dados do censo (censobr) a setores"

    def group(self):
        return "Censo (censobr)"

    def groupId(self):
        return "censobr"

    def shortHelpString(self):
        return (
            "Junta variaveis do Censo (censobr) a uma camada de setores "
            "censitarios do geobr, pela chave 'code_tract'.\n\n"
            "Fluxo tipico: read_census_tract (geobr) -> esta ferramenta com "
            "ano=2010, dataset=DomicilioRenda -> mapa coropletico de renda.\n\n"
            "Requer backend Parquet (driver GDAL ou pyarrow). Os arquivos do "
            "censobr sao NACIONAIS; o join mantem apenas os setores da sua "
            "camada de entrada."
        )

    def createInstance(self):
        return JoinCenso()
