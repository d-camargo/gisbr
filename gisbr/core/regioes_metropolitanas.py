# -*- coding: utf-8 -*-
"""Leitor e parser da composição de Regiões Metropolitanas e RIDE do IBGE.

Módulo stdlib puro (sem PyQGIS).
"""

import csv
import os
from typing import Any, Dict, List, Optional, Tuple

_DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "data", "regioes_metropolitanas.csv"
)


class RegioesMetropolitanasError(RuntimeError):
    """Exceção lançada quando o arquivo de Regiões Metropolitanas está ausente ou ilegível."""

    pass


_CACHE: Dict[str, Dict[str, Any]] = {}


def reset_cache() -> None:
    """Limpa o cache em memória (útil para testes)."""
    _CACHE.clear()


def _carregar_dados(csv_path: Optional[str] = None) -> Dict[str, Any]:
    """Carrega e memoiza em memória a composição das Regiões Metropolitanas do CSV.

    Args:
        csv_path: Caminho opcional para o arquivo CSV.

    Returns:
        Dict com estruturas pré-computadas {'by_id': ..., 'by_uf': ..., 'all': ...}.

    Raises:
        RegioesMetropolitanasError: Se o arquivo estiver ausente ou ilegível.
    """
    path = os.path.abspath(csv_path) if csv_path else os.path.abspath(_DEFAULT_CSV_PATH)
    if path in _CACHE:
        return _CACHE[path]

    if not os.path.exists(path):
        raise RegioesMetropolitanasError(
            f"Arquivo de regiões metropolitanas não encontrado: '{path}'"
        )

    rms_by_id: Dict[str, Dict[str, Any]] = {}
    rms_by_uf: Dict[str, List[Dict[str, Any]]] = {}

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
                    if first_cell == "id_rm":
                        header_found = True
                        continue
                    else:
                        raise RegioesMetropolitanasError(
                            f"Cabeçalho inválido no arquivo '{path}': esperava 'id_rm', obteve '{first_cell}'"
                        )

                if len(row) < 5:
                    continue

                id_rm = row[0].strip()
                nome_rm = row[1].strip()
                sigla_uf = row[2].strip().upper()
                code_muni = row[3].strip()
                nome_muni = row[4].strip()

                if not id_rm or not sigla_uf or not code_muni:
                    continue

                if id_rm not in rms_by_id:
                    rm_dict: Dict[str, Any] = {
                        "id": id_rm,
                        "nome": nome_rm,
                        "uf": sigla_uf,
                        "municipios": [],
                    }
                    rms_by_id[id_rm] = rm_dict

                    if sigla_uf not in rms_by_uf:
                        rms_by_uf[sigla_uf] = []
                    rms_by_uf[sigla_uf].append(rm_dict)

                rms_by_id[id_rm]["municipios"].append((code_muni, nome_muni))

            if not header_found:
                raise RegioesMetropolitanasError(
                    f"Nenhum cabeçalho válido encontrado no arquivo '{path}'"
                )

    except RegioesMetropolitanasError:
        raise
    except Exception as e:
        raise RegioesMetropolitanasError(
            f"Erro ao ler arquivo de regiões metropolitanas '{path}': {e}"
        ) from e

    # Ordena a lista de cada UF por nome da RM
    for uf in rms_by_uf:
        rms_by_uf[uf].sort(key=lambda x: x["nome"])

    data = {
        "by_id": rms_by_id,
        "by_uf": rms_by_uf,
        "all": sorted(rms_by_id.values(), key=lambda x: x["nome"]),
    }
    _CACHE[path] = data
    return data


def listar_por_uf(uf: str, csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna lista de RMs de uma UF, ordenada por nome da RM.

    Args:
        uf: Sigla da UF (ex: 'MG', 'sp').
        csv_path: Caminho opcional para o CSV.

    Returns:
        Lista de dicts {"id", "nome", "uf", "municipios": [(code, nome), ...]}.
    """
    if not uf:
        return []
    uf_clean = str(uf).strip().upper()
    data = _carregar_dados(csv_path)
    return data["by_uf"].get(uf_clean, [])


def por_id(id_rm: Any, csv_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retorna o dict da RM pelo seu ID ou None se não encontrada.

    Args:
        id_rm: ID da RM (ex: '04501' ou 4501).
        csv_path: Caminho opcional para o CSV.

    Returns:
        Dict da RM ou None.
    """
    if id_rm is None:
        return None
    data = _carregar_dados(csv_path)
    id_str = str(id_rm).strip()
    by_id = data["by_id"]
    if id_str in by_id:
        return by_id[id_str]
    # Se id_rm for numérico (ex: 4501), tenta zfill com 5 dígitos
    if id_str.isdigit() and len(id_str) < 5:
        id_zfill = id_str.zfill(5)
        if id_zfill in by_id:
            return by_id[id_zfill]
    return None


def codes(id_rm: Any, csv_path: Optional[str] = None) -> List[str]:
    """Retorna lista de códigos IBGE (string, 7 dígitos) dos municípios da RM.

    Args:
        id_rm: ID da RM (ex: '04501').
        csv_path: Caminho opcional para o CSV.

    Returns:
        Lista de code_muni (strings de 7 dígitos).
    """
    rm = por_id(id_rm, csv_path=csv_path)
    if not rm:
        return []
    return [muni[0] for muni in rm.get("municipios", [])]


def listar_todas(csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna lista de todas as Regiões Metropolitanas do Brasil."""
    data = _carregar_dados(csv_path)
    return data["all"]
