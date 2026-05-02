import os
import zipfile

def create_squarecloud_update_zip():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    zip_filename = os.path.join(base_dir, 'YasMimos_UPDATE_SQUARE.zip')
    
    # Files/Dirs to include
    include_files = [''
        'manage.py',
        'requirements.txt',
        'squarecloud.app',
        'main.py',
        'ca-certificate.crt',
        'certificate.pem',
        'private-key.key',
    ]
    
    include_dirs = [
        'carrinho',
        'sistema',
        'pedidos',
        'produtos',
        'static',
        'templates',
        'usuarios',
        'chat',
        'fidelidade',
        'robo_whatsapp',
        'robo_instagram',
        'YasMimos',
        # 'media' -> Excluded to avoid overwriting production images with local testing images
    ]
    
    excludes = [
        '__pycache__',
        '.git',
        '.github',
        '.vscode',
        'venv',
        'env',
        '.agent',
        'db.sqlite3', # CRITICAL: Exclude DB
        'db.sqlite3-journal',
        'staticfiles',
        'node_modules',
    ]

    print(f"Criando arquivo de ATUALIZAÇÃO (Sem Banco de Dados): {zip_filename}")
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add individual files
            for file in include_files:
                file_path = os.path.join(base_dir, file)
                if os.path.exists(file_path):
                    print(f"Adicionando {file}...")
                    zipf.write(file_path, file)

            # Add directories
            for directory in include_dirs:
                dir_path = os.path.join(base_dir, directory)
                if os.path.exists(dir_path):
                    print(f"Adicionando diretório {directory}...")
                    for root, dirs, files in os.walk(dir_path):
                        # Filter directories
                        dirs[:] = [d for d in dirs if d not in excludes]
                        
                        for file in files:
                            if file.endswith('.pyc') or file == '.DS_Store':
                                continue
                            if file == 'db.sqlite3': # Double check exclusion
                                continue
                            
                            file_full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_full_path, base_dir)
                            zipf.write(file_full_path, rel_path)
                else:
                    print(f"Aviso: Diretório {directory} não encontrado.")
                    
        print("\nZIP de Atualizacao Criado! [OK]")
        print(f"Arquivo: {zip_filename}")
        print("IMPORTANTE: Este arquivo NAO contem o 'db.sqlite3'. Use-o para atualizar o codigo mantendo os dados do site.")
        
    except Exception as e:
        print(f"Erro ao criar ZIP: {e}")

if __name__ == '__main__':
    create_squarecloud_update_zip()
