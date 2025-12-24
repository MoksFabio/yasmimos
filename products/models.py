from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True)
    image2 = models.ImageField(upload_to='products/%Y/%m/%d', blank=True, verbose_name="Imagem 2 (Opcional)")
    image3 = models.ImageField(upload_to='products/%Y/%m/%d', blank=True, verbose_name="Imagem 3 (Opcional)")
    image4 = models.ImageField(upload_to='products/%Y/%m/%d', blank=True, verbose_name="Imagem 4 (Opcional)")
    image5 = models.ImageField(upload_to='products/%Y/%m/%d', blank=True, verbose_name="Imagem 5 (Opcional)")
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name
