import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yasmimos.settings')
django.setup()

from products.models import Category, Product

if not Category.objects.exists():
    c1 = Category.objects.create(name='Brigadeiros', slug='brigadeiros')
    c2 = Category.objects.create(name='Brownies', slug='brownies')
    c3 = Category.objects.create(name='Bolos no Pote', slug='bolos-no-pote')

    Product.objects.create(category=c1, name='Brigadeiro Tradicional', slug='brigadeiro-tradicional', price=5.00, description='O clássico brigadeiro de chocolate belga.')
    Product.objects.create(category=c1, name='Brigadeiro de Ninho', slug='brigadeiro-ninho', price=6.00, description='Delicioso brigadeiro de leite ninho com Nutella.')
    Product.objects.create(category=c1, name='Brigadeiro de Morango', slug='brigadeiro-morango', price=5.50, description='Brigadeiro bicho de pé feito com morangos frescos.')
    
    Product.objects.create(category=c2, name='Brownie Recheado', slug='brownie-recheado', price=12.00, description='Brownie molhadinho com muito recheio de doce de leite.')
    Product.objects.create(category=c2, name='Brownie Simples', slug='brownie-simples', price=8.00, description='Brownie tradicional com casquinha crocante.')
    
    Product.objects.create(category=c3, name='Bolo de Cenoura', slug='bolo-cenoura', price=15.00, description='Bolo de cenoura com cobertura de chocolate.')

    print("Database populated successfully.")
else:
    print("Database already populated.")
