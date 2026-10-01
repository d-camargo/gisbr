# -*- coding: utf-8 -*-
"""Leitor e parser da composição de Macrorregiões de Saúde do DataSUS/Ministério da Saúde.

Módulo stdlib puro (sem PyQGIS).
"""

import csv
import os
from typing import Any, Dict, List, Optional, Tuple

from .constants import UF_CODE_TO_ABBREV

_DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "data", "macro_saude.csv"
)


class MacroSaudeError(RuntimeError):
    """Exceção lançada quando o arquivo de Macrorregiões de Saúde está ausente ou ilegível."""

    pass


_CACHE: Dict[str, Dict[str, Any]] = {}


def reset_cache() -> None:
    """Limpa o cache em memória (útil para testes)."""
    _CACHE.clear()


def _normalizar_uf(uf: Optional[Any]) -> Optional[str]:
    """Normaliza a sigla da UF."""
    if uf is None:
        return None
    s = str(uf).strip().upper()
    if not s:
        return None
    if s.isdigit() and int(s) in UF_CODE_TO_ABBREV:
        return UF_CODE_TO_ABBREV[int(s)]
    return s


def _carregar_dados(csv_path: Optional[str] = None) -> Dict[str, Any]:
    """Carrega e memoiza em memória a composição das Macrorregiões de Saúde do CSV.

    Args:
        csv_path: Caminho opcional para o arquivo CSV.

    Returns:
        Dict com estruturas pré-computadas {'macro_nomes': ..., 'macros_by_uf': ..., ...}.

    Raises:
        MacroSaudeError: Se o arquivo estiver ausente ou ilegível.
    """
    path = os.path.abspath(csv_path) if csv_path else os.path.abspath(_DEFAULT_CSV_PATH)
    if path in _CACHE:
        return _CACHE[path]

    if not os.path.exists(path):
        raise MacroSaudeError(
            f"Arquivo de macrorregiões de saúde não encontrado: '{path}'"
        )

    macro_nomes: Dict[str, str] = {}
    macro_ufs: Dict[str, str] = {}
    macros_by_uf: Dict[str, Dict[str, str]] = {}
    munis_by_macro: Dict[str, List[Tuple[str, str]]] = {}
    all_macros: Dict[str, str] = {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            header_found = False
            for line_idx, row in enumerate(reader, 1):
                if not row:
                    continue

                first_cell = row[0].strip()
                # Ignora linhas de comentário (#)
                if first_cell.startswith("#"):
                    continue

                if not header_found:
                    if first_cell == "code_muni":
                        header_found = True
                        continue
                    else:
                        raise MacroSaudeError(
                            f"Cabeçalho inválido no arquivo '{path}': esperava 'code_muni', obteve '{first_cell}'"
                        )

                if len(row) < 5:
                    continue

                code_muni = row[0].strip()
                nome_muni = row[1].strip()
                sigla_uf = row[2].strip().upper()
                id_macsaud = row[3].strip()
                nome_macsaud = row[4].strip()

                if not code_muni or not id_macsaud:
                    continue

                muni_item = (code_muni, nome_muni)
                macro_nomes[id_macsaud] = nome_macsaud
                macro_ufs[id_macsaud] = sigla_uf
                all_macros[id_macsaud] = nome_macsaud

                if sigla_uf:
                    if sigla_uf not in macros_by_uf:
                        macros_by_uf[sigla_uf] = {}
                    macros_by_uf[sigla_uf][id_macsaud] = nome_macsaud

                if id_macsaud not in munis_by_macro:
                    munis_by_macro[id_macsaud] = []
                munis_by_macro[id_macsaud].append(muni_item)

            if not header_found:
                raise MacroSaudeError(
                    f"Nenhum cabeçalho válido encontrado no arquivo '{path}'"
                )

    except MacroSaudeError:
        raise
    except Exception as e:
        raise MacroSaudeError(
            f"Erro ao ler arquivo de macrorregiões de saúde '{path}': {e}"
        ) from e

    data = {
        "macro_nomes": macro_nomes,
        "macro_ufs": macro_ufs,
        "macros_by_uf": macros_by_uf,
        "munis_by_macro": munis_by_macro,
        "all_macros": all_macros,
    }
    _CACHE[path] = data
    return data


def listar(
    sigla_uf: Optional[Any] = None,
    csv_path: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Lista as macrorregiões de saúde (id, nome), ordenadas alfabeticamente por nome.

    Args:
        sigla_uf: Sigla opcional da UF (ex: 'MG', 'sp') ou código numérico (ex: 31).
        csv_path: Caminho opcional para o arquivo CSV.

    Returns:
        Lista de tuplas [(id_macsaud, nome_macsaud), ...] ordenada por nome.

    Raises:
        MacroSaudeError: Se o arquivo CSV estiver ausente ou ilegível.
    """
    data = _carregar_dados(csv_path)

    if sigla_uf is not None:
        uf_clean = _normalizar_uf(sigla_uf)
        macros_dict = data["macros_by_uf"].get(uf_clean, {}) if uf_clean else {}
    else:
        macros_dict = data["all_macros"]

    result = list(macros_dict.items())
    result.sort(key=lambda x: (x[1], x[0]))
    return result


def municipios(
    id_macro: Any,
    csv_path: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Retorna lista de municípios [(code_muni, nome_muni)] da macrorregião de saúde.

    Args:
        id_macro: ID da macrorregião de saúde (ex: '3103' ou 3103).
        csv_path: Caminho opcional para o arquivo CSV.

    Returns:
        Lista de tuplas [(code_muni, nome_muni)], ou lista vazia se não encontrada.

    Raises:
        MacroSaudeError: Se o arquivo CSV estiver ausente ou ilegível.
    """
    if id_macro is None:
        return []

    id_str = str(id_macro).strip()
    if not id_str:
        return []

    data = _carregar_dados(csv_path)
    munis = data["munis_by_macro"].get(id_str)
    if munis is None and id_str.isdigit() and len(id_str) < 4:
        munis = data["munis_by_macro"].get(id_str.zfill(4))

    if munis is None:
        return []

    return list(munis)


def nome(
    id_macro: Any,
    csv_path: Optional[str] = None,
) -> Optional[str]:
    """Retorna o nome da macrorregião de saúde pelo seu identificador.

    Args:
        id_macro: ID da macrorregião de saúde (ex: '3103' ou 3103).
        csv_path: Caminho opcional para o arquivo CSV.

    Returns:
        Nome da macrorregião, ou None se não encontrada.

    Raises:
        MacroSaudeError: Se o arquivo CSV estiver ausente ou ilegível.
    """
    if id_macro is None:
        return None

    id_str = str(id_macro).strip()
    if not id_str:
        return None

    data = _carregar_dados(csv_path)
    if id_str in data["macro_nomes"]:
        return data["macro_nomes"][id_str]

    if id_str.isdigit() and len(id_str) < 4:
        id_zfill = id_str.zfill(4)
        if id_zfill in data["macro_nomes"]:
            return data["macro_nomes"][id_zfill]

    return None
