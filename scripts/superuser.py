import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yasmimos.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

if User.objects.filter(username='admin').exists():
    print("Superusuário 'admin' existe e está seguro.")
else:
    print("ATENÇÃO: Superusuário 'admin' não existe! Crie um usando: python manage.py createsuperuser")
