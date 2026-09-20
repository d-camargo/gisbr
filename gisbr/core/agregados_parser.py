# -*- coding: utf-8 -*-
"""Parser stdlib puro para respostas da API v3 de Agregados do IBGE."""

import json
import re
from typing import Any, List, Optional, Tuple, Union

# Codigos especiais de estatistica oficial brasileira que representam ausencia de valor numerico
# D4 / D15: "-", "..", "...", "X" e string vazia -> None (JAMAIS 0)
SPECIAL_NONE_CODES = {"-", "..", "...", "X", "x", ""}


class AgregadosParseError(Exception):
    """Excecao lancada quando a resposta da API de Agregados nao e um JSON valido."""

    pass


def _parse_valor(raw_val: Any) -> Optional[Union[int, float]]:
    """Converte valor bruto da API para numerico (int/float) ou None se for codigo especial.

    Regra D4/D15: '-', '..', '...', 'X' e '' -> None, JAMAIS 0.
    """
    if raw_val is None:
        return None

    if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool):
        return raw_val

    s_val = str(raw_val).strip()

    if s_val in SPECIAL_NONE_CODES:
        return None

    # Trata possivel sufixo de estimativa '*'
    cleaned = s_val.rstrip("*").strip()
    if not cleaned or cleaned in SPECIAL_NONE_CODES:
        return None

    try:
        return int(cleaned)
    except ValueError:
        try:
            return float(cleaned)
        except ValueError:
            return None


def parse_agregados_v3(
    raw_bytes: bytes,
) -> List[Tuple[str, str, str, str, str, Optional[Union[int, float]]]]:
    """Parseia resposta em bytes da API v3 de Agregados do IBGE.

    Args:
        raw_bytes: Conteudo binario da resposta HTTP.

    Returns:
        Lista de tuplas (variavel_id, variavel_nome, unidade, produto, periodo, valor).

    Raises:
        AgregadosParseError: Se o corpo nao for JSON (ex: HTML Cloudflare, erro HTTP).
    """
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise AgregadosParseError("Entrada deve ser do tipo bytes")

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("latin-1")
        except Exception as e:
            raise AgregadosParseError(
                f"Corpo binario nao-decodificavel ({type(e).__name__})"
            ) from e

    stripped = text.strip()

    # (b) Corpo que nao e JSON (HTML da Cloudflare, pagina de erro)
    if (
        stripped.startswith("<")
        or "<html" in stripped.lower()
        or "<!doctype html" in stripped.lower()
    ):
        match = re.search(
            r"<title>(.*?)</title>", stripped, re.IGNORECASE | re.DOTALL
        )
        if match:
            title = match.group(1).strip()
            raise AgregadosParseError(
                f"Corpo HTML recebido ('{title}') ao inves de JSON v3 da API de Agregados"
            )
        raise AgregadosParseError(
            "Corpo HTML recebido (ex: Cloudflare challenge ou pagina de erro) ao inves de JSON v3 da API de Agregados"
        )

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        snippet = stripped[:80].replace("\n", " ")
        raise AgregadosParseError(
            f"Corpo de texto nao-JSON recebido ('{snippet}') ao inves de JSON v3 da API de Agregados"
        ) from e

    lines: List[Tuple[str, str, str, str, str, Optional[Union[int, float]]]] = []

    # (c) Resposta JSON valida mas sem resultados -> lista vazia
    var_items = (
        data
        if isinstance(data, list)
        else [data]
        if isinstance(data, dict)
        else []
    )

    for item in var_items:
        if not isinstance(item, dict):
            continue

        var_id = str(item.get("id", ""))
        var_nome = str(item.get("variavel", ""))
        unidade = str(item.get("unidade", ""))

        resultados = item.get("resultados")
        if not isinstance(resultados, list):
            continue

        for res in resultados:
            if not isinstance(res, dict):
                continue

            # Extrai nome do produto/categoria se houver
            prod_names = []
            for cls in res.get("classificacoes", []):
                if isinstance(cls, dict):
                    cat = cls.get("categoria")
                    if isinstance(cat, dict):
                        prod_names.extend(str(v) for v in cat.values())
            produto = ", ".join(prod_names) if prod_names else ""

            series_list = res.get("series")
            if not isinstance(series_list, list):
                continue

            for ser in series_list:
                if not isinstance(ser, dict):
                    continue

                loc = ser.get("localidade")
                loc_id = (
                    str(loc.get("id"))
                    if isinstance(loc, dict) and loc.get("id") is not None
                    else ""
                )

                serie_dict = ser.get("serie")
                if not isinstance(serie_dict, dict):
                    continue

                for periodo, raw_val in serie_dict.items():
                    valor = _parse_valor(raw_val)
                    lines.append(
                        (
                            var_id,
                            var_nome,
                            unidade,
                            produto,
                            str(periodo),
                            valor,
                            loc_id,
                        )
                    )

    return lines
