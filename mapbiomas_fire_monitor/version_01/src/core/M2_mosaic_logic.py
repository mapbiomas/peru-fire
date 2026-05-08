"""
M2 - Processamento e Download (Lógica)
Converte shards (GCS) em COGs nacionais através do GDAL (Sequencial/Monoprocess)
"""
import os
import subprocess
import glob
import time
from datetime import timedelta

from M0_auth_config import (
    CONFIG, mosaic_name, 
    monthly_chunk_path, monthly_mosaic_path, monthly_cog_path,
    yearly_chunk_path, yearly_mosaic_path, yearly_cog_path,
    gcs_chunks_prefix, get_temp_dir, check_command_exists
)

# Mapeamento de Tipos de Dados Recomendado (IPAM/MapBiomas)
BAND_DATATYPES = {
    'blue': 'Int16', 'green': 'Int16', 'red': 'Int16', 
    'nir': 'Int16', 'swir1': 'Int16', 'swir2': 'Int16',
    'nbr': 'Int16', 'dayOfYear': 'Int16',
    'classification': 'Byte', 'burned_area': 'Byte',
    'probability': 'Float32', 'score': 'Float32'
}

def list_gcs_files(prefix, logger=None):
    """Lista shards diretamente no diretório GCS alvo."""
    import platform
    cmd = 'gsutil.cmd' if platform.system() == 'Windows' else 'gsutil'
    
    bucket_url = f"gs://{CONFIG['bucket']}"
    # Garante que o prefixo comece certo e termine com barra
    clean_prefix = prefix.replace(f"gs://{CONFIG['bucket']}/", "").strip("/")
    target_url = f"{bucket_url}/{clean_prefix}/"
    
    if logger: logger(f"Buscando shards em: {target_url}", "info")
    
    try:
        # Listagem recursiva apenas da pasta alvo
        result = subprocess.run([cmd, 'ls', '-r', target_url], capture_output=True, text=True)
        
        if result.returncode != 0:
            return []
            
        files = [l.strip() for l in result.stdout.splitlines() if l.strip().endswith('.tif')]
        return files
    except Exception as e:
        if logger: logger(f"Erro ao acessar GCS: {e}", "error")
        return []

def check_m2_dependencies():
    """Valida se utilitarios estao integrados."""
    from M0_auth_config import ensure_gdal_path
    ensure_gdal_path()
    
    deps = {
        'gsutil':  'gsutil' if os.name != 'nt' else 'gsutil.cmd',
        'gdalbuildvrt': 'gdalbuildvrt',
        'gdal_translate': 'gdal_translate'
    }
    return [name for name, cmd in deps.items() if not check_command_exists(cmd)]

def run_cmd(args, label="Comando"):
    """Envolve comando subprocess com traces mais seguros"""
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=True)
        return res
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erro em {label}: {e.stderr.strip() if e.stderr else e.stdout.strip()}")

def assemble_country_mosaic(year, month=None, period='monthly', bands=None, sensor=None, mosaic_method='minnbr', logger=None, progress_idx=0, progress_total=0, start_time=None):
    import shutil
    from M0_auth_config import GLOBAL_OPTS

    s = sensor or GLOBAL_OPTS['SENSOR']
    m_method = mosaic_method or 'minnbr'

    if period == 'monthly':
        chunk_prefix  = monthly_chunk_path(year, month, mosaic=m_method, sensor=s)
        mosaic_prefix = monthly_cog_path(year, month, mosaic=m_method, sensor=s)
        base_name = mosaic_name(year, month, 'monthly', mosaic=m_method, sensor=s)
        label = f"{year}-{month:02d}"
    else:
        chunk_prefix  = yearly_chunk_path(year, mosaic=m_method, sensor=s)
        mosaic_prefix = yearly_cog_path(year, mosaic=m_method, sensor=s)
        base_name = mosaic_name(year, period='yearly', mosaic=m_method, sensor=s)
        label = f"{year} Anual"

    missing = check_m2_dependencies()
    if missing:
        msg = f"❌ Faltam dependências vitais: {missing}"
        if logger: logger(msg, "error")
        return []

    import platform
    gsutil_cmd = 'gsutil.cmd' if platform.system() == 'Windows' else 'gsutil'

    work_root = get_temp_dir()
    session_id = f"m2_{base_name}_{int(time.time())}"
    tmp_path = os.path.join(work_root, session_id)
    os.makedirs(tmp_path, exist_ok=True)

    results = []

    try:
        # Busca direta no GCS
        gcs_files = list_gcs_files(chunk_prefix, logger=logger)
        
        if not gcs_files:
            if logger: logger(f"Nenhum shard encontrado no GCS para {label}.", "warning")
            return []
            
        found_bands = {}
        for f in gcs_files:
            fname = os.path.basename(f)
            # Match mais flexível: busca a banda cercada por separadores
            for b_name in (bands or CONFIG['bands_all']):
                # Procuramos a banda como um "token" isolado no nome do arquivo
                # Ex: _blue_ ou _blue.tif ou _blue-
                if f"_{b_name}_" in fname or f"_{b_name}." in fname:
                    if b_name not in found_bands: found_bands[b_name] = []
                    found_bands[b_name].append(f)
                    break
        
        # Log para conferência
        if logger:
            for b, f_list in found_bands.items():
                logger(f"[DEBUG] Banda {b}: {len(f_list)} shards encontrados.", "info")
        
        target_bands = bands or CONFIG['bands_all']
        bands_to_process = {b: found_bands[b] for b in target_bands if b in found_bands}
        
        if not bands_to_process:
            if logger: logger(f"Bandas alvo {target_bands} não detectadas no GCS para {base_name}.", "warning")
            return []

        current_step = progress_idx

        for b_name, remote_shards in bands_to_process.items():
            clean_b_name = "dayOfYear" if b_name.lower() == "dayofyear" else b_name
            current_step += 1
            
            if logger: logger(f"Processando [{b_name}] ({len(remote_shards)} shards)...", "info")
            
            band_tmp = os.path.join(tmp_path, b_name)
            os.makedirs(band_tmp, exist_ok=True)

            try:
                run_cmd([gsutil_cmd, '-m', 'cp'] + remote_shards + [band_tmp], label=f"Download ({b_name})")

                local_shards = glob.glob(os.path.join(band_tmp, '*.tif'))
                if not local_shards: continue

                vrt_path = os.path.join(tmp_path, f"{base_name}_{b_name}.vrt")
                run_cmd(['gdalbuildvrt', vrt_path] + local_shards, label=f"VRT ({b_name})")

                cog_remote_name = f"{mosaic_name(year, month, period, clean_b_name, sensor=s, mosaic=m_method)}_cog.tif"
                cog_local_path = os.path.join(tmp_path, cog_remote_name)
                
                dt = BAND_DATATYPES.get(clean_b_name, 'Int16')
                
                run_cmd([
                    'gdal_translate', '-of', 'COG', '-ot', dt,
                    '-co', 'COMPRESS=LZW', '-co', 'PREDICTOR=2',
                    '-co', 'NUM_THREADS=2', '-co', 'BIGTIFF=YES', vrt_path, cog_local_path
                ], label=f"Conversão COG ({clean_b_name})")

                dest = f"gs://{CONFIG['bucket']}/{mosaic_prefix}/{cog_remote_name}"
                run_cmd([gsutil_cmd, 'cp', cog_local_path, dest], label=f"Upload ({b_name})")
                
                if logger: logger(f"✅ Sucesso: {cog_remote_name}", "success")
                results.append(dest)
            finally:
                if os.path.exists(band_tmp): shutil.rmtree(band_tmp)

    finally:
        if os.path.exists(tmp_path): shutil.rmtree(tmp_path)

    return results
