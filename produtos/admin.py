from django.contrib import admin
from .models import Category, Product, Bundle

class BundleInline(admin.TabularInline):
    model = Bundle
    fk_name = 'parent_product'
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price', 'available', 'stock', 'created', 'updated']
    list_filter = ['available', 'created', 'updated', 'category']
    list_editable = ['price', 'available', 'stock']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [BundleInline]
