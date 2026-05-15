"""
m4_local_server.py
------------------
Inicia o M4 Auditor Dashboard como um servidor local usando Voila ou
Jupyter Notebook, sem depender do ambiente Colab.

Uso:
    python m4_local_server.py

Requisitos:
    pip install voila jupyter ipywidgets
"""

import os
import sys
import subprocess

# Garante que o diretório src/core está no path
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
os.chdir(CORE_DIR)

NOTEBOOK_PATH = os.path.abspath(
    os.path.join(CORE_DIR, "..", "..", "notebooks", "m4_standalone.ipynb")
)


def create_standalone_notebook():
    """Cria um notebook mínimo para o M4, se não existir."""
    import json

    nb = {
        "nbformat": 4,
        "nbformat_minor": 4,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}
        },
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import sys, os\n",
                    f"sys.path.insert(0, r'{CORE_DIR}')\n",
                    f"os.chdir(r'{CORE_DIR}')\n",
                    "\n",
                    "from M4_model_trainer import run_ui\n",
                    "ui_trainer = run_ui()",
                ],
            }
        ],
    }
    os.makedirs(os.path.dirname(NOTEBOOK_PATH), exist_ok=True)
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print(f"Notebook criado em: {NOTEBOOK_PATH}")


def run_voila():
    """Inicia com Voila (UI limpa sem células visíveis)."""
    import shutil
    voila_path = shutil.which("voila")
    cmd = [voila_path] if voila_path else [sys.executable, "-m", "voila"]
    try:
        result = subprocess.run(cmd + ["--version"], capture_output=True, timeout=10)
        print(f"\n Iniciando M4 com Voila em http://localhost:8866 ...")
        print(" Pressione Ctrl+C para parar.\n")
        subprocess.run(cmd + [NOTEBOOK_PATH, "--port=8866"])
    except Exception as e:
        print(f"Voila falhou ({e}). Tentando Jupyter...")
        run_jupyter()


def run_jupyter():
    """Fallback: abre o notebook no Jupyter Lab."""
    import shutil
    jlab_path = shutil.which("jupyter-lab") or shutil.which("jupyter")
    cmd = [jlab_path] if jlab_path else [sys.executable, "-m", "jupyterlab"]
    print(f"\n Iniciando Jupyter Lab em http://localhost:8888 ...")
    print(" Pressione Ctrl+C para parar.\n")
    nb_dir = os.path.dirname(NOTEBOOK_PATH)
    nb_file = os.path.basename(NOTEBOOK_PATH)
    try:
        subprocess.run(cmd + [f"--notebook-dir={nb_dir}", "--port=8888"])
    except Exception:
        # Last resort: python -m jupyterlab
        subprocess.run([sys.executable, "-m", "jupyterlab",
                        f"--notebook-dir={nb_dir}", "--port=8888"])


if __name__ == "__main__":
    if not os.path.exists(NOTEBOOK_PATH):
        print("Notebook standalone nao encontrado. Criando...")
        create_standalone_notebook()

    print("=" * 55)
    print("  M4 Auditor Dashboard - Servidor Local")
    print("=" * 55)
    run_voila()
