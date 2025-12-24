from products.models import Product
from django.utils.text import slugify

print("Fixing product slugs...")
count = 0
for p in Product.objects.all():
    new_slug = slugify(p.name)
    if new_slug != p.slug:
        print(f"Updating {p.name}: {p.slug} -> {new_slug}")
        p.slug = new_slug
        p.save()
        count += 1

print(f"Fixed {count} products.")
