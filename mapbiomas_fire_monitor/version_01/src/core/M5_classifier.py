import os
import json
import time
import rasterio
import numpy as np
import tensorflow as tf
from M0_auth_config import CONFIG, GLOBAL_OPTS, _get_fs, _gcs_models_base

def run_m5_queue(send=None):
    """
    Motor de Processamento (Fase 1: Classificacao, Fase 2: Upload GEE)
    """
    if send is None:
        send = ['classification', 'upload']
        
    from M5_classifier_ui import load_queue, save_queue
    from IPython.display import display, HTML, clear_output
    import ipywidgets as widgets
    
    out = widgets.Output()
    display(out)
    
    valid_commands = ['classification', 'upload']
    if not isinstance(send, list) or not any(s in valid_commands for s in send):
        with out:
            print("Atencion: Argumento 'send' invalido. Use send=['classification'], send=['upload'] o send=['classification', 'upload'].")
        return
        
    queue = load_queue()
    
    pending_jobs = [j for j in queue if j['status'] == 'PENDING' and j.get('enabled', True)]
    upload_jobs = [j for j in queue if j['status'] == 'COMPLETED' and j.get('upload_gee', False)]
    
    if not pending_jobs and not upload_jobs:
        with out: 
            clear_output()
            display(HTML("<b style='color:green;'>Exito: No hay tareas activas pendientes ni uploads configurados.</b>"))
        return
        
    # --- FASE 1: CLASIFICACION ---
    if pending_jobs and 'classification' in send:
        with out: print("--- INICIANDO FASE DE CLASIFICACION ---")
        for job in pending_jobs:
            job['status'] = 'RUNNING'
            save_queue(queue)
            
            try:
                with out:
                    print(f"Iniciando clasificación regional: [{job['id']}]")
                
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
    if upload_jobs and 'upload' in send:
        with out: print("--- INICIANDO FASE DE UPLOAD AL GEE ---")
        queue = load_queue() # Recarrega caso a fase 1 tenha alterado
        for job in upload_jobs:
            try:
                with out: print(f"Iniciando subida al GEE: [{job['id']}]")
                _upload_job_to_gee(job, out)
                
                # Desmarca a flag para não subir novamente atoa na próxima
                job['upload_gee'] = False 
                job['progress'] = '100% (GEE)'
                save_queue(queue)
                
                with out: print(f"Exito: Tarea {job['id']} enviada como Task al GEE.")
                    
            except Exception as e:
                with out: print(f"Error al subir tarea {job['id']}: {str(e)}")

def _process_job(job, out):
    import ee
    from M5_classifier_ui import load_queue, save_queue
    fs = _get_fs()
    
    model_id = job['model']
    region_name = job['region']
    period = job['period'] 
    
    # 1. Recuperar Metadatos del Modelo
    model_dir = f"{CONFIG['bucket']}/{_gcs_models_base()}/{model_id}"
    meta_path = f"{model_dir}/metadata.json"
    
    if not fs.exists(meta_path):
        raise ValueError(f"Modelo {model_id} no encontrado en GCS ({meta_path}).")
        
    with fs.open(meta_path, 'r') as f:
        meta = json.load(f)
        
    bands_config = meta.get('bands_config', {})
    if not bands_config:
        raise ValueError(f"El modelo {model_id} no tiene 'bands_config' en sus metadatos. No se puede saber qué bandas requiere.")
        
    parts = period.split('_')
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 0
    
    # 2. Determinar Celdas Geográficas (cim-world)
    with out: print(f"Extrayendo grilla de la región '{region_name}' desde GEE...")
    cells = _get_region_cells(region_name)
    if not cells:
        raise ValueError(f"No se encontraron celdas de la grilla cim-world para la región {region_name}.")
    
    total_cells = len(cells)
    with out: print(f"Se encontraron {total_cells} celdas (tiles) para procesar.")
    
    # 3. Cargar el Modelo de IA a RAM
    local_model_path = f"/tmp/{model_id}.keras"
    if not os.path.exists(local_model_path):
        with out: print(f"Descargando modelo Keras a la instancia local...")
        fs.get(f"{model_dir}/model.keras", local_model_path)
    
    with out: print("Cargando modelo en memoria (TensorFlow)...")
    model = tf.keras.models.load_model(local_model_path)
    
    # 4. Bucle de Procesamiento con Checkpoint Local
    queue = load_queue() # Recarrega para salvar progresso
    
    for i, cell in enumerate(cells):
        cell_id = cell['system:index']
        
        # Atualiza a interface da fila para o usuário saber onde parou
        if i % 5 == 0: 
            for q_job in queue:
                if q_job['id'] == job['id']:
                    q_job['progress'] = f"{i}/{total_cells} ({(i/total_cells):.1%})"
            save_queue(queue)
            
        out_gcs = f"{CONFIG['bucket']}/{CONFIG['gcs_library_classifications']}/{model_id}/{period}/regional_classification_{cell_id}_{model_id}_{region_name}_{period}.tif"
        
        # --- CHECKPOINT: Salta si ya existe ---
        if fs.exists(out_gcs):
            with out: print(f"  [{(i+1):03d}/{total_cells}] Carta {cell_id} ya procesada. Saltando.")
            continue
            
        with out: print(f"  [{(i+1):03d}/{total_cells}] Clasificando carta: {cell_id} ...")
        
        # --- INFERENCIA ---
        _classify_cell(cell_id, model, bands_config, year, month, out_gcs, fs)

def _get_region_cells(region_name):
    """
    Busca no Earth Engine os polígonos do grid cim-world que cruzam com a região.
    """
    import ee
    cim = ee.FeatureCollection("projects/mapbiomas-workspace/AUXILIAR/cim-world-1-250000")
    
    if region_name.lower() == 'peru':
        region_fc = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(ee.Filter.eq('ADM0_NAME', 'Peru'))
    else:
        # Usa o asset de regiões configurado e filtra pela coluna name
        region_fc = ee.FeatureCollection(CONFIG['asset_regions']).filter(ee.Filter.eq('region_nam', region_name))
        
    intersected = cim.filterBounds(region_fc.geometry())
    
    # Coleta a lista de identificadores das cartas (ex: NA-1-V-A)
    try:
        ids = intersected.aggregate_array('system:index').getInfo()
        return [{'system:index': str(i)} for i in ids]
    except Exception as e:
        print(f"Erro ao buscar grilla no GEE: {e}")
        return []

def _classify_cell(cell_id, model, bands_config, year, month, out_gcs_path, fs):
    """
    Função de inferência isolada por carta.
    """
    # 1. Montar os paths dinamicamente baseados nas bandas exigidas pelo modelo
    # (A lógica de /vsigs/ rasterio entra aqui para empilhar os arrays Numpy das bandas da carta)
    
    # ... LÓGICA DE EXTRAÇÃO E INFERÊNCIA RASTERIO AQUI ...
    
    # [SIMULAÇÃO] Tempo de processamento raster
    time.sleep(1.5) 
    
    # [SIMULAÇÃO] Salvar o TIFF
    local_tmp = f"/tmp/regional_{cell_id}.tif"
    with open(local_tmp, 'w') as f: 
        f.write("Simulated Classified GeoTIFF")
    
    # Fazer upload para o GCS e limpar lixo local
    fs.put(local_tmp, out_gcs_path)
    os.remove(local_tmp)
