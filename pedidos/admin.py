from django.contrib import admin
from .models import Order, OrderItem, Coupon

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'guest_name', 'status', 'total_amount', 'created']
    list_filter = ['status', 'created', 'payment_method']
    inlines = [OrderItemInline]

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percentage', 'valid_from', 'valid_to', 'active']
    list_filter = ['active', 'valid_from', 'valid_to']
    search_fields = ['code']
