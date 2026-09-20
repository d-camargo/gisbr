#!/usr/bin/env python3
# coding=utf-8
"""Gerador do CSV de composição das Regiões Metropolitanas (RMs) e Aglomerações
Urbanas do Brasil a partir da API de Localidades do IBGE (v1).

Gera o arquivo `gisbr/core/data/regioes_metropolitanas.csv` contendo o mapeamento
entre RMs e municípios.

Uso:
    python3 tools/gera_regioes_metropolitanas.py
"""

import csv
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import urllib.request

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CSV = REPO_ROOT / "gisbr" / "core" / "data" / "regioes_metropolitanas.csv"

IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/regioes-metropolitanas"


def main():
    print(f"Baixando dados de {IBGE_URL}...")
    req = urllib.request.Request(
        IBGE_URL,
        headers={
            "User-Agent": "GisBR-Generator/1.0",
            "Accept-Encoding": "gzip",
        },
    )

    with urllib.request.urlopen(req) as resp:
        content = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip" or content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)
        data = json.loads(content.decode("utf-8"))

    print(f"Entidades (RMs/AUs) retornadas pela API: {len(data)}")

    rows = []
    id_rms = set()

    for rm in data:
        id_rm = str(rm["id"]).strip()
        nome_rm = str(rm["nome"]).strip()
        sigla_uf = str(rm["UF"]["sigla"]).strip() if rm.get("UF") and "sigla" in rm["UF"] else ""
        id_rms.add(id_rm)

        # NOTA: Sub-regiões metropolitanas (`sub-regioes-metropolitanas`) são ignoradas de propósito.
        # Os municípios pertencentes a sub-regiões já vêm listados no array principal `municipios` da RM
        # no payload da API do IBGE (Medição 2 confirmou 1.377 municípios únicos sem omissões).
        municipios = rm.get("municipios", [])
        for muni in municipios:
            code_muni = str(muni["id"]).strip()
            nome_muni = str(muni["nome"]).strip()
            rows.append({
                "id_rm": id_rm,
                "nome_rm": nome_rm,
                "sigla_uf": sigla_uf,
                "code_muni": code_muni,
                "nome_muni": nome_muni,
            })

    # Ordenado por id_rm e nome_muni
    rows.sort(key=lambda r: (r["id_rm"], r["nome_muni"]))

    data_extracao = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        f.write(f"# Origem: {IBGE_URL}\n")
        f.write(f"# Data de extração: {data_extracao}\n")
        writer = csv.DictWriter(
            f,
            fieldnames=["id_rm", "nome_rm", "sigla_uf", "code_muni", "nome_muni"],
            delimiter=";",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV gravado com sucesso em: {OUTPUT_CSV}")
    print(f"Validação: {len(id_rms)} RMs distintas | {len(rows)} linhas de dado.")


if __name__ == "__main__":
    main()
