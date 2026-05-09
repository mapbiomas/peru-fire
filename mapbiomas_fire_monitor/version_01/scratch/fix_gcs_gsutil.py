import os
import subprocess

# Lista de periodos detectados com erro (vamos fazer para todos os de 2025 e 2026)
years = ['2025', '2026']
months = [f"{m:02d}" for m in range(1, 13)]

bucket = "gs://mapbiomas-fire/sudamerica/peru/monitor/version_01/library_images/sentinel2/monthly"
wrong_base = f"{bucket}/minnbr"
correct_base = f"{bucket}/minnbr_buffer"

print("🚀 Iniciando migração via GSUTIL (Modo Seguro)")

for year in years:
    for month in months:
        period = f"{year}_{month}"
        
        source = f"{wrong_base}/{period}/chunks/*minnbr_buffer*"
        dest = f"{correct_base}/{period}/chunks/"
        
        # Primeiro, verificamos se existem arquivos para este periodo
        check_cmd = f'gsutil ls "{source}"'
        try:
            # shell=True é necessário no Windows para expandir wildcards do gsutil
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"\n📦 Periodo {period}: Encontrados shards de buffer. Movendo...")
                
                # Executa o movimento em massa (-m para paralelo)
                # O comando 'mv' no gsutil cria a pasta de destino automaticamente
                mv_cmd = f'gsutil -m mv "{source}" "{dest}"'
                subprocess.run(mv_cmd, shell=True)
                print(f"✅ Periodo {period} migrado com sucesso.")
            
        except Exception:
            # Se der erro ou não achar nada, apenas pula para o próximo mês
            continue

print("\n🏁 Finalizado! Todos os meses organizados.")
