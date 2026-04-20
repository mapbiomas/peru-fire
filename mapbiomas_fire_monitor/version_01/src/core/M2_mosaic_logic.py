"""
M2 - Processamento e Download (Lógica)
Converte shards (GCS) em COGs nacionais através do GDAL (Sequencial/Monoprocess)
"""
import os
import subprocess
import glob
import time

from M0_auth_config import CONFIG, mosaic_name, monthly_chunk_path, monthly_mosaic_path, yearly_chunk_path, yearly_mosaic_path, gcs_chunks_prefix, get_temp_dir, check_command_exists

_GCS_CACHE = None

# Mapeamento de Tipos de Dados Recomendado (IPAM/MapBiomas)
BAND_DATATYPES = {
    'blue': 'Int16', 'green': 'Int16', 'red': 'Int16', 
    'nir': 'Int16', 'swir1': 'Int16', 'swir2': 'Int16',
    'nbr': 'Int16', 'dayOfYear': 'Int16',
    'classification': 'Byte', 'burned_area': 'Byte',
    'probability': 'Float32', 'score': 'Float32'
}

def fetch_all_gcs_files(force=False, logger=None):
    """Lista arquivos GCS dos prefixos otimizado sem listagem global pesada."""
    global _GCS_CACHE
    if _GCS_CACHE is not None and not force:
        return _GCS_CACHE

    import platform
    cmd = 'gsutil.cmd' if platform.system() == 'Windows' else 'gsutil'

    if logger: logger("Conectando ao GCS e listando chunks...", "info")

    try:
        all_files = []
        prefixes = [gcs_chunks_prefix('monthly'), gcs_chunks_prefix('yearly')]
        
        for prefix in prefixes:
            result = subprocess.run([cmd, 'ls', f"gs://{CONFIG['bucket']}/{prefix}/"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.splitlines() if l.strip().endswith('.tif')]
                all_files.extend(lines)
        
        _GCS_CACHE = all_files
        if logger: logger(f"Cache GCS carregado com {len(_GCS_CACHE)} chunks.", "success")
        return _GCS_CACHE
    except Exception as e:
        if logger: logger(f"Erro no GCS: {e}", "error")
        return []

def list_gcs_files(prefix):
    """Filtra shards na lista indexada baseada em sub-prefixo alvo."""
    all_files = fetch_all_gcs_files()
    target_prefix = f"gs://{CONFIG['bucket']}/{prefix}"
    return [f for f in all_files if f.startswith(target_prefix)]

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

def assemble_country_mosaic(year, month=None, period='monthly', bands=None, logger=None):
    import shutil

    if period == 'monthly':
        chunk_prefix  = monthly_chunk_path(year, month)
        # Fix: M2 saves to cogs exactly like the repository dictates
        mosaic_prefix = monthly_chunk_path(year, month).replace('chunks', 'cog')
        base_name = mosaic_name(year, month, 'monthly')
        label = f"{year}-{month:02d}"
    else:
        chunk_prefix  = yearly_chunk_path(year)
        mosaic_prefix = yearly_chunk_path(year).replace('chunks', 'cog')
        base_name = mosaic_name(year, period='yearly')
        label = f"{year} Anual"

    missing = check_m2_dependencies()
    if missing:
        msg = f"Faltam dependências vitais: {missing}. "
        if 'gdalbuildvrt' in missing or 'gdal_translate' in missing:
            msg += "\n💡 No Colab, execute: !apt-get install -y gdal-bin\n💡 No Windows, instale GDAL via OSGeo4W ou Conda."
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
        if logger: logger(f"Buscando chunks GCS para {base_name}", "info")
        ls_res = subprocess.run([gsutil_cmd, 'ls', f"gs://{CONFIG['bucket']}/{chunk_prefix}/*.tif"], capture_output=True, text=True)
        all_remote_files = [line.strip() for line in ls_res.stdout.splitlines() if line.strip()]
        
        target_bands = bands or CONFIG['bands_all']
        band_files = {}
        
        for f in all_remote_files:
            fname = os.path.basename(f)
            for b_name in target_bands:
                if fname.startswith(f"{base_name}_{b_name}"):
                    if b_name not in band_files: band_files[b_name] = []
                    band_files[b_name].append(f)
                    break

        if not band_files:
            if logger: logger("Bandas alvo não detectadas no GCS.", "warning")
            return []

        for b_name, remote_shards in band_files.items():
            if logger: logger(f"Processando [{b_name}] ({len(remote_shards)} shards)", "info")
            band_tmp = os.path.join(tmp_path, b_name)
            os.makedirs(band_tmp, exist_ok=True)

            try:
                run_cmd([gsutil_cmd, '-m', 'cp'] + remote_shards + [band_tmp], label=f"Download ({b_name})")

                local_shards = glob.glob(os.path.join(band_tmp, '*.tif'))
                if not local_shards: continue

                vrt_path = os.path.join(tmp_path, f"{base_name}_{b_name}.vrt")
                run_cmd(['gdalbuildvrt', vrt_path] + local_shards, label=f"VRT ({b_name})")

                cog_remote_name = f"{base_name}_{b_name}_cog.tif"
                cog_local_path = os.path.join(tmp_path, cog_remote_name)
                
                # Determinar tipo de dado (ot)
                dt = BAND_DATATYPES.get(b_name, 'Float32')
                
                run_cmd([
                    'gdal_translate', '-of', 'COG', '-ot', dt,
                    '-co', 'COMPRESS=LZW', '-co', 'PREDICTOR=2',
                    '-co', 'NUM_THREADS=2', '-co', 'BIGTIFF=YES', vrt_path, cog_local_path
                ], label=f"Conversão COG ({b_name})")

                dest = f"gs://{CONFIG['bucket']}/{mosaic_prefix}/{cog_remote_name}"
                run_cmd([gsutil_cmd, 'cp', cog_local_path, dest], label=f"Upload ({b_name})")
                
                check_ls = subprocess.run([gsutil_cmd, 'ls', dest], capture_output=True)
                if check_ls.returncode == 0:
                    if logger: logger(f"Sucesso exportado: {cog_remote_name}", "success")
                    results.append(dest)
                else:
                    if logger: logger(f"Falha salvando {dest}", "error")
            finally:
                # Limpeza severa imediata por banda para evitar oclusão de disco em Windows
                try:
                    shutil.rmtree(band_tmp)
                except: pass

    finally:
        try:
            shutil.rmtree(tmp_path)
        except: pass

    return results

def delete_cogs(year, month=None, period='monthly', bands=None, logger=None):
    """Remove os COGs selecionados do GCS."""
    import platform
    gsutil_cmd = 'gsutil.cmd' if platform.system() == 'Windows' else 'gsutil'
    
    if period == 'monthly':
        mosaic_prefix = monthly_chunk_path(year, month).replace('chunks', 'cog')
        base_name = mosaic_name(year, month, 'monthly')
    else:
        mosaic_prefix = yearly_chunk_path(year).replace('chunks', 'cog')
        base_name = mosaic_name(year, period='yearly')

    target_bands = bands or CONFIG['bands_all']
    deleted = []

    for b in target_bands:
        cog_remote_name = f"{base_name}_{b}_cog.tif"
        dest = f"gs://{CONFIG['bucket']}/{mosaic_prefix}/{cog_remote_name}"
        
        try:
            if logger: logger(f"Removendo {cog_remote_name}...", "warning")
            subprocess.run([gsutil_cmd, 'rm', dest], check=True, capture_output=True)
            deleted.append(dest)
        except Exception as e:
            if logger: logger(f"Falha ao remover {cog_remote_name}: {e}", "error")
            
    return deleted
