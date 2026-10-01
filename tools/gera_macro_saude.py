#!/usr/bin/env python3
"""Gerador do CSV de composição das Macrorregiões de Saúde do Brasil a partir
da Base Territorial do DataSUS/Ministério da Saúde.

Gera o arquivo `gisbr/core/data/macro_saude.csv` contendo o mapeamento entre
municípios, macrorregiões de saúde e regiões de saúde.

Contagens validadas na Base Territorial DataSUS (jun/2026):
- 5.571 municípios ativos (linhas de dados);
- 121 macrorregiões de saúde ativas distintas (id_macsaud);
- 16 macrorregiões de saúde em Minas Gerais (sigla_uf=MG);
- Linha 3106200: Belo Horizonte, id_macsaud=3103, nome_macsaud=Centro.
(Se os números divergirem em atualizações futuras do DataSUS, registrar os novos aqui).

Uso:
    python3 tools/gera_macro_saude.py
    python3 tools/gera_macro_saude.py [caminho_base_territorial.zip]
"""

import argparse
import csv
import io
import re
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CSV = REPO_ROOT / "gisbr" / "core" / "data" / "macro_saude.csv"

DATASUS_URL = "ftp://ftp.datasus.gov.br/territorio/tabelas/2026/06-base_territorial_jun26.zip"
BASE_MES_ANO = "jun26"

FIELDNAMES = [
    "code_muni",
    "nome_muni",
    "sigla_uf",
    "id_macsaud",
    "nome_macsaud",
    "id_regsaud",
    "nome_regsaud",
]


def _obter_zip(origem: str) -> zipfile.ZipFile:
    """Abre arquivo ZIP local ou baixa da URL DataSUS via FTP."""
    caminho = Path(origem)
    if caminho.is_file():
        print(f"Carregando arquivo ZIP local: {caminho}")
        return zipfile.ZipFile(caminho)

    print(f"Baixando dados de {origem}...")
    req = urllib.request.Request(
        origem,
        headers={"User-Agent": "GisBR-Generator/1.0"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        content = resp.read()
    print(f"Download concluído: {len(content):,} bytes.")
    return zipfile.ZipFile(io.BytesIO(content))


def gerar_macro_saude(origem_zip: str = DATASUS_URL, output_csv: Path = OUTPUT_CSV) -> list:
    """Processa a base territorial do DataSUS e grava macro_saude.csv."""
    with _obter_zip(origem_zip) as z:
        # 1. Tabela de macrorregiões de saúde (tb_macsaud.csv)
        tb_macsaud = {}
        with z.open("tb_macsaud.csv") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter=";")
            for row in reader:
                tb_macsaud[row["CO_MACSAUD"].strip()] = row

        # 2. Relação município -> macrorregião (rl_municip_macsaud.csv)
        rl_macsaud = {}
        with z.open("rl_municip_macsaud.csv") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter=";")
            for row in reader:
                rl_macsaud[row["CO_MUNICIP"].strip()] = row["CO_MACSAUD"].strip()

        # 3. Tabela de regiões de saúde (tb_regsaud.csv, delimitada por vírgula)
        tb_regsaud = {}
        with z.open("tb_regsaud.csv") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
            for row in reader:
                tb_regsaud[row["CO_REGSAUD"].strip()] = row

        # 4. Relação município -> região de saúde (rl_municip_regsaud.csv)
        rl_regsaud = {}
        with z.open("rl_municip_regsaud.csv") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter=";")
            for row in reader:
                rl_regsaud[row["CO_MUNICIP"].strip()] = row["CO_REGSAUD"].strip()

        # 5. Tabela de municípios (tb_municip.csv) - apenas municípios ativos
        municipios_ativos = []
        with z.open("tb_municip.csv") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter=";")
            for row in reader:
                if row.get("CO_STATUS", "").strip().upper() == "ATIVO":
                    municipios_ativos.append(row)

    print(f"Municípios ativos encontrados no DataSUS: {len(municipios_ativos)}")

    rows = []
    for m in municipios_ativos:
        co_6 = str(m.get("CO_MUNICIP", "")).strip()
        code_muni = str(m.get("CO_MUNICDV", "")).strip()
        nome_muni = str(m.get("DS_NOME", "")).strip()
        sigla_uf = str(m.get("UF", "")).strip().upper()

        id_macsaud = str(m.get("MACRORREGIONAL", "")).strip() or rl_macsaud.get(co_6, "")
        if not id_macsaud or id_macsaud not in tb_macsaud:
            raise RuntimeError(
                f"Macro de saúde desconhecida ou ausente ({id_macsaud}) para município {code_muni} ({nome_muni})."
            )

        mac_info = tb_macsaud[id_macsaud]
        if mac_info.get("CO_STATUS", "").strip().upper() != "S":
            raise RuntimeError(
                f"Macro inativa referenciada por município ativo {code_muni} ({nome_muni}): "
                f"id={id_macsaud}, status={mac_info.get('CO_STATUS')}"
            )

        # Nome da macrorregião vem de DS_ABREV com a primeira letra em maiúscula
        ds_abrev = re.sub(r"\s+", " ", mac_info.get("DS_ABREV", "")).strip()
        nome_macsaud = ds_abrev[:1].upper() + ds_abrev[1:]

        # Região de saúde
        id_regsaud = rl_regsaud.get(co_6, "").strip()
        reg_info = tb_regsaud.get(id_regsaud)
        if not reg_info:
            raise RuntimeError(
                f"Região de saúde desconhecida ({id_regsaud}) para município {code_muni} ({nome_muni})."
            )
        nome_regsaud = re.sub(r"\s+", " ", reg_info.get("DS_NOME", "")).strip()

        rows.append({
            "code_muni": code_muni,
            "nome_muni": nome_muni,
            "sigla_uf": sigla_uf,
            "id_macsaud": id_macsaud,
            "nome_macsaud": nome_macsaud,
            "id_regsaud": id_regsaud,
            "nome_regsaud": nome_regsaud,
        })

    # Ordenado por code_muni (7 dígitos)
    rows.sort(key=lambda r: r["code_muni"])

    # Validações dos critérios do plano
    total_linhas = len(rows)
    id_macsaud_set = {r["id_macsaud"] for r in rows}
    mg_macros = {r["id_macsaud"] for r in rows if r["sigla_uf"] == "MG"}
    bh_linha = next((r for r in rows if r["code_muni"] == "3106200"), None)

    print("\n--- Validação dos Critérios do Plano ---")
    print(f"Linhas de dados: {total_linhas} (esperado: 5.571)")
    print(f"id_macsaud distintos: {len(id_macsaud_set)} (esperado: 121)")
    print(f"Macros em MG: {len(mg_macros)} (esperado: 16)")
    if bh_linha:
        print(
            f"Linha 3106200: id_macsaud={bh_linha['id_macsaud']} "
            f"nome_macsaud='{bh_linha['nome_macsaud']}' "
            f"(esperado: id_macsaud=3103, nome_macsaud=Centro)"
        )
    else:
        print("ERRO: Linha 3106200 (Belo Horizonte) não encontrada!")

    if total_linhas != 5571 or len(id_macsaud_set) != 121 or len(mg_macros) != 16:
        print(
            "AVISO: Os números divergiram dos esperados na medição inicial. "
            "Confira se houve atualização na base territorial do DataSUS.",
            file=sys.stderr,
        )
    if not bh_linha or bh_linha["id_macsaud"] != "3103" or bh_linha["nome_macsaud"] != "Centro":
        raise RuntimeError(f"Validação da linha 3106200 falhou: {bh_linha}")

    # Gravação do CSV
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    data_extracao = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        f.write(f"# Origem: {origem_zip}\n")
        f.write(f"# Data de extração: {data_extracao}\n")
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDNAMES,
            delimiter=";",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCSV gravado com sucesso em: {output_csv}")
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Gera gisbr/core/data/macro_saude.csv a partir da base do DataSUS."
    )
    parser.add_argument(
        "origem",
        nargs="?",
        default=DATASUS_URL,
        help=f"Arquivo ZIP local ou URL da base territorial (padrão: {DATASUS_URL})",
    )
    args = parser.parse_args()
    gerar_macro_saude(args.origem)


if __name__ == "__main__":
    main()
