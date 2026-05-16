import os

path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core\M5_classifier_ui.py'
with open(path, 'r', encoding='utf-8') as f:
    txt = f.read()

# 1. Update Grid logic to accept specific columns
old_grid = """    def _create_checkbox_grid(self, options, description, single_select=False, bg_color='#fafafa'):
        title = widgets.HTML(f"<div style='margin-bottom:5px; color:#2c3e50;'><b>{description}</b></div>")
        checkboxes = []
        for opt in options:
            chk = widgets.Checkbox(value=False, description=str(opt), indent=False, style={'description_width': 'initial'}, layout=widgets.Layout(width='auto', margin='0 5px 5px 0'))
            checkboxes.append(chk)
            
        if single_select:
            def on_change(change, current_chk):
                if change['new']:
                    for c in checkboxes:
                        if c != current_chk:
                            c.value = False
            for chk in checkboxes:
                chk.observe(lambda change, c=chk: on_change(change, c), names='value')
                
        grid = widgets.GridBox(checkboxes, layout=widgets.Layout(grid_template_columns="repeat(auto-fill, minmax(280px, 1fr))", width='100%'))"""

new_grid = """    def _create_checkbox_grid(self, options, description, single_select=False, bg_color='#fafafa', columns=None):
        title = widgets.HTML(f"<div style='margin-bottom:5px; color:#2c3e50;'><b>{description}</b></div>")
        checkboxes = []
        for opt in options:
            chk = widgets.Checkbox(value=False, description=str(opt), indent=False, style={'description_width': 'initial'}, layout=widgets.Layout(width='auto', margin='0 5px 5px 0'))
            checkboxes.append(chk)
            
        if single_select:
            def on_change(change, current_chk):
                if change['new']:
                    for c in checkboxes:
                        if c != current_chk:
                            c.value = False
            for chk in checkboxes:
                chk.observe(lambda change, c=chk: on_change(change, c), names='value')
                
        gtc = f"repeat({columns}, 1fr)" if columns else "repeat(auto-fill, minmax(280px, 1fr))"
        grid = widgets.GridBox(checkboxes, layout=widgets.Layout(grid_template_columns=gtc, width='100%'))"""

if old_grid in txt:
    txt = txt.replace(old_grid, new_grid)

# 2. Update Periods logic with datetime sorting and columns=4
old_str = """        # 3. Periods
        periods = []
        for y in self.years:
            if "yearly" in self.peridiocity_active:
                periods.append(str(y))
            if "monthly" in self.peridiocity_active:
                for m in range(1, 13):
                    periods.append(f"{y}_{m:02d}")
                    
        box, self.chk_periods = self._create_checkbox_grid(periods, "3. Seleccione Períodos (Año / Año_Mes):", bg_color='#ebf5eb')"""

new_str = """        # 3. Periods
        import datetime
        now = datetime.datetime.now()
        
        periods = []
        for y in self.years:
            if "yearly" in self.peridiocity_active:
                if y < now.year:
                    periods.append(str(y))
            if "monthly" in self.peridiocity_active:
                max_m = (now.month - 1) if y == now.year else (12 if y < now.year else 0)
                for m in range(1, max_m + 1):
                    periods.append(f"{y}_{m:02d}")
                    
        periods.sort(reverse=True)
        box, self.chk_periods = self._create_checkbox_grid(periods, "3. Seleccione Períodos (Año / Año_Mes):", bg_color='#ebf5eb', columns=4)"""

if old_str in txt:
    txt = txt.replace(old_str, new_str)
    
with open(path, 'w', encoding='utf-8') as f:
    f.write(txt)
print("Sucesso!")
