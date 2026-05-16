import os

path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core\M5_classifier_ui.py'
with open(path, 'r', encoding='utf-8') as f:
    txt = f.read()

# 1. Correção Visual dos Checkboxes
old_chk_pend = "chk = widgets.Checkbox(value=job.get('enabled', True), description=job['id'], layout=widgets.Layout(width='350px'))"
new_chk_pend = "chk = widgets.Checkbox(value=job.get('enabled', True), description=job['id'], style={'description_width': 'initial'}, layout=widgets.Layout(width='auto', max_width='100%'))"
txt = txt.replace(old_chk_pend, new_chk_pend)

old_chk_comp = "chk_gee = widgets.Checkbox(value=job.get('upload_gee', False), description=f\"{job['region']} | {job['period']}\", layout=widgets.Layout(width='300px'))"
new_chk_comp = "chk_gee = widgets.Checkbox(value=job.get('upload_gee', False), description=f\"{job['region']} | {job['period']}\", style={'description_width': 'initial'}, layout=widgets.Layout(width='auto', max_width='100%'))"
txt = txt.replace(old_chk_comp, new_chk_comp)

# 2. Bloqueio GCS em _on_add_click
old_add = """        added = 0
        for r in regions:
            for period in periods:
                job_id = f"{model} | {r} | {period}"
                
                # Check if already in queue
                if any(job['id'] == job_id for job in self.queue):
                    continue
                    
                self.queue.append({
                    'id': job_id,"""

new_add = """        added = 0
        skipped = 0
        
        try:
            from M0_auth_config import CONFIG, _get_fs
            fs = _get_fs()
        except Exception:
            fs = None
            
        for r in regions:
            for period in periods:
                job_id = f"{model} | {r} | {period}"
                
                # Check if already in queue
                if any(job['id'] == job_id for job in self.queue):
                    skipped += 1
                    continue
                    
                # Check if already processed in GCS
                if fs is not None:
                    gcs_dir = f"{CONFIG['bucket']}/{CONFIG['gcs_library_classifications']}/{model}/{period}"
                    # Se achar arquivos para essa região, considera bloqueado
                    try:
                        if len(fs.glob(f"{gcs_dir}/*{r}*.tif")) > 0:
                            skipped += 1
                            continue
                    except:
                        pass
                    
                self.queue.append({
                    'id': job_id,"""
txt = txt.replace(old_add, new_add)

old_add_msg = """        with self.out_msg:
            clear_output()
            if added > 0:
                display(HTML(f"<b style='color:green;'>Exito: {added} tareas añadidas a la cola exitosamente.</b>"))
            else:
                display(HTML(f"<b style='color:orange;'>Atencion: Las combinaciones seleccionadas ya estaban en la cola.</b>"))"""

new_add_msg = """        with self.out_msg:
            clear_output()
            if added > 0:
                msg = f"<b style='color:green;'>Exito: {added} tareas añadidas a la cola.</b>"
                if skipped > 0:
                    msg += f"<br><span style='color:orange;'>Atencion: {skipped} omitidas (ya en cola o clasificadas en GCS).</span>"
                display(HTML(msg))
            else:
                display(HTML(f"<b style='color:orange;'>Atencion: {skipped} tareas omitidas. Ya estaban en la cola o ya se clasificaron en el Storage.</b>"))"""
txt = txt.replace(old_add_msg, new_add_msg)

with open(path, 'w', encoding='utf-8') as f:
    f.write(txt)
print("Atualizações de UI da M5 concluídas!")
