# -*- coding: utf-8 -*-
"""anexar_censo — junta dados tabulares do censobr (Censo IBGE) a uma camada de setores.

Motor desacoplado de QgsProcessingAlgorithm (D1): chamável pelo algoritmo
gisbr:join_censo, pelo motor do painel de diagnóstico (sem context) e por
scripts. Devolve (layer_resultante, relatorio).
"""

from qgis.core import QgsVectorLayer, QgsProcessingUtils

from . import capabilities, catalog_censo, downloader, loader_v2
from .loader_v2 import LoaderV2Error


class CensoJoinError(Exception):
    """Excecao levantada quando ocorre um erro fatal no join do censobr."""
    pass


DATASETS_FALLBACK = [
    "Basico", "Domicilio", "DomicilioRenda", "Entorno", "Instrucao",
    "Morador", "Pessoa", "PessoaRenda", "Pessoas", "Responsavel",
    "ResponsavelRenda", "Obitos", "Preliminares", "Indigenas", "Quilombolas",
]


def prefixo_de(dataset):
    """Retorna o prefixo padrao de coluna para um dataset: '<Dataset>_'."""
    return f"{dataset}_"


def filtro_censo(code_muni, colunas):
    """Retorna a tupla de filtro para loader_v2 ou None se code_muni for None.

    Se code_muni for fornecido:
    - Se 'code_muni' estiver em colunas: ("code_muni", code_muni, "igual")
    - Senao: ("code_tract", str(code_muni)[:7], "prefixo")
    - Se code_muni for None: None
    """
    if code_muni is None:
        return None
    if colunas and "code_muni" in colunas:
        return ("code_muni", code_muni, "igual")
    return ("code_tract", str(code_muni)[:7], "prefixo")


def anexar_censo(
    layer,
    ano,
    datasets,
    code_muni=None,
    prefixo=None,
    descartar_join_vazio=True,
    context=None,
    feedback=None,
):
    """Anexa dados tabulares do censobr a uma camada de setores censitarios.

    Devolve (layer_resultante, relatorio), onde relatorio e
    {"datasets_ok": [..], "casados": int, "sem_par": int,
     "infos": [str], "avisos": [str]}.
    """
    if capabilities.parquet_backend() is None:
        raise CensoJoinError(capabilities.install_hint())

    import processing

    relatorio = {
        "datasets_ok": [],
        "casados": 0,
        "sem_par": 0,
        "infos": [],
        "avisos": [],
    }

    def _run(alg, params):
        # Com context (algoritmo): child algorithm mantem a propriedade das
        # camadas no context do chamador. Sem context (painel/scripts): run
        # "puro", no qual o Processing cria um contexto interno e ja devolve
        # QgsVectorLayer nos resultados (o mesmo padrao do osm_pipeline).
        if context is not None:
            return processing.run(
                alg, params, context=context, feedback=feedback,
                is_child_algorithm=True,
            )
        return processing.run(alg, params)

    def _as_layer(out):
        if isinstance(out, QgsVectorLayer):
            return out
        if context is not None and isinstance(out, str):
            return QgsProcessingUtils.mapLayerFromString(out, context)
        return None

    camada_atual = layer

    for dataset in datasets:
        try:
            # 1. Catalogo
            try:
                row = catalog_censo.select(ano, dataset)
            except Exception as exc:
                relatorio["avisos"].append(
                    "censobr: erro no catalogo para dataset '{}': {}".format(dataset, exc)
                )
                continue

            # Tamanho antes de baixar (D10)
            file_name = row.get("file_name", "")
            size_bytes = row.get("size", 0)
            if size_bytes:
                relatorio["infos"].append(
                    "[censo] {} — {:.1f} MB (baixa uma vez; fica em cache)".format(
                        file_name, size_bytes / (1024.0 * 1024.0))
                )
            else:
                relatorio["infos"].append("[censo] {}".format(file_name))

            # 2. Download
            try:
                path = downloader.fetch_asset(
                    row["file_name"], row["download_url"], feedback=feedback
                )
            except Exception as exc:
                relatorio["avisos"].append(
                    "censobr: falha no download do dataset '{}': {}".format(dataset, exc)
                )
                continue

            # 3. Leitura com filtro (D3: tenta code_muni, cai para o prefixo de
            #    code_tract se a coluna nao existir no arquivo)
            try:
                censo = None
                if code_muni is not None:
                    try:
                        censo = loader_v2.read_parquet_layer(
                            path, "censo_{}_{}".format(ano, dataset),
                            filtro=filtro_censo(code_muni, ["code_muni"]),
                        )
                    except LoaderV2Error:
                        relatorio["infos"].append(
                            "censobr: coluna 'code_muni' ausente em '{}'; "
                            "filtrando pelo prefixo de 'code_tract'.".format(dataset)
                        )
                        censo = loader_v2.read_parquet_layer(
                            path, "censo_{}_{}".format(ano, dataset),
                            filtro=filtro_censo(code_muni, []),
                        )
                else:
                    censo = loader_v2.read_parquet_layer(
                        path, "censo_{}_{}".format(ano, dataset), filtro=None
                    )
            except Exception as exc:
                relatorio["avisos"].append(
                    "censobr: falha ao ler o dataset '{}': {}".format(dataset, exc)
                )
                continue

            # 4. Normalizacao da chave code_tract para texto nos dois lados
            #    (geobr v1 e double, censobr e string — medição com dados reais)
            key = "__geobr_jk"
            formula = 'to_string(to_int("code_tract"))'
            fc_params = {
                "FIELD_NAME": key,
                "FIELD_TYPE": 2,  # 2 = Texto (string)
                "FIELD_LENGTH": 40,
                "FIELD_PRECISION": 0,
                "FORMULA": formula,
                "OUTPUT": "memory:",
            }

            inp_norm = _run(
                "native:fieldcalculator",
                dict(fc_params, INPUT=camada_atual),
            )["OUTPUT"]

            censo_norm = _run(
                "native:fieldcalculator",
                dict(fc_params, INPUT=censo),
            )["OUTPUT"]

            censo_lyr = _as_layer(censo_norm)
            if censo_lyr is None:
                relatorio["avisos"].append(
                    "censobr: nao foi possivel resolver a tabela do dataset '{}'".format(dataset)
                )
                continue
            copy_fields = [
                f.name()
                for f in censo_lyr.fields()
                if f.name() not in (key, "code_tract")
            ]

            prefix_val = prefixo if prefixo is not None else prefixo_de(dataset)

            # 5. Join pela chave normalizada
            res = _run(
                "native:joinattributestable",
                {
                    "INPUT": inp_norm,
                    "FIELD": key,
                    "INPUT_2": censo_norm,
                    "FIELD_2": key,
                    "FIELDS_TO_COPY": copy_fields,
                    "METHOD": 1,
                    "DISCARD_NONMATCHING": False,
                    "PREFIX": prefix_val,
                    "OUTPUT": "memory:",
                },
            )

            joined = res.get("JOINED_COUNT") or 0
            unjoin = res.get("UNJOINABLE_COUNT") or 0

            if descartar_join_vazio and joined == 0:
                # D5: join que casou zero setor nao entra na camada —
                # camada cheia de NULL e erro disfarcado de sucesso.
                relatorio["avisos"].append(
                    "censobr: dataset '{}' casou 0 setores com a camada "
                    "(chaves de censos diferentes?); resultado descartado.".format(dataset)
                )
                continue

            relatorio["casados"] += joined
            relatorio["sem_par"] += unjoin

            # 6. Remove a coluna auxiliar
            out = _run(
                "native:deletecolumn",
                {
                    "INPUT": res["OUTPUT"],
                    "COLUMN": [key],
                    "OUTPUT": "memory:",
                },
            )["OUTPUT"]

            nova = _as_layer(out)
            if nova is None:
                relatorio["avisos"].append(
                    "censobr: nao foi possivel resolver o resultado do dataset '{}'".format(dataset)
                )
                continue

            camada_atual = nova
            relatorio["datasets_ok"].append(dataset)

        except Exception as exc:
            # D12: falha de um dataset nao derruba os outros — mas sempre
            # reporta a causa, nunca silenciosa.
            relatorio["avisos"].append(
                "censobr: falha ao processar dataset '{}': {}".format(dataset, exc)
            )
            continue

    camada_final = _as_layer(camada_atual)
    if camada_final is not None:
        n_cols = len(camada_final.fields())
        relatorio["infos"].append(
            "censobr: camada final com {} colunas.".format(n_cols)
        )
        if n_cols > 1000:
            relatorio["avisos"].append(
                "censobr: atencao — camada final com {} colunas (>1000), "
                "o que pode exceder limites do GeoPackage/SQLite.".format(n_cols)
            )

    return camada_atual, relatorio
