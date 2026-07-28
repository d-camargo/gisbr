# -*- coding: utf-8 -*-
"""Deteccao de capacidades do ambiente (Fase 2).

A Fase 2 (backend Parquet/GeoParquet do v2.0.0 e integracao com o censobr)
depende do driver GDAL *Parquet*/*Arrow*, que e distribuido a parte do GDAL
core e pode nao estar presente — especialmente em builds do apt do
Ubuntu/Pop!_OS.

Este modulo NAO instala nada e NAO converte arquivos. Apenas detecta e, se o
driver faltar, fornece uma mensagem amigavel com as opcoes de instalacao.
"""

from osgeo import ogr


def parquet_available():
    """True se o driver GDAL Parquet (ou Arrow) estiver disponivel."""
    for name in ("Parquet", "Arrow"):
        if ogr.GetDriverByName(name) is not None:
            return True
    return False


def pyarrow_available():
    """True se o pacote python `pyarrow` estiver importavel.

    Fallback para ler (Geo)Parquet quando o driver GDAL nao existe (caso do
    QGIS empacotado via apt/flatpak no Linux). Instalavel com:
        pip install --user pyarrow
    """
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        return False


def parquet_backend():
    """Retorna o backend de leitura Parquet disponivel: 'gdal', 'pyarrow' ou None."""
    if parquet_available():
        return "gdal"
    if pyarrow_available():
        return "pyarrow"
    return None


def gdal_version():
    from osgeo import gdal
    return gdal.__version__


def install_hint():
    """Mensagem orientando a instalacao do driver (sem executar nada).

    Observacao verificada em Pop!_OS / Ubuntu 'noble' (GDAL 3.8.4): o pacote
    apt ``gdal-plugins`` NAO inclui o driver arrow/parquet (nao instala nenhum
    .so), e nao ha ``libarrow-dev``/``libparquet-dev`` no apt para compilar.
    Portanto, nesta familia de sistema, os caminhos reais sao Flatpak ou conda.
    """
    ver = gdal_version()
    return (
        "Backend v2 (Parquet) indisponivel: nem o driver GDAL 'Parquet'/'Arrow' "
        f"(GDAL {ver}) nem o pacote python 'pyarrow' foram encontrados.\n\n"
        "A Fase 1 (GeoPackage) continua funcionando normalmente.\n\n"
        "Para habilitar o v2/censobr, escolha UMA opcao:\n\n"
        "  [A] pyarrow (recomendado no Linux apt/flatpak — usa o QGIS atual):\n"
        "        pip install --user pyarrow\n\n"
        "  [B] driver GDAL nativo (Windows/macOS oficiais ja costumam ter):\n"
        "        conda-forge: conda install -c conda-forge libgdal-arrow-parquet\n"
        "        verifique:   ogrinfo --formats | grep -i parquet\n\n"
        "ATENCAO (Pop!_OS/Ubuntu/Flatpak): o driver GDAL parquet NAO vem nessas "
        "builds (verificado em GDAL 3.8.4 apt e 3.13 flatpak). Use a opcao [A]."
    )
