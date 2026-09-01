#!/usr/bin/env python3
# coding=utf-8
"""Verifica se a ancora TLS de cada host em SOURCES esta coberta pelos
.pem embarcados em gisbr/core/certs/.

Para cada host, abre uma conexao TLS (openssl s_client -showcerts), pega o
ultimo certificado da cadeia enviada pelo servidor e resolve a autoridade
que a encerra (emissor do ultimo certificado, ou o proprio certificado
quando autoassinado). Compara o CN dessa autoridade contra os CNs de
assunto de todo certificado em gisbr/core/certs/*.pem.

Uso:
    python3 tools/check_sources_tls.py               # varre os hosts de SOURCES
    python3 tools/check_sources_tls.py --host HOST    # checa um host avulso

Sai com codigo != 0 se algum host ficar marcado FALTA (ou em ERRO).
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from cryptography import x509
from cryptography.x509.oid import NameOID

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = REPO_ROOT / "gisbr" / "core" / "sources.py"
OSM_CONNECTOR_PATH = REPO_ROOT / "gisbr" / "core" / "connectors" / "osm.py"
CERTS_DIR = REPO_ROOT / "gisbr" / "core" / "certs"

CERT_BLOCK_RE = re.compile(
    rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S
)


def load_sources():
    """Carrega SOURCES de gisbr/core/sources.py sem depender do pacote gisbr."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("gisbr_sources", SOURCES_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SOURCES


def hosts_from_sources(sources):
    hosts = set()
    for source in sources:
        endpoint = source.get("endpoint")
        if not endpoint:
            continue
        host = urlparse(endpoint).hostname
        if host:
            hosts.add(host)
    return hosts


def hosts_from_osm_connector():
    """Hosts da cadeia de mirrors Overpass (_OVERPASS_ENDPOINTS em
    connectors/osm.py), extraidos por regex — o modulo importa qgis.core
    e nao pode ser carregado aqui. Fontes de protocolo "osm" nao tem
    "endpoint" em SOURCES, entao sem isto os mirrors ficariam de fora."""
    if not OSM_CONNECTOR_PATH.exists():
        return set()
    text = OSM_CONNECTOR_PATH.read_text(encoding="utf-8")
    match = re.search(r"_OVERPASS_ENDPOINTS\s*=\s*\((.*?)\)", text, re.S)
    if not match:
        return set()
    hosts = set()
    for url in re.findall(r'"(https?://[^"]+)"', match.group(1)):
        host = urlparse(url).hostname
        if host:
            hosts.add(host)
    return hosts


def local_anchor_cns():
    """CNs de assunto de todo certificado em CERTS_DIR/*.pem."""
    cns = set()
    for pem in sorted(CERTS_DIR.glob("*.pem")):
        data = pem.read_bytes()
        for block in CERT_BLOCK_RE.findall(data):
            cert = x509.load_pem_x509_certificate(block)
            cn = subject_cn(cert.subject)
            if cn:
                cns.add(cn)
    return cns


def subject_cn(name):
    attrs = name.get_attributes_for_oid(NameOID.COMMON_NAME)
    return attrs[0].value if attrs else None


def fetch_chain(host, port=443, timeout=15):
    """Cadeia de certificados enviada pelo servidor, na ordem recebida."""
    proc = subprocess.run(
        [
            "openssl", "s_client",
            "-connect", "{}:{}".format(host, port),
            "-servername", host,
            "-showcerts",
        ],
        input=b"",
        capture_output=True,
        timeout=timeout,
    )
    blocks = CERT_BLOCK_RE.findall(proc.stdout)
    return [x509.load_pem_x509_certificate(block) for block in blocks]


def resolve_anchor_cn(chain):
    """CN da autoridade que encerra a cadeia (emissor do ultimo certificado
    recebido, ou o proprio certificado quando autoassinado)."""
    last = chain[-1]
    anchor_name = last.subject if last.issuer == last.subject else last.issuer
    return subject_cn(anchor_name)


def check_host(host, known_cns):
    try:
        chain = fetch_chain(host)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return "ERRO", "conexao falhou: {}".format(exc)
    if not chain:
        return "ERRO", "nenhum certificado recebido"

    anchor_cn = resolve_anchor_cn(chain)
    if anchor_cn is None:
        return "ERRO", "certificado sem CN de assunto/emissor"
    if anchor_cn in known_cns:
        return "OK", anchor_cn
    return "FALTA", anchor_cn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host", help="checa um unico host, em vez de varrer SOURCES"
    )
    args = parser.parse_args()

    known_cns = local_anchor_cns()

    if args.host:
        hosts = [args.host]
    else:
        hosts = sorted(hosts_from_sources(load_sources()) | hosts_from_osm_connector())

    failed = False
    for host in hosts:
        status, detail = check_host(host, known_cns)
        print("{} -> {} [{}]".format(host, detail, status))
        if status != "OK":
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
