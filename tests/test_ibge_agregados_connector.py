# -*- coding: utf-8 -*-
"""Testes unitarios para o conector IBGE Agregados (gisbr.core.connectors.ibge_agregados)."""

import pytest
from gisbr.core.connectors.ibge_agregados import build_url, fetch_layer


def test_build_url_basico():
    url = build_url(1612, 3106200, variaveis=["109", "214"], periodo=2023, classificacao="81[all]")
    assert "https://servicodados.ibge.gov.br/api/v3/agregados/1612/periodos/2023/variaveis/109|214" in url
    assert "localidades=N6[3106200]" in url
    assert "classificacao=81[all]" in url


def test_build_url_defaults():
    url = build_url("6881", "3170404")
    assert "https://servicodados.ibge.gov.br/api/v3/agregados/6881/periodos/-1/variaveis/all" in url
    assert "localidades=N6[3170404]" in url
    assert "classificacao" not in url


def test_build_url_classificacao_dict():
    url = build_url(1612, 3106200, variaveis="109", periodo=2023, classificacao={"81": "2713"})
    assert "classificacao=81[2713]" in url


def test_fetch_layer_html_cloudflare_d2(monkeypatch):
    html_bytes = b"<!DOCTYPE html><html><head><title>Just a moment...</title></head><body>Cloudflare</body></html>"

    class DummyReply:
        def content(self):
            return html_bytes
        def errorString(self):
            return ""

    class DummyBlocking:
        def get(self, req, flag):
            pass
        def reply(self):
            return DummyReply()

    monkeypatch.setattr("gisbr.core.connectors.ibge_agregados.QgsBlockingNetworkRequest", DummyBlocking)

    layer = fetch_layer(1612, 3106200, "pam_temp")
    assert not layer.isValid()
    assert hasattr(layer, "error_msg")
    assert "servicodados.ibge.gov.br" in layer.error_msg
    assert "Corpo HTML recebido ('Just a moment...')" in layer.error_msg


def test_fetch_layer_sucesso_real_fixture(monkeypatch):
    json_bytes = b"""[
  {
    "id": "109",
    "variavel": "Area plantada",
    "unidade": "Hectares",
    "resultados": [
      {
        "classificacoes": [
          {
            "id": "81",
            "nome": "Produto das lavouras temporarias",
            "categoria": {
              "2713": "Soja (em grao)"
            }
          }
        ],
        "series": [
          {
            "localidade": {
              "id": "3170404",
              "nome": "Unai (MG)"
            },
            "serie": {
              "2023": "185000"
            }
          }
        ]
      }
    ]
  }
]"""

    class DummyReply:
        def content(self):
            return json_bytes
        def errorString(self):
            return ""

    class DummyBlocking:
        def get(self, req, flag):
            pass
        def reply(self):
            return DummyReply()

    monkeypatch.setattr("gisbr.core.connectors.ibge_agregados.QgsBlockingNetworkRequest", DummyBlocking)

    layer = fetch_layer(1612, 3170404, "pam_temp_unai", variaveis=["109"], periodo=2023, classificacao="81[2713]")
    assert layer.isValid()
    assert layer.featureCount() == 1
    assert layer.customProperty("fonte") == "IBGE Agregados (API v3)"
    assert layer.customProperty("data_extracao") is not None

    feat = next(layer.getFeatures())
    attrs = feat.attributes()
    # [var_id, var_nome, unidade, produto, periodo, valor]
    assert attrs[0] == "109"
    assert attrs[1] == "Area plantada"
    assert attrs[2] == "Hectares"
    assert attrs[3] == "Soja (em grao)"
    assert attrs[4] == "2023"
    assert attrs[5] == 185000.0


def test_fetch_layer_resposta_vazia(monkeypatch):
    class DummyReply:
        def content(self):
            return b""
        def errorString(self):
            return "Host not found"

    class DummyBlocking:
        def get(self, req, flag):
            pass
        def reply(self):
            return DummyReply()

    monkeypatch.setattr("gisbr.core.connectors.ibge_agregados.QgsBlockingNetworkRequest", DummyBlocking)

    layer = fetch_layer(1612, 3106200, "pam_temp")
    assert not layer.isValid()
    assert "Host not found" in layer.error_msg
    assert "servicodados.ibge.gov.br" in layer.error_msg
