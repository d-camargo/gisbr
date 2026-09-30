#!/usr/bin/env python3
# coding=utf-8
"""Gerador do CSV de composição da Divisão Regional do Brasil a partir da API de
Localidades do IBGE (v1).

Gera o arquivo `gisbr/core/data/divisao_regional.csv` contendo o mapeamento
entre municípios, microrregiões, mesorregiões, regiões imediatas, regiões
intermediárias e macrorregiões.

Uso:
    python3 tools/gera_divisao_regional.py
"""

import csv
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import urllib.request

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CSV = REPO_ROOT / "gisbr" / "core" / "data" / "divisao_regional.csv"

IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

FIELDNAMES = [
    "code_muni",
    "nome_muni",
    "sigla_uf",
    "id_micro",
    "nome_micro",
    "id_meso",
    "nome_meso",
    "id_imediata",
    "nome_imediata",
    "id_intermediaria",
    "nome_intermediaria",
    "id_regiao",
    "nome_regiao",
]


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

    print(f"Municípios retornados pela API: {len(data)}")

    rows = []
    id_meso_set = set()
    id_micro_set = set()
    id_regiao_set = set()

    for m in data:
        code_muni = str(m["id"]).strip()
        nome_muni = str(m["nome"]).strip()

        micro = m.get("microrregiao")
        uf_obj = None
        if micro:
            id_micro = str(micro["id"]).strip()
            nome_micro = str(micro["nome"]).strip()
            meso = micro.get("mesorregiao")
            if meso:
                id_meso = str(meso["id"]).strip()
                nome_meso = str(meso["nome"]).strip()
                uf_obj = meso.get("UF")
            else:
                id_meso = ""
                nome_meso = ""
        else:
            id_micro = ""
            nome_micro = ""
            id_meso = ""
            nome_meso = ""

        imediata = m.get("regiao-imediata")
        if imediata:
            id_imediata = str(imediata["id"]).strip()
            nome_imediata = str(imediata["nome"]).strip()
            intermediaria = imediata.get("regiao-intermediaria")
            if intermediaria:
                id_intermediaria = str(intermediaria["id"]).strip()
                nome_intermediaria = str(intermediaria["nome"]).strip()
                if not uf_obj:
                    uf_obj = intermediaria.get("UF")
            else:
                id_intermediaria = ""
                nome_intermediaria = ""
        else:
            id_imediata = ""
            nome_imediata = ""
            id_intermediaria = ""
            nome_intermediaria = ""

        if uf_obj:
            sigla_uf = str(uf_obj.get("sigla", "")).strip().upper()
            regiao_obj = uf_obj.get("regiao")
            if regiao_obj:
                id_regiao = str(regiao_obj.get("id", "")).strip()
                nome_regiao = str(regiao_obj.get("nome", "")).strip()
            else:
                id_regiao = ""
                nome_regiao = ""
        else:
            sigla_uf = ""
            id_regiao = ""
            nome_regiao = ""

        if id_meso:
            id_meso_set.add(id_meso)
        if id_micro:
            id_micro_set.add(id_micro)
        if id_regiao:
            id_regiao_set.add(id_regiao)

        rows.append({
            "code_muni": code_muni,
            "nome_muni": nome_muni,
            "sigla_uf": sigla_uf,
            "id_micro": id_micro,
            "nome_micro": nome_micro,
            "id_meso": id_meso,
            "nome_meso": nome_meso,
            "id_imediata": id_imediata,
            "nome_imediata": nome_imediata,
            "id_intermediaria": id_intermediaria,
            "nome_intermediaria": nome_intermediaria,
            "id_regiao": id_regiao,
            "nome_regiao": nome_regiao,
        })

    # Ordenado por code_muni
    rows.sort(key=lambda r: r["code_muni"])

    data_extracao = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        f.write(f"# Origem: {IBGE_URL}\n")
        f.write(f"# Data de extração: {data_extracao}\n")
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDNAMES,
            delimiter=";",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV gravado com sucesso em: {OUTPUT_CSV}")
    print(
        f"Validação: {len(rows)} linhas de dados | "
        f"{len(id_meso_set)} id_meso distintos | "
        f"{len(id_micro_set)} id_micro distintos | "
        f"{len(id_regiao_set)} id_regiao distintos."
    )


if __name__ == "__main__":
    main()
