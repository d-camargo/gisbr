#!/usr/bin/env python3
# coding=utf-8
"""Script de verificação do pacote ZIP de plugin QGIS (GisBR).

Uso:
    python3 tools/check_package.py <caminho_para_pacote.zip>

Verificações:
1. (a) Grep amplo por enums Qt/PyQGIS não-escopados (\\bQ[A-Za-z]+\\.[A-Z][A-Za-z]+\\b) em todos os arquivos .py do zip.
2. (b) Divergência entre version= do metadata.txt no zip e gisbr/metadata.txt do working tree.
3. (c) Todo *.pem presente em gisbr/core/certs/ do working tree precisa estar dentro do ZIP;
   o ZIP precisa conter pelo menos um .pem.
"""

import sys
import os
import re
import zipfile
import configparser
from pathlib import Path


# Regras e exclusões para enums Qt não-escopados
QT_ENUM_PATTERN = re.compile(r'\b(Q[A-Za-z0-9_]+)\.([A-Z][A-Za-z0-9_]+)\b')

# Exceções conhecidas / formas válidas que coincidem com o padrão simples
KNOWN_ALLOWED = {
    "QgsVectorFileWriter.SaveVectorOptions",
    "QVariant.Type",
    "QMetaType.Type",
    "QgsVectorFileWriter.ActionOnExistingFile",
    "QgsVectorFileWriter.Mode",
    "QgsVectorFileWriter.EditionCapability",
}


def check_unscoped_qt_enums(zf: zipfile.ZipFile) -> list:
    """Verifica todos os arquivos .py dentro do ZIP em busca de enums Qt não-escopados."""
    errors = []

    for name in zf.namelist():
        if not name.endswith('.py'):
            continue

        try:
            content = zf.read(name).decode('utf-8', errors='replace')
        except Exception as e:
            errors.append(f"{name}: Erro ao ler arquivo do ZIP: {e}")
            continue

        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            code_line = line.split('#')[0]

            for m in QT_ENUM_PATTERN.finditer(code_line):
                matched_str = m.group(0)

                end_pos = m.end()
                rest = code_line[end_pos:]
                if rest.startswith('.'):
                    continue

                if rest.startswith('('):
                    continue

                if matched_str in KNOWN_ALLOWED:
                    continue

                if 'qgis_compat.py' in name:
                    continue

                errors.append(f"{name}:{idx}: {matched_str} (linha: {stripped})")

    return errors


def check_version_match(zf: zipfile.ZipFile, working_tree_root: Path) -> list:
    """Verifica se a versão em metadata.txt no ZIP bate com a versão do working tree."""
    errors = []

    zip_meta_files = [n for n in zf.namelist() if n.endswith('metadata.txt')]
    if not zip_meta_files:
        errors.append("metadata.txt não encontrado dentro do arquivo ZIP!")
        return errors

    zip_meta_path = zip_meta_files[0]

    try:
        zip_meta_content = zf.read(zip_meta_path).decode('utf-8', errors='replace')
        config_zip = configparser.ConfigParser(strict=False)
        config_zip.read_string(zip_meta_content)
        zip_version = config_zip.get('general', 'version', fallback='').strip()
    except Exception as e:
        errors.append(f"Erro ao ler metadata.txt do ZIP ({zip_meta_path}): {e}")
        return errors

    wt_meta_path = working_tree_root / 'gisbr' / 'metadata.txt'
    if not wt_meta_path.exists():
        wt_meta_path = working_tree_root / 'metadata.txt'

    if not wt_meta_path.exists():
        errors.append(f"metadata.txt do working tree não encontrado em {wt_meta_path}")
        return errors

    try:
        config_wt = configparser.ConfigParser(strict=False)
        config_wt.read(str(wt_meta_path), encoding='utf-8')
        wt_version = config_wt.get('general', 'version', fallback='').strip()
    except Exception as e:
        errors.append(f"Erro ao ler metadata.txt do working tree ({wt_meta_path}): {e}")
        return errors

    if zip_version != wt_version:
        errors.append(
            f"Divergência de versão! Versão no ZIP: '{zip_version}' != Versão no working tree ({wt_meta_path.name}): '{wt_version}'"
        )

    return errors


def check_pem_files_packaged(zf: zipfile.ZipFile, working_tree_root: Path) -> list:
    """Verifica se todo *.pem de gisbr/core/certs/ do working tree está dentro do ZIP."""
    errors = []

    certs_dir = working_tree_root / 'gisbr' / 'core' / 'certs'
    wt_pems = sorted(p.name for p in certs_dir.glob('*.pem')) if certs_dir.is_dir() else []

    if not wt_pems:
        errors.append(f"Nenhum *.pem encontrado em {certs_dir} — verificação sem material para conferir.")
        return errors

    zip_pem_names = {os.path.basename(n) for n in zf.namelist() if n.endswith('.pem')}

    if not zip_pem_names:
        errors.append("Nenhum arquivo .pem encontrado dentro do ZIP!")
        return errors

    missing = [name for name in wt_pems if name not in zip_pem_names]
    if missing:
        errors.append(
            "Certificado(s) presente(s) no working tree mas ausente(s) do ZIP: " + ", ".join(missing)
        )

    return errors


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 tools/check_package.py <caminho_para_pacote.zip>")
        sys.exit(2)

    zip_path = sys.argv[1]
    if not os.path.exists(zip_path):
        print(f"ERRO: Arquivo ZIP não encontrado: {zip_path}")
        sys.exit(1)

    if not zipfile.is_zipfile(zip_path):
        print(f"ERRO: O arquivo não é um ZIP válido: {zip_path}")
        sys.exit(1)

    working_tree_root = Path(__file__).resolve().parent.parent

    print(f"=== Verificando pacote ZIP: {zip_path} ===")
    errors = []

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            enum_errors = check_unscoped_qt_enums(zf)
            if enum_errors:
                errors.append("Enums Qt/PyQGIS não-escopados encontrados:")
                errors.extend(enum_errors)

            version_errors = check_version_match(zf, working_tree_root)
            if version_errors:
                errors.append("Divergência de versão encontrada:")
                errors.extend(version_errors)

            pem_errors = check_pem_files_packaged(zf, working_tree_root)
            if pem_errors:
                errors.append("Problema com certificados (.pem) no pacote:")
                errors.extend(pem_errors)

    except Exception as e:
        print(f"ERRO fatal ao processar {zip_path}: {e}")
        sys.exit(1)

    if errors:
        print(f"❌ REPROVADO: {len(errors)} problema(s) encontrado(s) no pacote:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print(f"✅ APROVADO: O pacote {os.path.basename(zip_path)} passou em todas as verificações!")
        sys.exit(0)


if __name__ == "__main__":
    main()
