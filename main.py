import os
import sys
import subprocess
import django
from django.core.management import execute_from_command_line

def main():
    # 1. CONFIGURAÇÕES INICIAIS
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "YasMimos.settings")
    
    # 2. CORREÇÃO DE PERMISSÕES SSL (Obrigatório para Square Cloud)
    key_path = "/application/private-key.key"
    if os.path.exists(key_path):
        try:
            os.chmod(key_path, 0o600)
            print("Permissoes da chave SSL ajustadas.")
        except:
            pass

    # 3. SETUP DJANGO
    try:
        django.setup()
    except Exception as e:
        print(f"Erro no setup do Django: {e}")

    # 4. PREPARAÇÃO DO SERVIDOR (Migrate e Static)
    print("--- PREPARANDO NOVO AMBIENTE ---")
    
    # Coleta arquivos estáticos (Visual do site)
    subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"])
    
    # Cria as tabelas do zero e atualiza mudanças recentes
    subprocess.run([sys.executable, "manage.py", "makemigrations", "--noinput"])
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"])
    
    # Atualiza o nome do site no banco (de example.com para yasmimos.com.br)
    try:
        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        site.domain = 'yasmimos.com.br'
        site.name = 'YasMimos'
        site.save()
        print("Nome do site atualizado no banco.")
        
        # PROMOVE O PRIMEIRO USUÁRIO A ADMIN (FORÇADO)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        first_user = User.objects.order_by('id').first()
        if first_user and not first_user.is_superuser:
            first_user.is_staff = True
            first_user.is_superuser = True
            first_user.save()
            print(f"FORÇADO: Usuario {first_user.username} promovido a SuperAdmin.")

        # CRIA CONFIGURAÇÕES DA LOJA SE NÃO EXISTIREM
        from sistema.models import StoreSettings
        if not StoreSettings.objects.exists():
            StoreSettings.objects.create(pk=1, is_open=True)
            print("Configuracoes da loja inicializadas.")

        # CORREÇÃO DEFINITIVA DE CATEGORIAS E SLUGS
        from produtos.models import Category
        from django.utils.text import slugify
        from django.db import models
        
        # 1. Se não houver nada, cria as padrão
        if not Category.objects.exists():
            for cat_name in ['Brigadeiros', 'Kits', 'Bebidas', 'Caixas']:
                Category.objects.create(name=cat_name, slug=slugify(cat_name))
            print("Categorias padrao criadas.")
        
        # 2. SE JÁ EXISTIREM, CORRIGE AS QUE ESTÃO SEM SLUG
        for cat in Category.objects.filter(models.Q(slug='') | models.Q(slug__isnull=True)):
            cat.slug = slugify(cat.name)
            cat.save()
            print(f"Slug corrigido para a categoria: {cat.name}")
            
    except Exception as e:
        print(f"Aviso na inicializacao: {e}")
    
    print("--- AMBIENTE PRONTO ---")

    # 5. INICIAR BOT DO WHATSAPP (Segundo Plano)
    try:
        # Instala dependências do bot se não existirem
        bot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "robo_whatsapp")
        if not os.path.exists(os.path.join(bot_dir, "node_modules")):
            print("Instalando dependencias do bot do WhatsApp...")
            subprocess.run(["npm", "install"], cwd=bot_dir)
            
        subprocess.Popen(["node", "index.js"], 
                        cwd=bot_dir)
        print("Bot do WhatsApp iniciado.")
    except Exception as e:
        print(f"Aviso: Nao foi possivel iniciar o bot do WhatsApp. Detalhes: {e}")

    # 5.1 INICIAR BOT DO INSTAGRAM (Segundo Plano)
    try:
        if os.environ.get("IG_USERNAME") and (os.environ.get("IG_PASSWORD") or os.environ.get("IG_SESSIONID")):
            ig_bot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "robo_instagram")
            if os.path.exists(ig_bot_dir):
                if not os.path.exists(os.path.join(ig_bot_dir, "node_modules")):
                    print("Instalando dependencias do bot do Instagram...")
                    subprocess.run(["npm", "install"], cwd=ig_bot_dir)
                    
                subprocess.Popen(["node", "index.js"], 
                                cwd=ig_bot_dir)
                print("Bot do Instagram iniciado.")
        else:
            print("Bot do Instagram pulado: Credenciais IG_USERNAME ou IG_PASSWORD ausentes no ambiente.")
    except Exception as e:
        print(f"Aviso: Nao foi possivel iniciar o bot do Instagram. Detalhes: {e}")

    # 6. INICIAR SERVIDOR DAPHNE
    print("Iniciando servidor...")
    subprocess.run([sys.executable, "-m", "daphne", "-b", "0.0.0.0", "-p", "80", "YasMimos.asgi:application"])

if __name__ == "__main__":
    main()
