# -*- coding: utf-8 -*-
"""Compatibilidade de tipos do QGIS entre versões 3.x e 4.x (Qt5/Qt6)."""

try:
    from qgis.PyQt.QtCore import QMetaType
except ImportError:
    QMetaType = None

try:
    from qgis.PyQt.QtCore import QVariant
except ImportError:
    QVariant = None


def field_type(kind):
    """Retorna o tipo de dado compatível com QgsField para a versão do QGIS em uso.

    Mapeia kind em {"bool", "int", "double", "string"} para QVariant.Type se
    QVariant estiver disponível (QGIS 3.x / PyQt5), senão cai para
    QMetaType.Type (QGIS 4.x / PyQt6, onde QVariant deixou de existir).

    QVariant é tentado primeiro (não QMetaType) porque o construtor
    QgsField(nome, QMetaType.Type) só existe a partir do QGIS ~3.38: em
    QGIS 3.16-3.37 o QMetaType também importa com sucesso, então testar sua
    disponibilidade não detectaria essa limitação e quebraria o QgsField().
    """
    kind_lower = str(kind).lower()

    # 1. Tentar usar QVariant primeiro (Qt5/PyQt5 / QGIS 3.x)
    if QVariant is not None:
        variant_map = {
            "bool": QVariant.Bool,
            "int": QVariant.LongLong,
            "longlong": QVariant.LongLong,
            "double": QVariant.Double,
            "string": QVariant.String,
        }
        return variant_map.get(kind_lower, QVariant.Invalid)

    # 2. Fallback para QMetaType (Qt6/PyQt6 / QGIS 4.x)
    if QMetaType is not None:
        type_enum = getattr(QMetaType, "Type", None)
        if type_enum is not None:
            meta_attr_map = {
                "bool": "Bool",
                "int": "LongLong",
                "longlong": "LongLong",
                "double": "Double",
                "string": "QString",
            }
            attr_name = meta_attr_map.get(kind_lower)
            if attr_name and hasattr(type_enum, attr_name):
                return getattr(type_enum, attr_name)

    return None
