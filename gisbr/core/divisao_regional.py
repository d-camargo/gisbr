# -*- coding: utf-8 -*-
"""Leitor e parser da composição da Divisão Regional do Brasil (IBGE).

Mapeia municípios, microrregiões, mesorregiões e macrorregiões.
Módulo stdlib puro (sem PyQGIS).
"""

import csv
import os
from typing import Any, Dict, List, Optional, Tuple

from .constants import UF_CODE_TO_ABBREV

_DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "data", "divisao_regional.csv"
)


class DivisaoRegionalError(RuntimeError):
    """Exceção lançada quando o arquivo de Divisão Regional está ausente ou ilegível."""

    pass


_CACHE: Dict[str, Dict[str, Any]] = {}

UF_NAMES: Dict[str, str] = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}


def _normalizar_tipo(tipo: str) -> str:
    """Normaliza o identificador do tipo regional."""
    t = str(tipo).strip().lower()
    if t in ("micro", "microrregiao", "microrregião"):
        return "micro"
    if t in ("meso", "mesorregiao", "mesorregião"):
        return "meso"
    if t in ("macro", "macrorregiao", "macrorregião", "regiao", "região"):
        return "macro"
    if t in ("uf", "estado"):
        return "uf"
    if t in ("muni", "municipio", "município"):
        return "muni"
    return t


def reset_cache() -> None:
    """Limpa o cache em memória (útil para testes)."""
    _CACHE.clear()


def _carregar_dados(csv_path: Optional[str] = None) -> Dict[str, Any]:
    """Carrega e memoiza em memória a composição da Divisão Regional do CSV.

    Args:
        csv_path: Caminho opcional para o arquivo CSV.

    Returns:
        Dict com estruturas pré-computadas para buscas rápidas.

    Raises:
        DivisaoRegionalError: Se o arquivo estiver ausente ou ilegível.
    """
    path = os.path.abspath(csv_path) if csv_path else os.path.abspath(_DEFAULT_CSV_PATH)
    if path in _CACHE:
        return _CACHE[path]

    if not os.path.exists(path):
        raise DivisaoRegionalError(
            f"Arquivo de divisão regional não encontrado: '{path}'"
        )

    micro_nomes: Dict[str, str] = {}
    meso_nomes: Dict[str, str] = {}
    macro_nomes: Dict[str, str] = {}
    muni_nomes: Dict[str, str] = {}

    micro_by_uf: Dict[str, Dict[str, str]] = {}
    meso_by_uf: Dict[str, Dict[str, str]] = {}

    all_micro: Dict[str, str] = {}
    all_meso: Dict[str, str] = {}
    all_macro: Dict[str, str] = {}

    munis_by_micro: Dict[str, List[Tuple[str, str]]] = {}
    munis_by_meso: Dict[str, List[Tuple[str, str]]] = {}
    munis_by_macro: Dict[str, List[Tuple[str, str]]] = {}
    munis_by_uf: Dict[str, List[Tuple[str, str]]] = {}

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
                        raise DivisaoRegionalError(
                            f"Cabeçalho inválido no arquivo '{path}': esperava 'code_muni', obteve '{first_cell}'"
                        )

                if len(row) < 13:
                    continue

                code_muni = row[0].strip()
                nome_muni = row[1].strip()
                sigla_uf = row[2].strip().upper()
                id_micro = row[3].strip()
                nome_micro = row[4].strip()
                id_meso = row[5].strip()
                nome_meso = row[6].strip()
                # row[7]: id_imediata, row[8]: nome_imediata
                # row[9]: id_intermediaria, row[10]: nome_intermediaria
                id_regiao = row[11].strip()
                nome_regiao = row[12].strip()

                if not code_muni:
                    continue

                muni_item = (code_muni, nome_muni)
                muni_nomes[code_muni] = nome_muni

                if sigla_uf:
                    if sigla_uf not in munis_by_uf:
                        munis_by_uf[sigla_uf] = []
                    munis_by_uf[sigla_uf].append(muni_item)

                if id_micro:
                    micro_nomes[id_micro] = nome_micro
                    all_micro[id_micro] = nome_micro
                    if sigla_uf not in micro_by_uf:
                        micro_by_uf[sigla_uf] = {}
                    micro_by_uf[sigla_uf][id_micro] = nome_micro

                    if id_micro not in munis_by_micro:
                        munis_by_micro[id_micro] = []
                    munis_by_micro[id_micro].append(muni_item)

                if id_meso:
                    meso_nomes[id_meso] = nome_meso
                    all_meso[id_meso] = nome_meso
                    if sigla_uf not in meso_by_uf:
                        meso_by_uf[sigla_uf] = {}
                    meso_by_uf[sigla_uf][id_meso] = nome_meso

                    if id_meso not in munis_by_meso:
                        munis_by_meso[id_meso] = []
                    munis_by_meso[id_meso].append(muni_item)

                if id_regiao:
                    macro_nomes[id_regiao] = nome_regiao
                    all_macro[id_regiao] = nome_regiao

                    if id_regiao not in munis_by_macro:
                        munis_by_macro[id_regiao] = []
                    munis_by_macro[id_regiao].append(muni_item)

            if not header_found:
                raise DivisaoRegionalError(
                    f"Nenhum cabeçalho válido encontrado no arquivo '{path}'"
                )

    except DivisaoRegionalError:
        raise
    except Exception as e:
        raise DivisaoRegionalError(
            f"Erro ao ler arquivo de divisão regional '{path}': {e}"
        ) from e

    data = {
        "micro_nomes": micro_nomes,
        "meso_nomes": meso_nomes,
        "macro_nomes": macro_nomes,
        "muni_nomes": muni_nomes,
        "micro_by_uf": micro_by_uf,
        "meso_by_uf": meso_by_uf,
        "all_micro": all_micro,
        "all_meso": all_meso,
        "all_macro": all_macro,
        "munis_by_micro": munis_by_micro,
        "munis_by_meso": munis_by_meso,
        "munis_by_macro": munis_by_macro,
        "munis_by_uf": munis_by_uf,
    }
    _CACHE[path] = data
    return data


def listar(
    tipo: str,
    sigla_uf: Optional[str] = None,
    csv_path: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Lista as divisões regionais (id, nome), ordenadas alfabeticamente por nome.

    Args:
        tipo: 'micro', 'meso' ou 'macro'.
        sigla_uf: Sigla opcional da UF para filtrar 'micro' e 'meso'.
        csv_path: Caminho opcional para o arquivo CSV.

    Returns:
        Lista de tuplas [(id, nome), ...] ordenada por nome.

    Raises:
        ValueError: Se o tipo não for 'micro', 'meso' ou 'macro'.
        DivisaoRegionalError: Se o arquivo CSV estiver ausente ou ilegível.
    """
    t = _normalizar_tipo(tipo)
    if t not in ("micro", "meso", "macro"):
        raise ValueError(
            f"Tipo regional inválido: '{tipo}'. Esperado: 'micro', 'meso' ou 'macro'."
        )

    data = _carregar_dados(csv_path)
    uf_clean = str(sigla_uf).strip().upper() if sigla_uf else None

    if t == "micro":
        if uf_clean:
            items_dict = data["micro_by_uf"].get(uf_clean, {})
        else:
            items_dict = data["all_micro"]
    elif t == "meso":
        if uf_clean:
            items_dict = data["meso_by_uf"].get(uf_clean, {})
        else:
            items_dict = data["all_meso"]
    else:  # macro
        items_dict = data["all_macro"]

    result = list(items_dict.items())
    result.sort(key=lambda x: (x[1], x[0]))
    return result


def municipios(
    tipo: str,
    id: Any,
    csv_path: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Retorna lista de municípios [(code_muni, nome_muni)] pertencentes à divisão regional.

    Args:
        tipo: 'micro', 'meso', 'uf' ou 'macro'.
        id: Identificador da divisão. No tipo 'uf', é a sigla (ex: 'MG') ou código (ex: 31).
            Nos demais tipos, pode ser string ou int (ex: '31030', '3107', '3').
        csv_path: Caminho opcional para o arquivo CSV.

    Returns:
        Lista de tuplas [(code_muni, nome_muni)].

    Raises:
        ValueError: Se o tipo não for 'micro', 'meso', 'uf' ou 'macro'.
        DivisaoRegionalError: Se o arquivo CSV estiver ausente ou ilegível.
    """
    if id is None:
        return []

    t = _normalizar_tipo(tipo)
    if t not in ("micro", "meso", "uf", "macro"):
        raise ValueError(
            f"Tipo regional inválido: '{tipo}'. Esperado: 'micro', 'meso', 'uf' ou 'macro'."
        )

    data = _carregar_dados(csv_path)
    id_str = str(id).strip()

    if t == "uf":
        uf_upper = id_str.upper()
        if uf_upper in data["munis_by_uf"]:
            return list(data["munis_by_uf"][uf_upper])
        if id_str.isdigit() and int(id_str) in UF_CODE_TO_ABBREV:
            sigla = UF_CODE_TO_ABBREV[int(id_str)]
            return list(data["munis_by_uf"].get(sigla, []))
        return []

    if t == "micro":
        return list(data["munis_by_micro"].get(id_str, []))

    if t == "meso":
        return list(data["munis_by_meso"].get(id_str, []))

    # macro
    if id_str in data["munis_by_macro"]:
        return list(data["munis_by_macro"][id_str])
    for macro_id, nome_reg in data["all_macro"].items():
        if nome_reg.lower() == id_str.lower():
            return list(data["munis_by_macro"].get(macro_id, []))

    return []


def nome(
    tipo: str,
    id: Any,
    csv_path: Optional[str] = None,
) -> str:
    """Retorna o nome da entidade regional pelo seu identificador.

    Args:
        tipo: 'micro', 'meso', 'uf' ou 'macro'.
        id: Identificador da entidade (ex: '31030', '3107', 'MG', '3').
        csv_path: Caminho opcional para o arquivo CSV.

    Returns:
        Nome da entidade ou string vazia se não encontrada.

    Raises:
        ValueError: Se o tipo não for suportado.
        DivisaoRegionalError: Se o arquivo CSV estiver ausente ou ilegível.
    """
    if id is None:
        return ""

    t = _normalizar_tipo(tipo)
    if t not in ("micro", "meso", "uf", "macro", "muni"):
        raise ValueError(
            f"Tipo regional inválido: '{tipo}'. Esperado: 'micro', 'meso', 'uf' ou 'macro'."
        )

    data = _carregar_dados(csv_path)
    id_str = str(id).strip()

    if t == "micro":
        return data["micro_nomes"].get(id_str, "")

    if t == "meso":
        return data["meso_nomes"].get(id_str, "")

    if t == "macro":
        if id_str in data["macro_nomes"]:
            return data["macro_nomes"][id_str]
        for mid, mname in data["macro_nomes"].items():
            if mname.lower() == id_str.lower():
                return mname
        return ""

    if t == "uf":
        uf_upper = id_str.upper()
        if uf_upper in UF_NAMES:
            return UF_NAMES[uf_upper]
        if id_str.isdigit() and int(id_str) in UF_CODE_TO_ABBREV:
            sigla = UF_CODE_TO_ABBREV[int(id_str)]
            return UF_NAMES.get(sigla, "")
        return ""

    if t == "muni":
        return data["muni_nomes"].get(id_str, "")

    return ""
