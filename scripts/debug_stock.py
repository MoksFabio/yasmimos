import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yasmimos.settings')
django.setup()

from products.models import Product
from orders.models import Order, OrderItem

print("--- Product Stock ---")
for p in Product.objects.all():
    print(f"{p.name}: {p.stock}")

print("\n--- Orders ---")
orders = Order.objects.all()
if not orders:
    print("No orders found.")
else:
    for o in orders:
        print(f"Order #{o.id} - Status: {o.status}")
        for item in o.items.all():
            print(f"  - {item.product.name} (Qty: {item.quantity})")

print("\n--- Orphaned Items ---")
# Check if any items exist without valid orders (should be impossible with CASCADE but good to check)
items = OrderItem.objects.all()
for i in items:
    if not i.order:
        print(f"Item {i.id} has no order!")
