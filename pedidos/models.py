from django.db import models
from django.conf import settings
from produtos.models import Product
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pendente'),
        ('paid', 'Pago'),
        ('preparing', 'Em Produção'),
        ('ready', 'Finalizado'),
        ('shipped', 'Enviado'),
        ('delivered', 'Entregue'),
        ('cancelled', 'Cancelado'),
        ('refunded', 'Reembolsado'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pedidos', null=True, blank=True)
    guest_name = models.CharField(max_length=100, blank=True, null=True)
    guest_phone = models.CharField(max_length=20, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=50, default='pix')
    coupon = models.ForeignKey('Coupon', related_name='pedidos', null=True, blank=True, on_delete=models.SET_NULL)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tip_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Gorjeta")
    mercado_pago_id = models.CharField(max_length=100, blank=True, null=True)
    mercado_pago_status = models.CharField(max_length=50, blank=True, null=True)
    mp_beneficiary = models.CharField(max_length=20, blank=True, null=True, choices=[('fabio', 'Fábio'), ('yasmim', 'Yasmim')])
    observations = models.TextField(blank=True, null=True, verbose_name="Observações do Pedido")

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f'Order {self.id}'

    def get_subtotal(self):
        return sum(item.get_cost() for item in self.items.all())

    @property
    def has_customizable_items(self):
        return self.items.filter(metadata__isnull=False).exists()

    @property
    def clube_plan_name(self):
        for item in self.items.all():
            if item.product.category and 'clube' in item.product.category.name.lower():
                return item.product.name
        return None

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Item do Pedido"

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Porcentagem de desconto (0-100)"
    )
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Valor Mínimo")
    max_uses = models.PositiveIntegerField(null=True, blank=True, verbose_name="Limite de Usos")
    used_count = models.PositiveIntegerField(default=0, verbose_name="Quantidade Usada")

    class Meta:
        verbose_name = "Cupom"

    def __str__(self):
        return self.code
