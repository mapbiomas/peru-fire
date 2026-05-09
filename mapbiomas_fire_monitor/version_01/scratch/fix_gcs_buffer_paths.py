import sys
import os

# Configurar path do core
sys.path.insert(0, r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core')

try:
    from M_cache import _get_fs
    from M0_auth_config import CONFIG
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    sys.exit(1)

fs = _get_fs()

# USANDO PREFIXO gs:// PARA GARANTIR QUE O GCSFS ENTENDA O BUCKET
bucket_name = CONFIG['bucket']
base_path = f"gs://{bucket_name}/sudamerica/peru/monitor/version_01/library_images/sentinel2/monthly"
wrong_base = f"{base_path}/minnbr"

print(f"🔍 Vasculhando GCS em: {wrong_base}")

try:
    # Listagem de períodos no minnbr
    periods = fs.ls(wrong_base)
except Exception as e:
    print(f"❌ Erro ao listar diretório base: {e}")
    sys.exit(1)

total_moved = 0

for p_path in periods:
    # p_path virá algo como: gs://bucket/.../minnbr/2026_04
    if not fs.isdir(p_path):
        continue
        
    period = os.path.basename(p_path.rstrip('/'))
    chunks_path = f"{p_path}/chunks"
    
    if fs.exists(chunks_path):
        try:
            files = fs.ls(chunks_path)
            # Filtra apenas o que deveria estar no buffer
            buffer_files = [f for f in files if 'minnbr_buffer' in f]
            
            if buffer_files:
                # Caminho de destino correto
                # Substitui a pasta 'minnbr' por 'minnbr_buffer' no caminho completo
                correct_dest_chunks = chunks_path.replace('/minnbr/', '/minnbr_buffer/')
                
                print(f"\n📦 Periodo {period}: Identificados {len(buffer_files)} shards de BUFFER em pasta errada.")
                
                # Garante que a pasta de destino exista
                if not fs.exists(correct_dest_chunks):
                    print(f"  -> Criando pasta: {correct_dest_chunks}")
                    fs.makedirs(correct_dest_chunks, exist_ok=True)
                
                for f in buffer_files:
                    filename = os.path.basename(f)
                    target = f"{correct_dest_chunks}/{filename}"
                    
                    try:
                        # Mover arquivo
                        fs.mv(f, target)
                        print(f"    ✅ Movido: {filename}")
                        total_moved += 1
                    except Exception as me:
                        print(f"    ❌ Erro ao mover {filename}: {me}")
                
                print(f"--- Concluido periodo {period} ---")
        except Exception as pe:
            print(f"⚠️ Erro ao processar chunks de {period}: {pe}")

print(f"\n🚀 FIM! Total de {total_moved} arquivos movidos com sucesso.")
