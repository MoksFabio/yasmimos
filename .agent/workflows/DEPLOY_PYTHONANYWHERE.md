# Desativar/Ativar modo Turbo para comandos, defina como 'true'.
SafeToAutoRun: true
---
description: Guia Completo para Deploy no PythonAnywhere
---

# Deploy na PythonAnywhere

Siga este guia passo-a-passo para colocar o YasMimos no ar.

## 1. Preparação Local (Já Feito!)

Nós já configuramos os arquivos essenciais:
- `requirements.txt`: Atualizado.
- `settings.py`: Configurado para segurança e arquivos estáticos (WhiteNoise).
- `.gitignore`: Criado para evitar subir arquivos sensíveis.

## 2. Salvar Código no GitHub (Via Terminal)

Abra o terminal e rode estes comandos para enviar o código para o GitHub (se já não tiver feito).
*Nota: Você precisará criar um repositório vazio no GitHub antes.*

```bash
git init
git add .
git commit -m "Preparando deploy"
git branch -M main
# Substitua SEU_USUARIO pelo seu usuário do GitHub
git remote add origin https://github.com/SEU_USUARIO/yasmimos.git
git push -u origin main
```

## 3. Configuração no PythonAnywhere

1.  Crie uma conta em [PythonAnywhere.com](https://www.pythonanywhere.com/).
2.  Vá em **Consoles** > **Bash**.
3.  Clone seu repositório:
    ```bash
    git clone https://github.com/SEU_USUARIO/yasmimos.git
    cd yasmimos
    ```
4.  Crie um ambiente virtual e instale dependências:
    ```bash
    mkvirtualenv --python=/usr/bin/python3.10 myvenv
    pip install -r requirements.txt
    ```

## 4. Configurar Variáveis de Ambiente

No PythonAnywhere, você deve configurar as variáveis de segurança.
Vá na aba **Web**, e na seção **WSGI configuration file**, edite o arquivo. Adicione isso no topo (antes de importar django):

```python
import os
os.environ['DJANGO_SECRET_KEY'] = 'sk-sua-chave-secreta-aleatoria-aqui'
os.environ['DJANGO_DEBUG'] = 'False'
os.environ['DJANGO_ALLOWED_HOSTS'] = 'seu-usuario.pythonanywhere.com'
os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'SuaSenhaForteAdmin123'
```

*Dica: Você pode gerar uma SECRET_KEY aleatória online.*

## 5. Configurar Banco de Dados e Estáticos

Volte ao **Console Bash** e rode:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser  # Vai usar a variável de ambiente que definimos ou pedir senha
```

## 6. Configurar o Web App

1.  Vá na aba **Web**.
2.  **Source code**: `/home/SEU_USUARIO/yasmimos`
3.  **Working directory**: `/home/SEU_USUARIO/yasmimos`
4.  **Virtualenv**: `/home/SEU_USUARIO/.virtualenvs/myvenv`
5.  **Static files**:
    *   URL: `/static/`
    *   Path: `/home/SEU_USUARIO/yasmimos/staticfiles`
    *   URL: `/media/`
    *   Path: `/home/SEU_USUARIO/yasmimos/media`

## 7. Reload
Clique no botão verde **Reload** no topo da página.

Pronto! Seu site estará no ar em `seu-usuario.pythonanywhere.com`.
