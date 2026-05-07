"""
🚀 MAPBIOMAS FIRE MONITOR — MASTER WORKFLOW SCRIPT
Este script é o 'irmão' executável do PSEUDO_NOTEBOOK_REFERENCE.md.
Ele permite rodar o pipeline completo (M0-M7) de forma sequencial ou modular.
"""

import os
import sys

# ─── [M0] CONFIGURAÇÃO DE AMBIENTE ───────────────────────────────────────────
def setup_environment():
    """Garante que o Python encontre os módulos na pasta src/core"""
    # Procura a pasta src/core a partir da raiz do projeto
    possible_paths = [
        os.path.abspath("./src/core"),
        os.path.abspath("../src/core"),
        os.path.join(os.path.dirname(__file__), "src", "core") if "__file__" in locals() else "."
    ]
    
    for p in possible_paths:
        if os.path.exists(os.path.join(p, "M0_auth_config.py")):
            if p not in sys.path:
                sys.path.insert(0, p)
            return p
    return None

found_path = setup_environment()
if not found_path:
    print("❌ ERRO: Não foi possível localizar a pasta src/core.")
    sys.exit(1)

from M0_auth_config import set_country, authenticate, set_global_opts, print_config

# --- Inicialização ---
COUNTRY = "peru"
set_country(COUNTRY)
set_global_opts(
    sensor='sentinel2', 
    periodicity='monthly', 
    personal_task_flag='MONITOR', 
    clean_cache=False
)
authenticate()
print_config()


# ─── [M1] EXPORTAÇÃO (GEE -> GCS) ────────────────────────────────────────────
def step_m1_export(years=[2025]):
    print("\n--- [M1] Despachando Exportações ---")
    from M1_export_ui import run_ui
    # Nota: Em scripts automáticos, você pode chamar a lógica diretamente
    # ui = run_ui(years=years)
    print("Dica: Use a interface M1 no Jupyter para selecionar meses específicos.")


# ─── [M2] MOSAICO (GCS -> COG) ───────────────────────────────────────────────
def step_m2_mosaic(years=[2025]):
    print("\n--- [M2] Montagem de Mosaicos COG ---")
    from M2_mosaic_ui import run_ui
    # ui = run_ui(years=years)


# ─── [M3] AMOSTRAS (TOOLKIT) ────────────────────────────────────────────────
def step_m3_samples():
    print("\n--- [M3] Gateway de Amostras ---")
    from M3_toolkit_ui import show_toolkit_links
    # show_toolkit_links()


# ─── [M4] TREINAMENTO (DNN) ─────────────────────────────────────────────────
def step_m4_train():
    print("\n--- [M4] Treinamento de Rede Neural ---")
    from M4_model_trainer import run_ui
    # run_ui()


# ─── [M5] CLASSIFICAÇÃO ─────────────────────────────────────────────────────
def step_m5_classify():
    print("\n--- [M5] Classificação Regional ---")
    # from M5_classify_logic import ...


# ─── [M7] VERSIONAMENTO ──────────────────────────────────────────────────────
def step_m7_versioner():
    print("\n--- [M7] Publicação PRE-OFICIAL ---")
    # from M7_versioner_logic import ...


# ─── EXECUÇÃO PRINCIPAL ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚦 Iniciando Master Workflow...")
    
    # Exemplo de execução modular:
    # step_m1_export(years=[2025])
    # step_m2_mosaic(years=[2025])
    
    print("\n✅ Script Master carregado. Edite este arquivo para habilitar os passos desejados.")
