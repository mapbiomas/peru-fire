
import os
import json
import sys

# Adiciona o caminho do projeto ao sys.path para importar os módulos core
sys.path.append(os.path.abspath(os.path.join(os.getcwd())))
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'src')))
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'src', 'core')))

from M0_auth_config import CONFIG, _get_fs, _gcs_library_base

def audit_gcs():
    fs = _get_fs()
    bucket = CONFIG['bucket']
    # Escaneia a raiz de todas as imagens, não apenas do sensor atual
    base_path = f"{bucket}/{CONFIG['gcs_library_images']}"
    
    print(f"--- AUDITORIA GCS ---")
    print(f"Base: gs://{base_path}")
    
    try:
        all_files = fs.find(base_path)
        print(f"Total de arquivos encontrados: {len(all_files)}")
        
        structure = {}
        for f in all_files:
            # Remove o bucket do path para facilitar a leitura
            rel_path = f.replace(f"{bucket}/", "")
            parts = rel_path.split('/')
            
            folder = "/".join(parts[:-1])
            filename = parts[-1]
            
            if folder not in structure:
                structure[folder] = {
                    "count": 0,
                    "samples": []
                }
            
            structure[folder]["count"] += 1
            if len(structure[folder]["samples"]) < 3:
                structure[folder]["samples"].append(filename)
        
        # Salva o resultado em um JSON para análise
        with open("gcs_audit_report.json", "w") as f:
            json.dump(structure, f, indent=2)
            
        print(f"Relatório gerado: gcs_audit_report.json")
        
        # Exibe um resumo no console
        print("\nResumo de Pastas Encontradas:")
        for folder, info in sorted(structure.items()):
            print(f"- {folder} ({info['count']} arquivos)")
            for s in info['samples']:
                print(f"    - {s}")

    except Exception as e:
        print(f"Erro na auditoria: {e}")

if __name__ == "__main__":
    audit_gcs()
