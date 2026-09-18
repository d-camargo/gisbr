# -*- coding: utf-8 -*-
"""Conector para a API v3 de Agregados do IBGE (dados tabulares do diagnostico).

Monta a URL da v3 a partir de (agregado, variaveis, classificacao, periodo, code_muni),
busca com QgsBlockingNetworkRequest + configure_request, inspeciona o corpo antes
de parsear (D2) e monta uma QgsVectorLayer sem geometria ("memory") com os resultados.
"""
from datetime import datetime
import urllib.parse

from qgis.core import QgsBlockingNetworkRequest, QgsFeature, QgsField, QgsVectorLayer
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from ..agregados_parser import AgregadosParseError, parse_agregados_v3
from ..qgis_compat import field_type
from ..ssl_support import configure_request

_UA = "GisBR-QGIS/0.3 (diagnostico Plano Diretor)"


def _stamp(layer, fonte):
    layer.setCustomProperty("data_extracao", datetime.now().strftime("%Y-%m-%d"))
    layer.setCustomProperty("fonte", fonte)
    return layer


def _invalid(layer_name, msg):
    layer = QgsVectorLayer("", layer_name, "memory")
    layer.error_msg = msg
    return layer


def build_url(agregado, code_muni, variaveis="all", periodo="-1", classificacao=None):
    """Monta a URL de requisicao para a API v3 de Agregados do IBGE.

    Exemplo:
      https://servicodados.ibge.gov.br/api/v3/agregados/1612/periodos/2023/variaveis/109|214?localidades=N6[3106200]&classificacao=81[all]
    """
    agregado_str = str(agregado)
    code_str = str(code_muni)
    periodo_str = str(periodo) if periodo is not None else "-1"

    if isinstance(variaveis, (list, tuple, set)):
        var_str = "|".join(str(v) for v in variaveis)
    elif variaveis:
        var_str = str(variaveis)
    else:
        var_str = "all"

    base = "https://servicodados.ibge.gov.br/api/v3/agregados/{}/periodos/{}/variaveis/{}".format(
        agregado_str, periodo_str, var_str
    )

    params = [("localidades", "N6[{}]".format(code_str))]

    if classificacao:
        if isinstance(classificacao, dict):
            cls_str = "|".join("{}[{}]".format(k, v) for k, v in classificacao.items())
        elif isinstance(classificacao, (list, tuple)):
            cls_str = "|".join(str(c) for c in classificacao)
        else:
            cls_str = str(classificacao)
        params.append(("classificacao", cls_str))

    return base + "?" + urllib.parse.urlencode(params, safe="[]|")


def fetch_layer(
    agregado,
    code_muni,
    layer_name,
    variaveis="all",
    periodo="-1",
    classificacao=None,
    feedback=None,
):
    """Requisita e constroi camada sem geometria (memory layer) com os agregados.

    Nao levanta excecoes. Em caso de erro HTTP/HTML/rede/parse, retorna uma
    QgsVectorLayer invalida com .error_msg contendo a causa.
    """
    url = build_url(
        agregado,
        code_muni,
        variaveis=variaveis,
        periodo=periodo,
        classificacao=classificacao,
    )
    host = QUrl(url).host()

    try:
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent", _UA.encode("utf-8"))
        configure_request(req)
        blocking = QgsBlockingNetworkRequest()
        blocking.get(req, True)
        reply = blocking.reply()
        data = bytes(reply.content()) if reply else b""

        if not data:
            err_msg = reply.errorString() if reply else ""
            return _invalid(
                layer_name,
                "Falha IBGE Agregados ({}, host: {}): resposta vazia ou erro de rede ({})".format(
                    agregado, host, err_msg or "sem conteudo"
                ),
            )

        rows = parse_agregados_v3(data)
    except AgregadosParseError as exc:
        return _invalid(
            layer_name,
            "Falha IBGE Agregados ({}, host: {}): {}".format(agregado, host, exc),
        )
    except Exception as exc:
        return _invalid(
            layer_name,
            "Falha IBGE Agregados ({}, host: {}): erro ao requisitar/parsear ({}: {})".format(
                agregado, host, type(exc).__name__, exc
            ),
        )

    uri = (
        "None?field=var_id:string&field=var_nome:string&field=unidade:string&"
        "field=produto:string&field=periodo:string&field=valor:double"
    )
    layer = QgsVectorLayer(uri, layer_name, "memory")

    if not layer.isValid():
        fields = [
            QgsField("var_id", field_type("string")),
            QgsField("var_nome", field_type("string")),
            QgsField("unidade", field_type("string")),
            QgsField("produto", field_type("string")),
            QgsField("periodo", field_type("string")),
            QgsField("valor", field_type("double")),
        ]
        layer = QgsVectorLayer("None", layer_name, "memory")
        dp = layer.dataProvider()
        dp.addAttributes(fields)
        layer.updateFields()

    features = []
    for var_id, var_nome, unidade, produto, periodo_val, valor in rows:
        feat = QgsFeature(layer.fields())
        feat.setAttributes([var_id, var_nome, unidade, produto, periodo_val, valor])
        features.append(feat)

    layer.dataProvider().addFeatures(features)
    layer.updateExtents()

    return _stamp(layer, "IBGE Agregados (API v3)")
