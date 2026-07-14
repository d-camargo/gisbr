# -*- coding: utf-8 -*-
"""Download com cache em disco e cadeia de mirrors (IPEA -> GitHub).

100% API nativa: QgsBlockingNetworkRequest + QNetworkRequest + stdlib.
Sem requests / urllib de terceiros.
"""

from pathlib import Path

from qgis.PyQt.QtCore import QStandardPaths, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsBlockingNetworkRequest

from .constants import CACHE_SUBDIR, GITHUB_MIRRORS, IPEA_V2_FALLBACK_BASE


class DownloadError(Exception):
    """Falha ao baixar um recurso de todos os mirrors."""


def cache_dir():
    """Diretorio de cache em disco: ~/.cache/geobr-qgis/ (ou equivalente)."""
    base = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
    # CacheLocation ja inclui o nome da app no QGIS; ainda assim isolamos.
    path = Path(base) / CACHE_SUBDIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _mirror_urls(url):
    """Dada uma URL primaria, devolve [primaria, *mirrors] usando o file_id."""
    file_id = url.rstrip("/").split("/")[-1]
    return [url] + [mirror.rstrip("/") + "/" + file_id for mirror in GITHUB_MIRRORS]


def _configure_ssl_config(request):
    """Carrega o certificado intermediario/raiz do IPEA (se existir) e injeta na request.

    Sem alterar o PeerVerifyMode.
    """
    cert_path = Path(__file__).parent / "certs" / "ipea_chain.pem"
    if cert_path.exists():
        try:
            from qgis.PyQt.QtNetwork import QSslCertificate
            certs = QSslCertificate.fromPath(str(cert_path))
            if certs:
                ssl_config = request.sslConfiguration()
                ssl_config.addCaCertificates(certs)
                request.setSslConfiguration(ssl_config)
        except Exception:
            pass


def _http_get(url):
    """GET sincrono via QgsBlockingNetworkRequest. Retorna bytes ou levanta."""
    request = QNetworkRequest(QUrl(url))
    # Alguns servidores (IPEA) filtram por User-Agent vazio.
    request.setHeader(
        QNetworkRequest.KnownHeaders.UserAgentHeader,
        "geobr-qgis/0.1 (+https://github.com/d-camargo/geobr-qgis)",
    )
    _configure_ssl_config(request)
    blocking = QgsBlockingNetworkRequest()
    err = blocking.get(request, forceRefresh=True)
    if err != QgsBlockingNetworkRequest.ErrorCode.NoError:
        raise DownloadError(blocking.errorMessage() or f"erro de rede em {url}")
    reply = blocking.reply()
    status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
    if status is not None and int(status) >= 400:
        raise DownloadError(f"HTTP {status} em {url}")
    data = bytes(reply.content())
    if not data:
        raise DownloadError(f"resposta vazia em {url}")
    return data


def _format_friendly_error(errors, file_id=None):
    """Gera uma mensagem de erro amigável em português explicando as causas prováveis."""
    details = "\n".join(errors)
    target = f" '{file_id}'" if file_id else ""
    return (
        f"Não foi possível concluir o download{target} de nenhuma das fontes/mirrors disponíveis.\n\n"
        "Causas prováveis:\n"
        "1. Certificado intermediário SSL ausente ou desatualizado no QGIS/sistema (ex.: cadeia incompleta do servidor IPEA).\n"
        "2. Antivírus, firewall ou proxy corporativo interceptando a conexão HTTPS (inspeção de tráfego SSL/TLS - MITM).\n"
        "3. Falta de conexão com a internet ou indisponibilidade temporária nos servidores do IPEA/GitHub.\n\n"
        "Recomendações:\n"
        "- Se estiver em rede corporativa, verifique se há bloqueios a conexões seguras externas.\n"
        "- O plugin tenta usar cópias locais/cache quando aplicável, mas o download inicial exige uma conexão funcional.\n\n"
        f"Detalhes técnicos dos erros:\n{details}"
    )


def fetch_bytes(url):
    """Baixa um recurso tentando IPEA -> mirrors. Retorna bytes.

    Nao usa cache (para metadados pequenos que cacheamos em memoria/CSV).
    """
    errors = []
    for candidate in _mirror_urls(url):
        try:
            return _http_get(candidate)
        except DownloadError as exc:  # tenta proximo mirror
            errors.append(f"  - {candidate}: {exc}")
    raise DownloadError(_format_friendly_error(errors))


def _fetch_to_cache(file_id, urls, feedback=None):
    """Baixa um arquivo para o cache tentando ``urls`` em ordem. Retorna Path."""
    dest = cache_dir() / file_id

    if dest.exists() and dest.stat().st_size > 0:
        if feedback is not None:
            feedback.pushInfo(f"[cache] {file_id}")
        return dest

    if feedback is not None:
        feedback.pushInfo(f"[download] {file_id}")

    errors = []
    for candidate in urls:
        try:
            data = _http_get(candidate)
        except DownloadError as exc:
            errors.append(f"  - {candidate}: {exc}")
            continue
        if not data:
            errors.append(f"  - {candidate}: arquivo vazio")
            continue
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(dest)
        return dest

    raise DownloadError(_format_friendly_error(errors, file_id))


def fetch(url, feedback=None):
    """Baixa um arquivo do backend v1.7.0 (GPKG) para o cache. Retorna Path.

    Cadeia ``url_solver`` do geobr: IPEA primario -> mirror GitHub (mesmo
    file_id).
    """
    file_id = url.rstrip("/").split("/")[-1]
    return _fetch_to_cache(file_id, _mirror_urls(url), feedback=feedback)


def fetch_v2(file_name, download_url, feedback=None):
    """Baixa um arquivo .parquet do backend v2 para o cache. Retorna Path.

    Cadeia INVERTIDA em relacao ao v1.7.0: GitHub (asset) primario -> IPEA
    fallback (``data_v2.0.0/<file_name>``).
    """
    urls = [download_url, f"{IPEA_V2_FALLBACK_BASE}/{file_name}"]
    return _fetch_to_cache(file_name, urls, feedback=feedback)


def fetch_asset(file_name, url, feedback=None):
    """Baixa um asset por URL unica para o cache (ex.: parquet do censobr)."""
    return _fetch_to_cache(file_name, [url], feedback=feedback)
