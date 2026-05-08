import json
import os

notebook_path = r"c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\notebooks\mapbiomas_fire_sentinel_peru.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Nova célula de Setup Automático
new_setup_md = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## ⚙️ [M0] — Setup Automático do Ambiente\n",
        "Esta célula autodetecta o ambiente (Colab ou Local), instala dependências, configura caminhos e realiza a autenticação."
    ]
}

new_setup_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# M0 — SETUP MESTRE (Auto-Detecção Local/Colab)\n",
        "import sys, os, subprocess\n",
        "\n",
        "def setup_environment():\n",
        "    is_colab = 'google.colab' in sys.modules\n",
        "    print(f\"🌍 Ambiente Detectado: {'Google Colab' if is_colab else 'Local (PC)'}\")\n",
        "\n",
        "    if is_colab:\n",
        "        # 1. Clonagem e Navegação no Colab\n",
        "        if not os.path.exists(\"fire_monitor\"):\n",
        "            print(\"📥 Clonando repositório...\")\n",
        "            subprocess.run([\"git\", \"clone\", \"https://github.com/mapbiomas/peru-fire.git\", \"fire_monitor\"])\n",
        "        \n",
        "        repo_path = \"/content/fire_monitor/mapbiomas_fire_monitor/version_01/src/core\"\n",
        "        if repo_path not in sys.path: sys.path.insert(0, repo_path)\n",
        "        os.chdir(repo_path)\n",
        "        \n",
        "        # 2. Instalação de Dependências no Colab\n",
        "        print(\"📦 Instalando dependências (GDAL, GCSFS, Rasterio)...\")\n",
        "        # subprocess.run([\"apt-get\", \"update\", \"-qq\"])\n",
        "        # subprocess.run([\"apt-get\", \"install\", \"-y\", \"-qq\", \"gdal-bin\", \"python3-gdal\"])\n",
        "        # subprocess.run([\"pip\", \"install\", \"-q\", \"earthengine-api\", \"gcsfs\", \"rasterio\", \"scipy\", \"tqdm\"])\n",
        "        print(\"Nota: Rodar comandos !apt e !pip manualmente no Colab se necessário.\")\n",
        "    else:\n",
        "        # 3. Setup Local\n",
        "        possible_paths = [\n",
        "            os.path.abspath(\".\"),             \n",
        "            os.path.abspath(\"../src/core\"),\n",
        "            os.path.abspath(\"../../src/core\")\n",
        "        ]\n",
        "        for p in possible_paths:\n",
        "            if os.path.exists(os.path.join(p, \"M0_auth_config.py\")):\n",
        "                if p not in sys.path: sys.path.insert(0, p)\n",
        "                print(f\"✅ Path localizado: {p}\")\n",
        "                break\n",
        "\n",
        "    # 4. Inicialização do Monitor\n",
        "    try:\n",
        "        from M0_auth_config import set_country, authenticate, set_global_opts, print_config\n",
        "        \n",
        "        COUNTRY = \"peru\"\n",
        "        set_country(COUNTRY)\n",
        "        set_global_opts(\n",
        "            sensor='sentinel2', \n",
        "            periodicity='monthly', \n",
        "            personal_task_flag='MONITOR', \n",
        "            clean_cache=False\n",
        "        )\n",
        "        \n",
        "        authenticate() \n",
        "        print_config()\n",
        "        print(\"\\n🚀 Sistema pronto para uso!\")\n",
        "    except ImportError:\n",
        "        print(\"❌ Erro: Módulo M0_auth_config não encontrado no sys.path.\")\n",
        "\n",
        "setup_environment()"
    ]
}

# Encontrar as células de M0 (índices 102 a 230 no original)
# Vamos substituir todas as células entre "# ## ⚙️ [M0]" e a próxima seção M1
start_idx = -1
end_idx = -1

for i, cell in enumerate(nb['cells']):
    source = "".join(cell.get('source', []))
    if "## ⚙️ [M0]" in source:
        start_idx = i
    if "## [M1]" in source:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    # Remove as células antigas e insere as novas
    new_cells = nb['cells'][:start_idx] + [new_setup_md, new_setup_code] + nb['cells'][end_idx:]
    nb['cells'] = new_cells
    
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print(f"✅ Notebook atualizado: {start_idx} -> {end_idx}")
else:
    print("❌ Marcadores M0/M1 não encontrados.")
