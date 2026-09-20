# -*- coding: utf-8 -*-
"""Testes unitarios do parser de agregados do IBGE (gisbr.core.agregados_parser)."""

import json
import pytest

from gisbr.core.agregados_parser import AgregadosParseError, parse_agregados_v3


@pytest.fixture
def ibge_v3_real_bytes():
    """Fixture real do passo 1 (secao 6 de ibge-agregados-acesso.md)."""
    return b"""[
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
              "nivel": {
                "id": "N6",
                "nome": "Municipio"
              },
              "nome": "Unai (MG)"
            },
            "serie": {
              "2023": "185000"
            }
          }
        ]
      }
    ]
  },
  {
    "id": "214",
    "variavel": "Quantidade produzida",
    "unidade": "Toneladas",
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
              "nivel": {
                "id": "N6",
                "nome": "Municipio"
              },
              "nome": "Unai (MG)"
            },
            "serie": {
              "2023": "699300"
            }
          }
        ]
      }
    ]
  },
  {
    "id": "215",
    "variavel": "Valor da producao",
    "unidade": "Mil Reais",
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
              "nivel": {
                "id": "N6",
                "nome": "Municipio"
              },
              "nome": "Unai (MG)"
            },
            "serie": {
              "2023": "1847725"
            }
          }
        ]
      }
    ]
  }
]"""


def test_parse_fixture_real(ibge_v3_real_bytes):
    rows = parse_agregados_v3(ibge_v3_real_bytes)
    assert len(rows) == 3
    assert rows[0] == (
        "109",
        "Area plantada",
        "Hectares",
        "Soja (em grao)",
        "2023",
        185000,
        "3170404",
    )
    assert rows[1] == (
        "214",
        "Quantidade produzida",
        "Toneladas",
        "Soja (em grao)",
        "2023",
        699300,
        "3170404",
    )
    assert rows[2] == (
        "215",
        "Valor da producao",
        "Mil Reais",
        "Soja (em grao)",
        "2023",
        1847725,
        "3170404",
    )


@pytest.mark.parametrize(
    "code_str",
    ["-", "..", "...", "X", "x", ""],
)
def test_parse_codigos_especiais_regra_d4(code_str):
    payload = [
        {
            "id": "109",
            "variavel": "Area plantada",
            "unidade": "Hectares",
            "resultados": [
                {
                    "classificacoes": [],
                    "series": [
                        {
                            "serie": {
                                "2023": code_str,
                            }
                        }
                    ],
                }
            ],
        }
    ]
    raw_bytes = json.dumps(payload).encode("utf-8")
    rows = parse_agregados_v3(raw_bytes)
    assert len(rows) == 1
    val = rows[0][5]
    # Regra D4: -, .., ..., X e string vazia -> None, JAMAIS 0
    assert val is None
    assert val != 0


def test_parse_valores_numericos():
    payload = [
        {
            "id": "109",
            "variavel": "Area plantada",
            "unidade": "Hectares",
            "resultados": [
                {
                    "classificacoes": [],
                    "series": [
                        {
                            "serie": {
                                "2021": "100",
                                "2022": "100.5",
                                "2023": 200,
                            }
                        }
                    ],
                }
            ],
        }
    ]
    raw_bytes = json.dumps(payload).encode("utf-8")
    rows = parse_agregados_v3(raw_bytes)
    assert len(rows) == 3
    assert rows[0][5] == 100
    assert rows[1][5] == 100.5
    assert rows[2][5] == 200


def test_parse_html_cloudflare_raises_agregados_parse_error():
    html_body = b"""<!DOCTYPE html><html lang="en-US"><head><title>Just a moment...</title>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
</head><body>Cloudflare challenge</body></html>"""

    with pytest.raises(AgregadosParseError) as exc_info:
        parse_agregados_v3(html_body)

    msg = str(exc_info.value)
    assert "Corpo HTML" in msg or "Just a moment" in msg
    assert "JSON invalido" not in msg


def test_parse_html_erro_http_raises_agregados_parse_error():
    html_body = b"<html><head><title>403 Forbidden</title></head><body>Forbidden</body></html>"

    with pytest.raises(AgregadosParseError) as exc_info:
        parse_agregados_v3(html_body)

    msg = str(exc_info.value)
    assert "Corpo HTML" in msg or "403 Forbidden" in msg
    assert "JSON invalido" not in msg


def test_parse_texto_nao_json_raises_agregados_parse_error():
    text_body = b"Internal Server Error"

    with pytest.raises(AgregadosParseError) as exc_info:
        parse_agregados_v3(text_body)

    msg = str(exc_info.value)
    assert "Corpo de texto" in msg or "Internal Server Error" in msg
    assert "JSON invalido" not in msg


def test_parse_json_sem_resultados_retorna_lista_vazia():
    assert parse_agregados_v3(b"[]") == []
    assert parse_agregados_v3(b'[{"id": "109", "variavel": "Area plantada"}]') == []
    assert parse_agregados_v3(b'{"mensagem": "Sem dados"}') == []
