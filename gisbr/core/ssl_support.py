# -*- coding: utf-8 -*-
"""Modulo unico de material confiavel (CA) do plugin.

Centraliza a injecao de certificados de autoridade certificadora empacotados
em ``core/certs/*.pem``. Serve tanto para requests individuais
(``configure_request``) quanto para a configuracao SSL padrao do processo
(``install_default_ca_certificates``), usada pelos caminhos que nao expoem a
``QNetworkRequest`` (ex.: basemap XYZ).

Regras (ver §10 do CLAUDE.md):
- **Nunca** mexer em ``PeerVerifyMode`` — a correcao e *adicionar confianca*,
  jamais *remover verificacao*.
- Os ``.pem`` sao carregados por **varredura do diretorio**, nunca por nome
  fixo: cobrir um servidor novo e soltar um arquivo, nao editar codigo.
- Nada aqui levanta excecao; falhas ficam registradas em ``last_errors()``.
"""

from pathlib import Path

try:
    from qgis.PyQt.QtNetwork import QSslCertificate, QSslConfiguration
    SSL_AVAILABLE = True
except ImportError:  # build do Qt sem suporte a SSL
    QSslCertificate = None
    QSslConfiguration = None
    SSL_AVAILABLE = False


CERTS_DIR = Path(__file__).parent / "certs"

_certs_cache = None
_errors = []
_default_installed = False


def last_errors():
    """Falhas de carregamento acumuladas (lista de strings, possivelmente vazia)."""
    return list(_errors)


def ca_certificates():
    """Todos os certificados de ``core/certs/*.pem``, concatenados e memoizados.

    Devolve lista de ``QSslCertificate`` (vazia se nao houver SSL ou material).
    Nunca levanta.
    """
    global _certs_cache
    if _certs_cache is not None:
        return _certs_cache

    certs = []
    if not SSL_AVAILABLE:
        _errors.append("Qt sem suporte a SSL: certificados do plugin nao carregados.")
        _certs_cache = certs
        return _certs_cache

    try:
        pem_files = sorted(CERTS_DIR.glob("*.pem"))
    except Exception as exc:
        _errors.append("Falha ao varrer {}: {}".format(CERTS_DIR, exc))
        _certs_cache = certs
        return _certs_cache

    if not pem_files:
        _errors.append("Nenhum .pem encontrado em {}.".format(CERTS_DIR))

    for pem in pem_files:
        try:
            loaded = QSslCertificate.fromPath(str(pem))
        except Exception as exc:
            _errors.append("Falha ao ler {}: {}".format(pem.name, exc))
            continue
        if loaded:
            certs.extend(loaded)
        else:
            _errors.append("Nenhum certificado valido em {}.".format(pem.name))

    _certs_cache = certs
    return _certs_cache


def _base_certificates(ssl_config):
    """CAs de partida sobre as quais as do plugin sao acrescentadas.

    Cuidado nao-obvio: o Qt carrega as raizes do sistema **sob demanda**, entao
    ``caCertificates()`` costuma vir vazia — e ``addCaCertificates()`` desliga
    esse carregamento sob demanda. Somar as nossas a uma lista vazia trocaria a
    loja inteira do sistema pelos poucos PEMs do plugin. Semear com
    ``systemCaCertificates()`` mantem a injecao puramente **aditiva**.
    """
    certs = ssl_config.caCertificates()
    if certs:
        return list(certs)
    try:
        return list(QSslConfiguration.systemCaCertificates())
    except Exception as exc:
        _errors.append("Falha ao ler as CAs do sistema: {}".format(exc))
        return []


def configure_request(request):
    """Acrescenta as CAs do plugin a ``request`` (``QNetworkRequest``).

    Nao altera ``PeerVerifyMode``. Nunca levanta.
    """
    if not SSL_AVAILABLE:
        return
    certs = ca_certificates()
    if not certs:
        return
    try:
        ssl_config = request.sslConfiguration()
        ssl_config.setCaCertificates(_base_certificates(ssl_config) + certs)
        request.setSslConfiguration(ssl_config)
    except Exception as exc:
        _errors.append("Falha ao injetar CAs na request: {}".format(exc))


def install_default_ca_certificates():
    """Acrescenta as CAs do plugin a ``QSslConfiguration`` padrao do processo.

    Alcanca os caminhos que nao expoem a ``QNetworkRequest`` (basemap XYZ e
    requisicoes feitas pelo proprio QGIS). Idempotente e nunca levanta.
    Devolve ``True`` se as CAs estao instaladas.
    """
    global _default_installed
    if _default_installed:
        return True
    if not SSL_AVAILABLE:
        return False
    certs = ca_certificates()
    if not certs:
        return False
    try:
        default_config = QSslConfiguration.defaultConfiguration()
        default_config.setCaCertificates(_base_certificates(default_config) + certs)
        QSslConfiguration.setDefaultConfiguration(default_config)
    except Exception as exc:
        _errors.append("Falha ao instalar CAs na configuracao padrao: {}".format(exc))
        return False
    _default_installed = True
    return True
