from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, related_name='produtos', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='produtos/%Y/%m/%d', blank=True)
    image2 = models.ImageField(upload_to='produtos/%Y/%m/%d', blank=True, verbose_name="Imagem 2 (Opcional)")
    image3 = models.ImageField(upload_to='produtos/%Y/%m/%d', blank=True, verbose_name="Imagem 3 (Opcional)")
    image4 = models.ImageField(upload_to='produtos/%Y/%m/%d', blank=True, verbose_name="Imagem 4 (Opcional)")
    image5 = models.ImageField(upload_to='produtos/%Y/%m/%d', blank=True, verbose_name="Imagem 5 (Opcional)")
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    
    # Customization (for Kits/Boxes)
    is_customizable = models.BooleanField(default=False, verbose_name="É personalizável?")
    customizable_slots = models.PositiveIntegerField(default=0, verbose_name="Quantidade de Itens")
    customization_category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='customization_for', verbose_name="Categoria de Itens")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

class Bundle(models.Model):
    parent_product = models.ForeignKey(Product, related_name='bundle_items', on_delete=models.CASCADE)
    sub_product = models.ForeignKey(Product, related_name='contained_in_bundles', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Combo/Kit"

    def __str__(self):
        return f"{self.quantity}x {self.sub_product.name} in {self.parent_product.name}"

class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reviews', on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Avaliação de {self.user} para {self.product}'

class Supply(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome do Insumo")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Pago (R$)")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Quantidade na Embalagem")
    UNIT_CHOICES = (
        ('g', 'Gramas (g)'),
        ('ml', 'Mililitros (ml)'),
        ('un', 'Unidades (un)'),
    )
    unit = models.CharField(max_length=5, choices=UNIT_CHOICES, default='g', verbose_name="Unidade")
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Estoque (Qtd Embalagens)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Insumo"

    def __str__(self):
        return f"{self.name} ({self.quantity}{self.unit})"

    def price_per_unit(self):
        # Avoid division by zero
        if self.quantity and self.quantity > 0:
            return float(self.price) / float(self.quantity)
        return 0.0

class ProductBatch(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='batch_recipe')
    unit_weight_g = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    evaporation_percent = models.DecimalField(max_digits=5, decimal_places=2, default=15) # Keep for backend compat
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ficha Técnica"

    def __str__(self):
        return f"Ficha: {self.product.name}"

    def calculate_metrics(self):
        # Calculate total weight of ingredients
        ingredients = self.ingredients.all()
        total_weight_raw = sum([float(item.quantity) for item in ingredients])
        total_cost = sum([item.get_cost() for item in ingredients])
        
        # Apply evaporation loss to weight (cooked weight)
        cooked_weight = total_weight_raw * (1 - (self.evaporation_percent / 100))
        
        # Yield (Rendimento)
        estimated_units = 0
        if self.unit_weight_g > 0:
            estimated_units = int(cooked_weight / float(self.unit_weight_g))
            
        unit_cost = 0
        if estimated_units > 0:
            unit_cost = total_cost / estimated_units
            
        return {
            'total_cost': total_cost,
            'raw_weight': total_weight_raw,
            'cooked_weight': cooked_weight,
            'estimated_units': estimated_units,
            'unit_cost': unit_cost
        }

class BatchIngredient(models.Model):
    batch = models.ForeignKey(ProductBatch, on_delete=models.CASCADE, related_name='ingredients')
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, verbose_name="Insumo")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Qtd. Usada")
    
    class Meta:
        verbose_name = "Ingrediente da Ficha"
    
    def get_cost(self):
        return float(self.quantity) * self.supply.price_per_unit()
