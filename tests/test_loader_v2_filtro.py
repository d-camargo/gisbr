# -*- coding: utf-8 -*-
import pytest

pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq

from gisbr.core import capabilities
from gisbr.core.loader_v2 import LoaderV2Error, _load_with_gdal, _load_with_pyarrow


@pytest.fixture
def sample_parquet(tmp_path):
    file_path = tmp_path / "sample.parquet"
    table = pa.Table.from_arrays(
        [
            pa.array(["MG", "MG", "SP", "RJ"]),
            pa.array([3106200, 3100100, 3550308, 3304557]),
            pa.array(["Belo Horizonte", "Abadia dos Dourados", "São Paulo", "Rio de Janeiro"]),
        ],
        names=["abbrev_state", "code_muni", "name_muni"],
    )
    pq.write_table(table, str(file_path))
    return file_path


def test_filtro_igualdade_texto(sample_parquet):
    layer = _load_with_pyarrow(sample_parquet, "test_layer", filtro=("abbrev_state", "MG", "igual"))
    assert layer.isValid()
    assert layer.featureCount() == 2
    for feat in layer.getFeatures():
        assert feat["abbrev_state"] == "MG"


def test_filtro_igualdade_inteiro(sample_parquet):
    # Passando inteiro
    layer = _load_with_pyarrow(sample_parquet, "test_layer", filtro=("code_muni", 3106200, "igual"))
    assert layer.isValid()
    assert layer.featureCount() == 1
    feat = next(layer.getFeatures())
    assert feat["code_muni"] == 3106200

    # Passando string (coacao para int)
    layer2 = _load_with_pyarrow(sample_parquet, "test_layer", filtro=("code_muni", "3106200", "igual"))
    assert layer2.isValid()
    assert layer2.featureCount() == 1


def test_filtro_prefixo(sample_parquet):
    # Prefixo em coluna numerica (coacao e cast para string)
    layer = _load_with_pyarrow(sample_parquet, "test_layer", filtro=("code_muni", "31", "prefixo"))
    assert layer.isValid()
    assert layer.featureCount() == 2

    # Prefixo em coluna texto
    layer2 = _load_with_pyarrow(sample_parquet, "test_layer", filtro=("name_muni", "Rio", "prefixo"))
    assert layer2.isValid()
    assert layer2.featureCount() == 1
    feat = next(layer2.getFeatures())
    assert feat["name_muni"] == "Rio de Janeiro"


def test_filtro_coluna_inexistente(sample_parquet):
    with pytest.raises(LoaderV2Error) as exc_info:
        _load_with_pyarrow(sample_parquet, "test_layer", filtro=("coluna_fantasma", "val", "igual"))
    err_msg = str(exc_info.value)
    assert "coluna_fantasma" in err_msg
    assert "abbrev_state" in err_msg


def test_filtro_gdal(sample_parquet):
    if not capabilities.parquet_available():
        pytest.skip("Driver GDAL Parquet nao disponivel")
    layer = _load_with_gdal(sample_parquet, "test_layer", filtro=("abbrev_state", "MG", "igual"))
    assert layer.isValid()
    assert layer.featureCount() == 2

    with pytest.raises(LoaderV2Error):
        _load_with_gdal(sample_parquet, "test_layer", filtro=("coluna_fantasma", "val", "igual"))
