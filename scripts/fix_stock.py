import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yasmimos.settings')
django.setup()

from products.models import Product

try:
    p = Product.objects.get(name="Brigadeiro Branco")
    if p.stock == 29:
        print(f"Updating stock for {p.name} from {p.stock} to 30.")
        p.stock = 30
        p.save()
        print("Stock updated successfully.")
    else:
        print(f"Product stock is currently {p.stock}, skipping update.")
except Product.DoesNotExist:
    print("Product not found.")
