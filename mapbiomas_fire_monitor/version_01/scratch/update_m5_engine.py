import os
import re

path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core\M5_classifier.py'
with open(path, 'r', encoding='utf-8') as f:
    txt = f.read()

# 1. Trocar o run_m5_queue para executar em 2 blocos
pattern = re.compile(r'def run_m5_queue\(\):.*?def _process_job', re.DOTALL)

new_run = """def run_m5_queue():
    \"\"\"
    Motor de Processamento (Fase 1: Classificacao, Fase 2: Upload GEE)
    \"\"\"
    from M5_classifier_ui import load_queue, save_queue
    from IPython.display import display, HTML, clear_output
    import ipywidgets as widgets
    
    out = widgets.Output()
    display(out)
    
    queue = load_queue()
    
    pending_jobs = [j for j in queue if j['status'] == 'PENDING' and j.get('enabled', True)]
    upload_jobs = [j for j in queue if j['status'] == 'COMPLETED' and j.get('upload_gee', False)]
    
    if not pending_jobs and not upload_jobs:
        with out: 
            clear_output()
            display(HTML("<b style='color:green;'>Exito: No hay tareas activas pendientes ni uploads configurados.</b>"))
        return
        
    # --- FASE 1: CLASIFICACION ---
    if pending_jobs:
        with out: print("--- INICIANDO FASE DE CLASIFICACION ---")
        for job in pending_jobs:
            job['status'] = 'RUNNING'
            save_queue(queue)
            
            try:
                with out:
                    print(f"\\nIniciando clasificación regional: [{job['id']}]")
                
                _process_job(job, out)
                
                job['status'] = 'COMPLETED'
                job['progress'] = '100%'
                save_queue(queue)
                
                with out:
                    print(f"Exito: Tarea {job['id']} finalizada.")
                    
            except Exception as e:
                job['status'] = 'FAILED'
                save_queue(queue)
                with out: 
                    print(f"Error Crítico en la tarea {job['id']}: {str(e)}")
                break 

    # --- FASE 2: UPLOAD GEE ---
    if upload_jobs:
        with out: print("\\n--- INICIANDO FASE DE UPLOAD AL GEE ---")
        queue = load_queue() # Recarrega caso a fase 1 tenha alterado
        for job in upload_jobs:
            try:
                with out: print(f"\\nIniciando subida al GEE: [{job['id']}]")
                _upload_job_to_gee(job, out)
                
                # Desmarca a flag para não subir novamente atoa na próxima
                job['upload_gee'] = False 
                job['progress'] = '100% (GEE)'
                save_queue(queue)
                
                with out: print(f"Exito: Tarea {job['id']} enviada como Task al GEE.")
                    
            except Exception as e:
                with out: print(f"Error al subir tarea {job['id']}: {str(e)}")

def _process_job"""

txt = pattern.sub(new_run, txt)

# 2. Add _upload_job_to_gee at the end of the file
upload_func = """

def _upload_job_to_gee(job, out):
    import ee
    from M0_auth_config import CONFIG, _get_fs
    fs = _get_fs()
    
    model_id = job['model']
    region_name = job['region']
    period = job['period']
    
    gcs_dir = f"{CONFIG['bucket']}/{CONFIG['gcs_library_classifications']}/{model_id}/{period}"
    
    # Puxa os arquivos tif gerados no GCS
    files = fs.glob(f"{gcs_dir}/*{region_name}*.tif")
    if not files:
        raise ValueError(f"No se encontraron imagenes .tif en GCS para {job['id']}.")
        
    gee_base_folder = f"{CONFIG['asset_monitor_base']}/LIBRARY_MODELS"
    gee_ic_path = f"{gee_base_folder}/{model_id}"
    
    # Criar hierarchy
    try:
        ee.data.getAsset(gee_base_folder)
    except ee.EEException:
        ee.data.createAsset({'type': 'FOLDER'}, gee_base_folder)
        
    try:
        ee.data.getAsset(gee_ic_path)
    except ee.EEException:
        ee.data.createAsset({'type': 'IMAGE_COLLECTION'}, gee_ic_path)
        
    with out: print(f"  Encontradas {len(files)} imagenes. Creando Tasks de Ingestion...")
    
    for f in files:
        filename = f.split('/')[-1]
        asset_id = f"{gee_ic_path}/{filename.replace('.tif', '')}"
        gcs_uri = f"gs://{f}"
        
        request = {
            'id': asset_id,
            'tilesets': [{'id': filename, 'sources': [{'uris': [gcs_uri]}]}],
            'properties': {
                'model': model_id,
                'region': region_name,
                'period': period
            }
        }
        
        task_id = ee.data.newTaskId()[0]
        try:
            ee.data.startIngestion(task_id, request)
        except Exception as e:
            if "already exists" in str(e).lower():
                with out: print(f"    Asset {filename} ya existe en GEE. Saltando.")
            else:
                raise e
"""

if "_upload_job_to_gee" not in txt:
    txt += upload_func

with open(path, 'w', encoding='utf-8') as f:
    f.write(txt)
print("Fases injetadas no Motor M5!")
