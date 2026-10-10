# -*- coding: utf-8 -*-
"""Filtro puro em tabelas pyarrow para o backend Parquet.

Módulo sem dependências do ambiente SIG para permitir execução isolada
em ambientes e testes que disponham apenas do pyarrow.
"""

import decimal

try:
    import pyarrow as pa
    import pyarrow.compute as pc
except ImportError:  # pragma: no cover
    pa = None
    pc = None


class FiltroParquetError(ValueError):
    """Erro ao aplicar filtro em tabela Parquet/Arrow."""
    pass


def mascara(table, filtro):
    """Calcula a máscara booleana para filtrar uma tabela pyarrow.

    Parâmetros:
        table: pyarrow.Table
        filtro: tupla (coluna, valor, modo), com modo em ("igual", "prefixo")

    Retorna:
        pyarrow.ChunkedArray ou pyarrow.BooleanArray com a máscara resultante.
    """
    global pa, pc
    if pa is None or pc is None:
        import pyarrow as pa
        import pyarrow.compute as pc

    try:
        coluna, valor, modo = filtro
    except (ValueError, TypeError) as exc:
        raise FiltroParquetError(
            f"Filtro inválido {filtro!r}: esperado (coluna, valor, modo)."
        ) from exc

    schema = table.schema
    if coluna not in schema.names:
        first_cols = ", ".join(schema.names[:5])
        raise FiltroParquetError(
            f"Coluna '{coluna}' ausente no schema. Colunas existentes: {first_cols}"
        )

    if modo not in ("igual", "prefixo"):
        raise FiltroParquetError(f"Modo de filtro desconhecido: '{modo}'")

    field_type = schema.field(coluna).type
    col_arr = table[coluna]

    try:
        if modo == "igual":
            if pa.types.is_integer(field_type):
                if isinstance(valor, bool):
                    raise FiltroParquetError(
                        f"Valor booleano {valor!r} incompatível com coluna inteira '{coluna}' (tipo {field_type})"
                    )
                if isinstance(valor, float):
                    if not valor.is_integer():
                        raise FiltroParquetError(
                            f"Valor {valor!r} não é inteiro para a coluna '{coluna}' (tipo {field_type})"
                        )
                    val_coagido = int(valor)
                elif isinstance(valor, int):
                    val_coagido = int(valor)
                else:
                    try:
                        val_coagido = int(valor)
                    except (ValueError, TypeError) as exc:
                        try:
                            f = float(valor)
                            if f.is_integer():
                                val_coagido = int(f)
                            else:
                                raise FiltroParquetError(
                                    f"Valor {valor!r} não é inteiro para a coluna '{coluna}' (tipo {field_type})"
                                ) from exc
                        except Exception:
                            raise FiltroParquetError(
                                f"Não foi possível converter valor {valor!r} para inteiro na coluna '{coluna}' (tipo {field_type})"
                            ) from exc
            elif pa.types.is_floating(field_type):
                if isinstance(valor, bool):
                    raise FiltroParquetError(
                        f"Valor booleano {valor!r} incompatível com coluna de ponto flutuante '{coluna}' (tipo {field_type})"
                    )
                try:
                    val_coagido = float(valor)
                except (ValueError, TypeError) as exc:
                    raise FiltroParquetError(
                        f"Não foi possível converter valor {valor!r} para float na coluna '{coluna}' (tipo {field_type})"
                    ) from exc
            elif pa.types.is_decimal(field_type):
                if isinstance(valor, bool):
                    raise FiltroParquetError(
                        f"Valor booleano {valor!r} incompatível com coluna decimal '{coluna}' (tipo {field_type})"
                    )
                try:
                    val_coagido = decimal.Decimal(str(valor))
                except (decimal.DecimalException, ValueError, TypeError) as exc:
                    raise FiltroParquetError(
                        f"Não foi possível converter valor {valor!r} para decimal na coluna '{coluna}' (tipo {field_type})"
                    ) from exc
            elif pa.types.is_string(field_type) or pa.types.is_large_string(field_type):
                val_coagido = str(valor)
            else:
                val_coagido = valor

            mask = pc.equal(col_arr, val_coagido)

        elif modo == "prefixo":
            if isinstance(valor, float) and valor.is_integer():
                val_coagido = str(int(valor))
            else:
                val_coagido = str(valor)

            if pa.types.is_string(field_type) or pa.types.is_large_string(field_type):
                col_str = col_arr
            elif pa.types.is_floating(field_type) or pa.types.is_decimal(field_type):
                try:
                    col_int = pc.cast(col_arr, pa.int64())
                    col_str = pc.cast(col_int, pa.string())
                except (pa.ArrowInvalid, pa.ArrowNotImplementedError) as exc:
                    raise FiltroParquetError(
                        f"Coluna '{coluna}' (tipo {field_type}) contém valor não integral ou incompatível com conversão para int64 no filtro por prefixo: {exc}"
                    ) from exc
            else:
                try:
                    col_str = pc.cast(col_arr, pa.string())
                except (pa.ArrowInvalid, pa.ArrowNotImplementedError) as exc:
                    raise FiltroParquetError(
                        f"Erro ao converter coluna '{coluna}' (tipo {field_type}) para string no filtro por prefixo: {exc}"
                    ) from exc

            mask = pc.starts_with(col_str, val_coagido)

        return mask

    except FiltroParquetError:
        raise
    except (
        pa.ArrowNotImplementedError,
        pa.ArrowInvalid,
        pa.ArrowTypeError,
        pa.ArrowException,
        ValueError,
        TypeError,
    ) as exc:
        raise FiltroParquetError(str(exc)) from exc
