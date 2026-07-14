# -*- coding: utf-8 -*-
"""Script de validação para o passo 9 do plano (Validação manual/automatizada em QGIS).

Apaga o cache local para forçar o download real do metadado,
e executa catalog.available_years("municipality") no PyQGIS standalone
para confirmar que os metadados são carregados e parseados sem erros.
"""
import os
import sys
import shutil
from pathlib import Path

sys.path.insert(0, '/home/diego/projects')
sys.path.append('/usr/share/qgis/python/plugins')

from qgis.core import QgsApplication, QgsProcessingFeedback

def run_validation():
    print("=== Iniciando Validação do Passo 9 ===")
    
    # 1. Apaga/renomeia o cache local
    # No Linux, resolvido por ~/.cache/geobr-qgis/
    cache_path = Path(os.path.expanduser("~/.cache/geobr-qgis"))
    if cache_path.exists():
        backup_path = Path(os.path.expanduser("~/.cache/geobr-qgis-backup-step9"))
        if backup_path.exists():
            shutil.rmtree(backup_path)
        cache_path.rename(backup_path)
        print(f"Cache local existente movido para: {backup_path}")
    else:
        backup_path = None
    
    # 2. Inicializa o QGIS standalone
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    try:
        from gisbr.core import catalog
        print("Executando download e parse real do metadado...")
        
        feedback = QgsProcessingFeedback()
        years = catalog.available_years("municipality", feedback=feedback)
        
        print("✅ Sucesso! Anos disponíveis encontrados:", years)
        assert len(years) > 0, "A lista de anos retornada está vazia."
        
        print("\n🎉 VALIDAÇÃO DO PASSO 9 CONCLUÍDA COM SUCESSO!")
        
    except Exception as e:
        import traceback
        print("❌ FALHA na validação do passo 9:")
        traceback.print_exc()
        raise e
    finally:
        qgs.exitQgis()
        
        # Restaura o cache original se houver backup
        if backup_path and backup_path.exists():
            if cache_path.exists():
                if cache_path.is_dir():
                    shutil.rmtree(cache_path)
                else:
                    cache_path.unlink()
            backup_path.rename(cache_path)
            print("Cache local original restaurado.")

if __name__ == "__main__":
    run_validation()
