import os
import re

path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core\M4_model_trainer.py'
with open(path, 'r', encoding='utf-8') as f:
    txt = f.read()

# Add an auto-generate function inside ModelTrainerUI
smart_gen_func = '''
    def _auto_generate_shortname(self, *_):
        # Base format: [region]_[n]bands_[method]
        # Example: peru_r1_4bands_minnbr
        
        selected_samples = [name for name, chk in self.chk_dict.items() if chk.value]
        if not selected_samples:
            self.w_shortname.value = ""
            return
            
        first_sample = selected_samples[0]
        region_part = first_sample.replace('_samples', '').replace('library_samples_', '')
        if len(selected_samples) > 1:
            region_part += f'_multi'
            
        methods = set()
        bands_count = 0
        for (s, m, p, b), chk in self.band_chk_map.items():
            if chk.value:
                bands_count += 1
                methods.add(m)
                
        if bands_count == 0:
            return
            
        method_part = list(methods)[0] if len(methods) == 1 else 'mixed'
        
        new_name = f"{region_part}_{bands_count}bands_{method_part}"
        self.w_shortname.value = new_name
'''

if '_auto_generate_shortname' not in txt:
    txt = txt.replace('def _build_viz_toolbar(self):', smart_gen_func + '\n    def _build_viz_toolbar(self):')

hook_code = '''self.w_shortname = widgets.Text(value='peru_v1', description='Nome:', layout=L(width='200px'))
        
        # Smart Naming Hook
        def _hook_smart_naming(change):
            self._auto_generate_shortname()
            
        # Bind to samples
        for chk in self.chk_dict.values():
            chk.observe(_hook_smart_naming, names='value')
            
        # Bind to bands
        for chk in self.band_chk_map.values():
            chk.observe(_hook_smart_naming, names='value')
'''
# Using string replace without regex issues
txt = txt.replace("self.w_shortname = widgets.Text(value='peru_v1', description='Nome:', layout=L(width='200px'))", hook_code)

with open(path, 'w', encoding='utf-8') as f:
    f.write(txt)
print("Smart Name Generator injetado na M4!")
