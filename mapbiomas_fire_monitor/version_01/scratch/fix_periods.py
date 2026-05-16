import os

path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core\M5_classifier_ui.py'
with open(path, 'r', encoding='utf-8') as f:
    txt = f.read()

old_str = """        # 3. Periods
        periods = [] 
        box, self.chk_periods = self._create_checkbox_grid(periods, "3. Seleccione Períodos (Año / Año_Mes):", bg_color='#ebf5eb')
        self.w_period_box.children = box.children"""

new_str = """        # 3. Periods
        periods = []
        for y in self.years:
            if "yearly" in self.peridiocity_active:
                periods.append(str(y))
            if "monthly" in self.peridiocity_active:
                for m in range(1, 13):
                    periods.append(f"{y}_{m:02d}")
                    
        box, self.chk_periods = self._create_checkbox_grid(periods, "3. Seleccione Períodos (Año / Año_Mes):", bg_color='#ebf5eb')
        self.w_period_box.children = box.children"""

if old_str in txt:
    txt = txt.replace(old_str, new_str)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(txt)
    print("Sucesso!")
else:
    print("String antiga não encontrada!")
