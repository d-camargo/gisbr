# -*- coding: utf-8 -*-
"""Harness de reprodução da visibilidade do botão GISBR na pluginToolBar.

Verifica se o botão GISBR na barra de plugins (pluginToolBar) está visível
no startup do QGIS e após recarregar o plugin com reloadPlugin("gisbr").
Sai com código 0 se ambos estiverem visíveis, ou 1 caso contrário.
"""

import os
import sys
from qgis.PyQt.QtCore import QCoreApplication, QTimer
from qgis.PyQt.QtGui import QGuiApplication
import qgis.utils


def _checar_barra():
    platform = QGuiApplication.platformName()

    # 1. Medição no startup
    tb = qgis.utils.iface.pluginToolBar() if getattr(qgis.utils, "iface", None) else None
    plugin = qgis.utils.plugins.get("gisbr") if hasattr(qgis.utils, "plugins") else None
    action = getattr(plugin, "action", None) if plugin else None
    btn = tb.widgetForAction(action) if (tb and action) else None

    w_startup = tb.width() if tb else -1
    v_startup = btn.isVisible() if btn else False
    print(f"Startup: platform={platform} toolbar_width={w_startup} visible={v_startup}")

    # 2. Medição após reloadPlugin("gisbr")
    qgis.utils.reloadPlugin("gisbr")
    QCoreApplication.processEvents()

    tb2 = qgis.utils.iface.pluginToolBar() if getattr(qgis.utils, "iface", None) else None
    plugin2 = qgis.utils.plugins.get("gisbr") if hasattr(qgis.utils, "plugins") else None
    action2 = getattr(plugin2, "action", None) if plugin2 else None
    btn2 = tb2.widgetForAction(action2) if (tb2 and action2) else None

    w_reload = tb2.width() if tb2 else -1
    v_reload = btn2.isVisible() if btn2 else False
    print(f"Reload: platform={platform} toolbar_width={w_reload} visible={v_reload}")

    # 3. Fechar janela e sair com código 0 apenas se ambos estiverem visíveis
    sys.stdout.flush()
    sys.stderr.flush()

    if v_startup and v_reload:
        print("Resultado: SUCESSO (visível no startup e após reload)")
        sys.stdout.flush()
        os._exit(0)
    else:
        print("Resultado: FALHA (botão oculto no transbordo)")
        sys.stdout.flush()
        os._exit(1)


# Aguarda ~8 segundos para a interface e barras terminarem de carregar
QTimer.singleShot(8000, _checar_barra)
