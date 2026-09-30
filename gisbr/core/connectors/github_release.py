# -*- coding: utf-8 -*-
"""Conector para assets de GitHub Releases com verificação SHA-256 e cache local.

Usa apenas o link público ``releases/download/{tag}/{asset}`` — sem a API REST
do GitHub, sem gastar a cota anônima. O download reusa
``downloader._fetch_to_cache`` (QgsBlockingNetworkRequest + configure_request,
gravação ``.part`` → replace) e a chave de cache carrega a tag da release:
como o asset de uma tag é imutável, o cache vale para sempre e uma tag nova
ganha chaves novas (D2 da rodada 22).
"""

import hashlib
import json
from pathlib import Path

from ..downloader import DownloadError, _fetch_to_cache


def url_asset(base, nome):
    """URL pública de download direto de um asset na release declarada em ``base``.

    ``base`` é a chave declarativa ``base_rm`` do catálogo (repo/tag/manifest);
    ``nome`` é o nome do arquivo do asset, lido do manifest.
    """
    return "https://github.com/{}/releases/download/{}/{}".format(
        base["repo"].strip("/"), base["tag"], nome)


def _cache_key(base, nome):
    # ex.: gisbr_base_osm-20260929_osm_vias_rm04501.gpkg.zip
    return "{}_{}_{}".format(base["repo"].rstrip("/").split("/")[-1], base["tag"], nome)


def fetch_manifest(base, feedback=None):
    """Baixa (ou pega do cache) o manifest da release e devolve o dict parseado.

    Levanta DownloadError se o JSON for inválido ou ``schema_version`` != 1 —
    o manifest é o contrato da base (D2) e versão desconhecida é erro, não
    palpite.
    """
    nome = base["manifest"]
    path = Path(_fetch_to_cache(_cache_key(base, nome), [url_asset(base, nome)],
                                feedback=feedback))
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DownloadError(
            "manifest inválido ({} tag {}): {}".format(nome, base["tag"], exc))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        versao = manifest.get("schema_version") if isinstance(manifest, dict) else type(manifest).__name__
        raise DownloadError(
            "schema_version incompatível no manifest ({} tag {}): {} (esperado: 1)".format(
                nome, base["tag"], versao))
    return manifest


def fetch_asset(base, nome, sha256=None, feedback=None):
    """Baixa (ou pega do cache) um asset da release e confere o SHA-256.

    O hash é calculado em blocos de 1 MiB. Hash divergente **apaga o arquivo
    do cache** (um arquivo corrompido nunca fica no cache) e levanta
    DownloadError com o esperado e o calculado (D2).
    """
    path = Path(_fetch_to_cache(_cache_key(base, nome), [url_asset(base, nome)],
                                feedback=feedback))
    if sha256 is None:
        return path
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            bloco = f.read(1024 * 1024)
            if not bloco:
                break
            h.update(bloco)
    calculado = h.hexdigest()
    esperado = str(sha256).strip().lower()
    if calculado != esperado:
        path.unlink()
        raise DownloadError(
            "sha256 divergente para {} (tag {}): esperado {}, calculado {}".format(
                nome, base["tag"], esperado, calculado))
    return path


def entrada_rm(manifest, id_rm, tag=""):
    """Busca a entrada de uma RM no manifest — o manifest é o contrato (D3).

    Os ids do catálogo do plugin casam 1:1 com as chaves de ``manifest["rms"]``
    (M4); o caso "sem entrada" existe para bases futuras ou divergência entre
    o CSV do IBGE e a release, e vira motivo de pulo, não de falha.

    Returns:
        (entrada, None) quando a RM existe com ``status == "ok"``;
        (None, motivo) quando ausente ou com montagem falhada.
    """
    entrada = (manifest.get("rms") or {}).get(str(id_rm))
    if entrada is None:
        return None, "RM {} não está na base {}".format(id_rm, tag)
    if entrada.get("status") != "ok":
        return None, "RM {} falhou na montagem da base {} (status={})".format(
            id_rm, tag, entrada.get("status"))
    return entrada, None
