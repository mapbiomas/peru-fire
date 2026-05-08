import sys
import os

# Adiciona o path do core
core_path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core'
sys.path.insert(0, core_path)

print("--- INICIANDO TESTE M4 ---")
try:
    print("Importando...")
    from M4_model_trainer import ModelTrainerUI
    print("Instanciando...")
    ui = ModelTrainerUI()
    print("Sucesso!")
except Exception as e:
    print("\n❌ ERRO DETECTADO:")
    print(str(e))
    import traceback
    traceback.print_exc()
