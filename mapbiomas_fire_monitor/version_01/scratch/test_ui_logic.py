import sys
import os

# Configurar path do core
sys.path.insert(0, r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core')

from M0_auth_config import CONFIG, GLOBAL_OPTS, mosaic_name
from M_cache import CacheManager

def test_status_logic(year, month, sensor='sentinel2', period='monthly', mosaic_method='minnbr_buffer'):
    state = CacheManager.load(force=True)
    bands = CONFIG['bands_all']
    
    date_str = f"{year}_{month:02d}"
    print(f"\n--- TESTE DE STATUS UI: {mosaic_method.upper()} | {date_str} ---")
    print(f"{'Banda':<15} | {'Nome Esperado':<60} | {'Status UI'}")
    print("-" * 90)

    for b in bands:
        # EXATAMENTE A MESMA LOGICA DA LINHA 113 DO M2_mosaic_ui.py
        m_name = mosaic_name(year, month, period, band=b, mosaic=mosaic_method, sensor=sensor)
        
        # 1. Verifica se o COG final existe (Lógica da Linha 116)
        cogs_list = state.get('cogs_monthly' if period=='monthly' else 'cogs_annually', [])
        exists_cog = m_name.lower() in [c.lower() for c in cogs_list]
        
        # 2. Verifica se existem chunks para montar (Lógica da Linha 121)
        m_base_name = mosaic_name(year, month, period, mosaic=mosaic_method, sensor=sensor)
        chunks_in_state = state.get('gcs_chunks', {}).get(m_base_name.lower(), [])
        has_chunks = b in chunks_in_state
        
        # Decisão de Status (Lógica da Linha 127)
        if exists_cog:
            status = 'OK'
        elif has_chunks:
            status = 'READY'
        else:
            status = 'MISS'
            
        print(f"{b:<15} | {m_name:<60} | {status}")
        
        # Debug extra se for MISS
        if status == 'MISS':
            print(f"    [DEBUG] Chave no gcs_chunks: {m_base_name.lower()}")
            print(f"    [DEBUG] Bandas encontradas no cache: {chunks_in_state}")

# Executa para o mês que estávamos mexendo
test_status_logic(2026, 4)
