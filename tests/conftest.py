# -*- coding: utf-8 -*-
"""Fixtures globais para a suite de testes do gisbr."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qgis_app():
    try:
        from qgis.testing import start_app
    except ImportError:
        yield None
        return

    app = start_app()
    yield app
