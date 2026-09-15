# -*- coding: utf-8 -*-
"""Helper de ícone compartilhado entre a Caixa de Ferramentas e a barra de ferramentas do plugin."""

import os

from qgis.PyQt.QtGui import QIcon

_CANDIDATOS = ("icon.svg", "icon.png")


def icon_path():
    """Retorna o caminho do primeiro arquivo de ícone encontrado ou None."""
    here = os.path.dirname(__file__)
    for nome in _CANDIDATOS:
        path = os.path.join(here, nome)
        if os.path.exists(path):
            return path
    return None


def plugin_icon():
    """Retorna QIcon com o ícone do plugin ou QIcon() vazio se nenhum for encontrado."""
    path = icon_path()
    if path is not None:
        return QIcon(path)
    return QIcon()
