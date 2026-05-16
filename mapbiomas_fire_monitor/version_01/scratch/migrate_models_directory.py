import gcsfs

def migrate():
    bucket = "mapbiomas-fire"
    # Onde os modelos estavam até antes da refatoração
    source = f"{bucket}/sudamerica/peru/CATALOG_01/LIBRARY_IMAGES/MODELS"
    # Para onde devem ir agora
    target = f"{bucket}/sudamerica/peru/CATALOG_01/LIBRARY_MODELS"
    
    print(f"Iniciando migração no GCS...")
    print(f"Origem: {source}")
    print(f"Destino: {target}")
    
    fs = gcsfs.GCSFileSystem(token='google_default')
    
    if not fs.exists(source):
        print(f"Aviso: O diretório de origem '{source}' não foi encontrado. Talvez a migração já tenha ocorrido ou o nome da pasta antiga é outro.")
        
        # Vamos checar se talvez estivessem no diretório antigo provisório
        source_legacy = f"{bucket}/sudamerica/peru/monitor/version_01/models"
        if fs.exists(source_legacy):
            print(f"Encontrados modelos no diretório MUITO antigo: {source_legacy}. Movendo de lá!")
            source = source_legacy
        else:
            return
            
    print("Mapeando arquivos...")
    files = fs.find(source)
    if not files:
        print("Nenhum arquivo encontrado no diretório de origem.")
        return
        
    print(f"Encontrados {len(files)} arquivos. Iniciando copia...")
    for f in files:
        new_f = f.replace(source, target)
        fs.copy(f, new_f)
        print(f" -> Copiado: {new_f.split('/')[-1]}")
        
    print("Verificando se a copia foi bem sucedida...")
    new_files = fs.find(target)
    if len(new_files) >= len(files):
        print("Copia validada com sucesso! Deletando o diretorio antigo...")
        fs.rm(source, recursive=True)
        print("Migracao concluida. A pasta antiga foi apagada.")
    else:
        print("Parece que houve um problema na copia. Abortando a exclusao do diretorio antigo por seguranca.")

if __name__ == '__main__':
    migrate()
