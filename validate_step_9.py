# -*- coding: utf-8 -*-
"""Script de validação para a Etapa 9 do PLAN.md.

Inicializa o PyQGIS standalone, registra o provedor GisBR, configura um
cache local para OSM, altera a URL do Overpass para um endpoint inválido
para simular falha de rede, e roda a rotina de diagnóstico (eixo Transportes).
"""
import os
import sys
import json
import shutil
from pathlib import Path

# Configuração do caminho do PyQGIS e do plugin
sys.path.insert(0, '/home/diego/projects')
sys.path.append('/usr/share/qgis/python/plugins')

from qgis.core import QgsApplication, QgsProcessingFeedback, QgsProject

def run_validation():
    print("=== Iniciando Validação da Etapa 9 ===")
    
    # 1. Inicializa o QGIS e Processing
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    import processing
    from processing.core.Processing import Processing as ProcInit
    ProcInit.initialize()
    
    # 2. Registra o provedor gisbr
    from gisbr.provider import GeobrProvider
    provider = GeobrProvider()
    QgsApplication.processingRegistry().addProvider(provider)
    print("Provedor GisBR registrado com sucesso no QGIS Processing.")
    
    # 3. Define caminhos temporários de teste
    code_muni = "3106200"
    nome_muni = "Belo Horizonte"
    test_dir = Path("/home/diego/projects/gisbr/test_validation_tmp")
    test_dir.mkdir(exist_ok=True)
    gpkg_path = str(test_dir / "test_diagnostico.gpkg")
    cache_path = test_dir / "osm_overpass_3106200.json"
    
    # Payload válido do cache simulado (algumas vias e nós para Belo Horizonte)
    mock_payload = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": -19.92,
                "lon": -43.94
            },
            {
                "type": "node",
                "id": 2,
                "lat": -19.93,
                "lon": -43.93
            },
            {
                "type": "way",
                "id": 10,
                "nodes": [1, 2],
                "tags": {
                    "highway": "residential",
                    "name": "Rua de Teste do Cache"
                }
            }
        ]
    }
    
    # Escreve o cache em disco
    cache_path.write_text(json.dumps(mock_payload), encoding="utf-8")
    print(f"Cache simulado criado em: {cache_path}")
    
    # 4. Modifica a URL do Overpass para um endpoint inválido simulando falha de rede
    from gisbr.core.connectors import osm
    original_url = osm._OVERPASS_URL
    osm._OVERPASS_URL = "https://invalid-overpass-api-subdomain-12345.org/api/interpreter"
    print(f"URL do Overpass alterada de {original_url} para {osm._OVERPASS_URL} (simulação de falha).")
    
    # 5. Configura o feedback para capturar os logs
    class TestFeedback(QgsProcessingFeedback):
        def __init__(self):
            super().__init__()
            self.logs = []
            
        def pushInfo(self, info):
            print(f"[QGIS LOG] {info}")
            self.logs.append(info)
            
        def reportError(self, error, fatal=False):
            print(f"[QGIS ERROR] {error}")
            self.logs.append(error)
            
    feedback = TestFeedback()
    
    # BBox simplificado de BH
    bbox = [-44.05, -20.05, -43.85, -19.85]
    
    # 6. Executa a rotina carregar_fontes com a fonte 'osm_vias' (Transportes) e force=True
    # force=True força a tentativa de download pela rede, garantindo que o fallback seja exercitado
    print("\nExecutando carregar_fontes para o eixo de transportes (OSM) com force=True...")
    try:
        res = gisbr.core.diagnostico.carregar_fontes(
            source_ids=["osm_vias"],
            code_muni=code_muni,
            nome_muni=nome_muni,
            bbox=bbox,
            gpkg_path=gpkg_path,
            add_basemap=False,
            force=True,
            feedback=feedback
        )
        
        print("\n=== Resultado do Diagnóstico ===")
        print("Retorno:", res)
        
        # Validações
        assert "osm_vias" in res["ok"], "Erro: A fonte osm_vias deveria ter concluído com sucesso (usando o cache)"
        assert len(res["falhou"]) == 0, f"Erro: Houve falhas no processamento: {res['falhou']}"
        
        # Verifica se o log de fallback do cache foi registrado
        fallback_logged = any("Aviso: Falha na consulta do Overpass. Usando cache local" in log for log in feedback.logs)
        assert fallback_logged, "Erro: O aviso de fallback no cache não foi registrado no log de feedback."
        print("\n✅ Sucesso: O aviso de fallback no cache foi corretamente emitido!")
        
        # Verifica se as camadas de links e nós foram adicionadas ao GeoPackage
        from qgis.core import QgsVectorLayer
        gpkg_links = QgsVectorLayer(f"{gpkg_path}|layername=osm_links_{code_muni}", "links", "ogr")
        gpkg_nodes = QgsVectorLayer(f"{gpkg_path}|layername=osm_nodes_{code_muni}", "nodes", "ogr")
        
        assert gpkg_links.isValid(), "Erro: Camada osm_links não foi gravada/não é válida no GeoPackage."
        assert gpkg_nodes.isValid(), "Erro: Camada osm_nodes não foi gravada/não é válida no GeoPackage."
        
        print(f"✅ Sucesso: Camadas criadas com sucesso no GeoPackage!")
        print(f"   osm_links count: {gpkg_links.featureCount()}")
        print(f"   osm_nodes count: {gpkg_nodes.featureCount()}")
        
        print("\n🎉 VALIDAÇÃO DA ETAPA 9 CONCLUÍDA COM SUCESSO!")
        
    finally:
        # Restaura a URL original
        osm._OVERPASS_URL = original_url
        
        # Limpa os arquivos temporários criados
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("\nDiretório temporário de testes removido.")
            
        qgs.exitQgis()

if __name__ == "__main__":
    run_validation()
