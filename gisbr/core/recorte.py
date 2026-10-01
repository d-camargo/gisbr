# -*- coding: utf-8 -*-
from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class Recorte:
    tipo: str
    id: str
    nome: str
    codes: List[str]
    bbox: Optional[list] = None
    nomes: List[str] = field(default_factory=list)

    @classmethod
    def de_municipio(cls, code: str, nome: str, bbox=None):
        return cls(tipo="municipio", id=code, nome=nome, codes=[code], bbox=bbox, nomes=[nome])

    @classmethod
    def de_rm(cls, id_rm: str, nome: str, codes: List[str], nomes: Optional[List[str]] = None):
        return cls(tipo="rm", id=id_rm, nome=nome, codes=codes, nomes=list(nomes or []))

    @classmethod
    def de_agregado(cls, tipo: str, id_agregado: str, nome: str, codes: List[str], nomes: Optional[List[str]] = None):
        return cls(tipo=tipo, id=id_agregado, nome=nome, codes=codes, nomes=list(nomes or []))

    @property
    def sufixo(self) -> str:
        if self.e_agregado:
            return f"{self.tipo}{self.id}".lower()
        return self.id

    @property
    def nome_camada_limite(self) -> Optional[str]:
        """Nome da camada de limite no GeoPackage (D7: `<tipo>_<id>`); None no modo município."""
        if self.e_agregado:
            return f"{self.tipo}_{self.id}".lower()
        return None

    @property
    def rotulo(self) -> str:
        if self.tipo == "rm":
            return self.nome.replace("Região Metropolitana ", "RM ").replace("Regiões Metropolitanas ", "RMs ")
        return self.nome

    def codes_por_uf(self) -> Dict[str, List[str]]:
        resultado = {}
        for c in self.codes:
            uf = c[:2]
            if uf not in resultado:
                resultado[uf] = []
            resultado[uf].append(c)
        return resultado

    @property
    def uf_por_code(self) -> Dict[str, List[str]]:
        return self.codes_por_uf()

    @property
    def e_agregado(self) -> bool:
        return self.tipo != "municipio"

    @property
    def e_rm(self) -> bool:
        return self.tipo == "rm"

    # Ranking de escala do recorte (D3): municipio=0, micro=1, rm=1, meso=2,
    # macsaud=2, uf=3, macro=4. Agregado desconhecido cai no nível regional (2).
    _ESCALA_RECORTE = {"municipio": 0, "micro": 1, "rm": 1, "meso": 2, "macsaud": 2, "uf": 3, "macro": 4}

    @property
    def escala(self) -> int:
        return self._ESCALA_RECORTE.get(self.tipo, 2 if self.e_agregado else 0)

    @property
    def siglas_uf(self) -> List[str]:
        from gisbr.core.constants import UF_CODE_TO_ABBREV
        siglas = {UF_CODE_TO_ABBREV[int(uf)] for uf in self.codes_por_uf()
                  if int(uf) in UF_CODE_TO_ABBREV}
        return sorted(siglas)


def camada_do_recorte(recorte: Recorte, feedback=None, algo: str = "read_municipality", extra_params: dict = None):
    """
    Retorna a camada do recorte (executando gisbr:<algo> por UF e filtrando por code_muni IN (...)).
    """
    import processing
    from qgis.core import QgsMessageLog, Qgis

    grupos_uf = recorte.codes_por_uf()
    if not grupos_uf:
        msg = f"Nenhum código no recorte {recorte.rotulo}."
        if feedback:
            feedback.reportError(msg)
        else:
            QgsMessageLog.logMessage(msg, "GisBR", Qgis.MessageLevel.Warning)
        return None

    camadas_uf = []
    for uf, codes in grupos_uf.items():
        try:
            params = {"CODE": uf, "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT"}
            if extra_params:
                params.update(extra_params)
            res = processing.run(
                f"gisbr:{algo}", 
                params,
                feedback=feedback
            )
            layer = res.get("OUTPUT")
            if layer:
                camadas_uf.append(layer)
        except Exception as e:
            msg = f"Erro ao ler a UF {uf} para {algo}: {e}"
            if feedback:
                feedback.reportError(msg)
            else:
                QgsMessageLog.logMessage(msg, "GisBR", Qgis.MessageLevel.Warning)
            return None

    if not camadas_uf:
        msg = f"Nenhuma camada de {algo} foi retornada."
        if feedback:
            feedback.reportError(msg)
        else:
            QgsMessageLog.logMessage(msg, "GisBR", Qgis.MessageLevel.Warning)
        return None

    if len(camadas_uf) > 1:
        try:
            crs_val = camadas_uf[0].crs() if hasattr(camadas_uf[0], "crs") else None
            merge_params = {
                "LAYERS": camadas_uf,
                "OUTPUT": "memory:"
            }
            if crs_val is not None:
                merge_params["CRS"] = crs_val
            res = processing.run(
                "native:mergevectorlayers",
                merge_params,
                feedback=feedback
            )
            base_layer = res.get("OUTPUT")
        except Exception as e:
            msg = f"Erro ao mesclar camadas de UFs: {e}"
            if feedback:
                feedback.reportError(msg)
            else:
                QgsMessageLog.logMessage(msg, "GisBR", Qgis.MessageLevel.Warning)
            return None
    else:
        base_layer = camadas_uf[0]

    codes_in = ", ".join(f"'{c}'" for c in recorte.codes)
    expressao = f'"code_muni" IN ({codes_in})'

    try:
        res = processing.run(
            "native:extractbyexpression",
            {
                "INPUT": base_layer,
                "EXPRESSION": expressao,
                "OUTPUT": "memory:"
            },
            feedback=feedback
        )
        final_layer = res.get("OUTPUT")
    except Exception as e:
        msg = f"Erro ao extrair pela expressão {expressao}: {e}"
        if feedback:
            feedback.reportError(msg)
        else:
            QgsMessageLog.logMessage(msg, "GisBR", Qgis.MessageLevel.Warning)
        return None

    if not final_layer or (hasattr(final_layer, "featureCount") and final_layer.featureCount() == 0):
        msg = f"A camada extraída para {recorte.rotulo} ficou vazia silenciosamente (codes: {recorte.codes})."
        if feedback:
            feedback.reportError(msg)
        else:
            QgsMessageLog.logMessage(msg, "GisBR", Qgis.MessageLevel.Warning)
        return None

    if algo == "read_municipality" and hasattr(final_layer, "featureCount") and final_layer.featureCount() < len(recorte.codes):
        msg = f"Aviso: camada extraída para {recorte.rotulo} tem {final_layer.featureCount()} feições, mas o recorte tem {len(recorte.codes)} códigos."
        if feedback:
            feedback.pushInfo(msg)
        else:
            QgsMessageLog.logMessage(msg, "GisBR", Qgis.MessageLevel.Info)

    return final_layer
