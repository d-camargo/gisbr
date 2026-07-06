# -*- coding: utf-8 -*-
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Mock QGIS and PyQt modules to allow importing core.connectors.osm outside QGIS
sys.modules['qgis'] = MagicMock()
sys.modules['qgis.core'] = MagicMock()
sys.modules['qgis.PyQt'] = MagicMock()
sys.modules['qgis.PyQt.QtCore'] = MagicMock()
sys.modules['qgis.PyQt.QtNetwork'] = MagicMock()

import core.connectors.osm as osm

class MockFeedback:
    def __init__(self):
        self.messages = []

    def pushInfo(self, msg):
        self.messages.append(msg)

def run_tests():
    print("Iniciando testes locais para o parsing de erro do Overpass...")
    
    bbox = [-43.95, -19.95, -43.90, -19.90] # Exemplo de BBox
    
    # -------------------------------------------------------------
    # (a) Teste com bytes vazios (sem cache)
    # -------------------------------------------------------------
    print("\nExecutando: Teste (a) - Bytes vazios sem cache")
    with patch('core.connectors.osm._post_overpass') as mock_post:
        mock_post.return_value = b""
        
        try:
            osm.fetch_overpass_json(bbox, timeout=60)
            print("❌ ERRO: Deveria ter levantado OverpassError para bytes vazios.")
            sys.exit(1)
        except osm.OverpassError as e:
            print("✅ Sucesso: OverpassError levantado.")
            print("Mensagem do erro:", e)
            assert "Erro ao decodificar JSON" in str(e), "Mensagem incorreta para JSON vazio"
            
    # -------------------------------------------------------------
    # (b) Teste com HTML de erro (sem cache)
    # -------------------------------------------------------------
    print("\nExecutando: Teste (b) - HTML de erro sem cache")
    with patch('core.connectors.osm._post_overpass') as mock_post:
        html_error = b"<html>Too Many Requests</html>"
        mock_post.return_value = html_error
        
        try:
            osm.fetch_overpass_json(bbox, timeout=60)
            print("❌ ERRO: Deveria ter levantado OverpassError para HTML de erro.")
            sys.exit(1)
        except osm.OverpassError as e:
            print("✅ Sucesso: OverpassError levantado.")
            print("Mensagem do erro:", e)
            assert "Too Many Requests" in str(e), "Mensagem deve conter o snippet do HTML"
            
    # -------------------------------------------------------------
    # (c) Teste com cache_path válido presente
    # -------------------------------------------------------------
    print("\nExecutando: Teste (c) - Com cache válido (recuperação de erro)")
    
    cache_path = Path("/home/diego/projects/gisbr/test_cache_temp.json")
    expected_payload = {"type": "FeatureCollection", "features": [{"id": 1}]}
    
    # Salva o payload esperado no arquivo de cache
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(expected_payload, f)
        
    feedback = MockFeedback()
    
    try:
        # Mock para falhar (retorna HTML de erro que causa OverpassError)
        with patch('core.connectors.osm._post_overpass') as mock_post:
            mock_post.return_value = b"<html>Service Unavailable</html>"
            
            result = osm.fetch_overpass_json(bbox, timeout=60, cache_path=str(cache_path), feedback=feedback)
            
            # Garante que o retorno é igual ao payload do cache
            assert result == expected_payload, "Resultado retornado difere do payload do cache"
            print("✅ Sucesso: Retornou o payload correto do cache.")
            
            # Garante que a mensagem de feedback foi registrada
            assert len(feedback.messages) == 1, "Feedback de log não registrado"
            print("Mensagem de feedback registrada:", feedback.messages[0])
            assert "Usando cache local" in feedback.messages[0], "Mensagem de aviso incompleta"
            print("✅ Sucesso: Mensagem de aviso registrada no feedback.")
            
    finally:
        # Limpa o arquivo de cache temporário
        if cache_path.exists():
            cache_path.unlink()
            
    print("\n🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")

if __name__ == "__main__":
    run_tests()
