
import os
import json
import sys
import re

# Adiciona os caminhos de forma dinâmica baseada na localização deste arquivo
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # version_01
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'src'))
sys.path.append(os.path.join(BASE_DIR, 'src', 'core'))

# Garante saída em UTF-8 para evitar erros de charmap no console
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from M0_auth_config import CONFIG, _get_fs, mosaic_name

def migrate_gcs():
    fs = _get_fs()
    bucket = CONFIG['bucket']
    library_base = CONFIG['gcs_library_images']
    base_path = f"{bucket}/{library_base}"
    
    print(f"--- INICIANDO MIGRAÇÃO E PADRONIZAÇÃO GCS ---")
    
    try:
        all_files = fs.find(base_path)
        print(f"Total de arquivos para analisar: {len(all_files)}")
        
        move_ops = []
        bands_all = CONFIG.get('bands_all', ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'])
        sorted_bands = sorted(bands_all, key=len, reverse=True)

        for f in all_files:
            if not f.endswith('.tif') and not f.endswith('.npy') and not f.endswith('.json') and not f.endswith('.npz'):
                continue
                
            rel_path = f.replace(f"{bucket}/{library_base}/", "").replace("\\", "/")
            parts = rel_path.split('/')
            filename = parts[-1]
            
            # --- 1. IDENTIFICAÇÃO DOS METADADOS ---
            sensor = 'sentinel2' # Default para este projeto
            period = 'monthly' if 'monthly' in rel_path else 'yearly'
            mosaic = 'minnbr'
            date = None
            band = None
            is_cog = '_cog' in filename
            if '/models/' in rel_path: continue
            
            # 1.1 Identifica o Mosaico/Sensor pela pasta ou nome
            if 'minnbr_buffer' in rel_path or 'minnbr_buffer' in filename or 'sentinel2_buffer' in rel_path:
                mosaic = 'minnbr_buffer'
            
            # 1.2 Identifica a Data (Suporte a YYYY_MM e YYYY/MM)
            date_match = re.search(r'(\d{4}_\d{2})', filename)
            if not date_match:
                date_match = re.search(r'(\d{4}_\d{2})', rel_path)
            if not date_match:
                # Tenta capturar o padrão /YYYY/MM/
                path_date_match = re.search(r'/(\d{4})/(\d{2})/', rel_path)
                if path_date_match:
                    date = f"{path_date_match.group(1)}_{path_date_match.group(2)}"
            
            if not date and date_match:
                date = date_match.group(0)
            
            if not date:
                # Fallback para apenas ano
                year_match = re.search(r'(\d{4})', filename)
                if year_match: date = year_match.group(0)
            
            # 1.3 Identifica a Banda
            for b in sorted_bands:
                needle = f"_{b}"
                if needle in filename:
                    band = b
                    break
            
            if not (sensor and date): 
                continue

            # --- 2. DEFINIÇÃO DO NOVO CAMINHO ---
            year = date.split('_')[0]
            month = int(date.split('_')[1]) if '_' in date else None
            
            new_filename = filename
            if band:
                official_name = mosaic_name(year, month, period, band=band, mosaic=mosaic, sensor=sensor)
                if is_cog:
                    new_filename = f"{official_name}_cog.tif"
                elif filename.endswith('.tif'):
                    coord_match = re.search(r'(\d{10}-\d{10})', filename)
                    suffix = f"_{coord_match.group(0)}" if coord_match else ""
                    new_filename = f"{official_name}{suffix}.tif"

            subfolder = "cog" if is_cog else "chunks"
            target_rel_path = f"{library_base}/{sensor}/{period}/{mosaic}/{date}/{subfolder}/{new_filename}"
            target_full_path = f"{bucket}/{target_rel_path}"
            
            if f != target_full_path:
                move_ops.append((f, target_full_path))

        # --- 3. EXECUÇÃO ---
        print(f"Total de movimentações planejadas: {len(move_ops)}")
        
        if not move_ops:
            print("✅ Tudo já está no padrão correto!")
            return

        if "--confirm" in sys.argv:
            print(f"🚀 Executando {len(move_ops)} movimentações...")
            for i, (src, dst) in enumerate(move_ops):
                try:
                    if fs.exists(dst):
                        fs.rm(src)
                        print(f"🗑️ Já existe no destino. Deletada origem obsoleta: {src.split('/')[-1]}")
                    else:
                        fs.mv(src, dst)
                        print(f"✔ Movido: {src.split('/')[-1]} -> {dst.split('/')[-1]}")
                    
                    if i % 10 == 0: print(f"Progresso: {i}/{len(move_ops)} concluídos...")
                except KeyboardInterrupt:
                    print("\n🛑 Interrompido pelo usuário. Parando com segurança...")
                    break
                except Exception as e:
                    print(f"❌ Erro em {src}: {e}")
            print("\n✅ Processo finalizado!")
        else:
            # Amostra para validação
            print("\nAmostra de validação:")
            for src, dst in move_ops[:15]:
                print(f"DE:   {src.replace(bucket+'/', '')}")
                print(f"PARA: {dst.replace(bucket+'/', '')}\n")
            print(f"⚠️ MODO SIMULAÇÃO. Para executar: python scratch/migrate_gcs.py --confirm")

    except Exception as e:
        print(f"Erro na migração: {e}")

if __name__ == "__main__":
    migrate_gcs()
