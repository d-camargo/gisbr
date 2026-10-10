# -*- coding: utf-8 -*-
import pytest

pa = pytest.importorskip("pyarrow")

from gisbr.core.parquet_filtro import FiltroParquetError, mascara


def test_igual_double_texto_int_float():
    table = pa.Table.from_arrays(
        [pa.array([3106200.0, 3100100.0, 3550308.0])],
        names=["code_muni"],
    )
    # valor texto "3106200"
    m_txt = mascara(table, ("code_muni", "3106200", "igual"))
    res_txt = table.filter(m_txt)
    assert res_txt.num_rows == 1
    assert res_txt["code_muni"].to_pylist() == [3106200.0]

    # valor int 3106200
    m_int = mascara(table, ("code_muni", 3106200, "igual"))
    res_int = table.filter(m_int)
    assert res_int.num_rows == 1
    assert res_int["code_muni"].to_pylist() == [3106200.0]

    # valor float 3106200.0
    m_flt = mascara(table, ("code_muni", 3106200.0, "igual"))
    res_flt = table.filter(m_flt)
    assert res_flt.num_rows == 1
    assert res_flt["code_muni"].to_pylist() == [3106200.0]


def test_igual_inteiro_texto_e_float():
    table = pa.Table.from_arrays(
        [pa.array([3106200, 3100100, 3550308])],
        names=["code_muni"],
    )
    # valor texto "3106200"
    m_txt = mascara(table, ("code_muni", "3106200", "igual"))
    res_txt = table.filter(m_txt)
    assert res_txt.num_rows == 1
    assert res_txt["code_muni"].to_pylist() == [3106200]

    # valor float 3106200.0
    m_flt = mascara(table, ("code_muni", 3106200.0, "igual"))
    res_flt = table.filter(m_flt)
    assert res_flt.num_rows == 1
    assert res_flt["code_muni"].to_pylist() == [3106200]

    # valor int 3106200
    m_int = mascara(table, ("code_muni", 3106200, "igual"))
    res_int = table.filter(m_int)
    assert res_int.num_rows == 1
    assert res_int["code_muni"].to_pylist() == [3106200]


def test_igual_texto():
    table = pa.Table.from_arrays(
        [pa.array(["MG", "SP", "RJ"])],
        names=["abbrev_state"],
    )
    mask = mascara(table, ("abbrev_state", "MG", "igual"))
    res = table.filter(mask)
    assert res.num_rows == 1
    assert res["abbrev_state"].to_pylist() == ["MG"]


def test_prefixo_double_setor_15_digitos():
    table = pa.Table.from_arrays(
        [pa.array([310620005000001.0, 310010005000001.0, 355030805000001.0])],
        names=["code_tract"],
    )
    mask = mascara(table, ("code_tract", "3106200", "prefixo"))
    res = table.filter(mask)
    assert res.num_rows == 1
    assert res["code_tract"].to_pylist() == [310620005000001.0]


def test_prefixo_inteiro_e_texto():
    # Inteiro
    t_int = pa.Table.from_arrays(
        [pa.array([3106200, 3100100, 3550308])],
        names=["code_muni"],
    )
    m_int = mascara(t_int, ("code_muni", "31", "prefixo"))
    res_int = t_int.filter(m_int)
    assert res_int.num_rows == 2
    assert res_int["code_muni"].to_pylist() == [3106200, 3100100]

    # Texto
    t_txt = pa.Table.from_arrays(
        [pa.array(["Belo Horizonte", "Betim", "São Paulo"])],
        names=["name_muni"],
    )
    m_txt = mascara(t_txt, ("name_muni", "Be", "prefixo"))
    res_txt = t_txt.filter(m_txt)
    assert res_txt.num_rows == 2
    assert res_txt["name_muni"].to_pylist() == ["Belo Horizonte", "Betim"]


def test_nulo_fora_do_resultado():
    # Double com nulos (igual e prefixo)
    t_double = pa.Table.from_arrays(
        [pa.array([3106200.0, None, 3100100.0, None])],
        names=["code_muni"],
    )
    m_eq = mascara(t_double, ("code_muni", "3106200", "igual"))
    res_eq = t_double.filter(m_eq)
    assert res_eq.num_rows == 1
    assert None not in res_eq["code_muni"].to_pylist()

    m_pref = mascara(t_double, ("code_muni", "31", "prefixo"))
    res_pref = t_double.filter(m_pref)
    assert res_pref.num_rows == 2
    assert None not in res_pref["code_muni"].to_pylist()

    # Inteiro com nulos
    t_int = pa.Table.from_arrays(
        [pa.array([3106200, None, 3100100])],
        names=["code_muni"],
    )
    m_int = mascara(t_int, ("code_muni", "3106200", "igual"))
    res_int = t_int.filter(m_int)
    assert res_int.num_rows == 1
    assert None not in res_int["code_muni"].to_pylist()

    # Texto com nulos
    t_txt = pa.Table.from_arrays(
        [pa.array(["MG", None, "SP"])],
        names=["abbrev_state"],
    )
    m_txt = mascara(t_txt, ("abbrev_state", "MG", "igual"))
    res_txt = t_txt.filter(m_txt)
    assert res_txt.num_rows == 1
    assert None not in res_txt["abbrev_state"].to_pylist()


def test_mg_em_coluna_double_lanca_filtro_parquet_error():
    table = pa.Table.from_arrays(
        [pa.array([3106200.0, 3100100.0])],
        names=["code_muni"],
    )
    with pytest.raises(FiltroParquetError) as exc_info:
        mascara(table, ("code_muni", "MG", "igual"))
    msg = str(exc_info.value)
    assert "code_muni" in msg
    assert "MG" in msg


def test_coluna_ausente_e_modo_desconhecido():
    table = pa.Table.from_arrays(
        [pa.array([3106200.0])],
        names=["code_muni"],
    )
    # Coluna ausente
    with pytest.raises(FiltroParquetError) as exc_col:
        mascara(table, ("coluna_fantasma", "3106200", "igual"))
    msg_col = str(exc_col.value)
    assert "coluna_fantasma" in msg_col
    assert "code_muni" in msg_col
    assert "Coluna 'coluna_fantasma' ausente no schema." in msg_col

    # Modo desconhecido
    with pytest.raises(FiltroParquetError) as exc_modo:
        mascara(table, ("code_muni", "3106200", "contem"))
    msg_modo = str(exc_modo.value)
    assert "Modo de filtro desconhecido: 'contem'" in msg_modo


def test_double_nao_integral_no_prefixo_lanca_filtro_parquet_error():
    table = pa.Table.from_arrays(
        [pa.array([3106200.5, 3100100.0])],
        names=["code_muni"],
    )
    with pytest.raises(FiltroParquetError) as exc_info:
        mascara(table, ("code_muni", "3106200", "prefixo"))
    msg = str(exc_info.value)
    assert "code_muni" in msg
