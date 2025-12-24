from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from .models import Category, Product
from .forms import ProductForm
from orders.models import Order
from django.contrib.auth import get_user_model
from django.utils.text import slugify
User = get_user_model()

def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    return render(request, 'produtos/lista.html', {'category': category, 'categories': categories, 'products': products})

from django.db.models import Sum, F, Avg, Count

def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    return render(request, 'produtos/detalhes.html', {'product': product})

@user_passes_test(lambda u: u.is_superuser)
def manage_products(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    orders = Order.objects.filter(created__date=timezone.now().date()).order_by('-created')
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    
    # Financial Metrics
    # Financial Metrics
    total_sold = Order.objects.filter(status__in=['paid', 'shipped', 'completed']).aggregate(total=Sum('total_amount'))['total'] or 0
    total_stock = Product.objects.aggregate(total=Sum(F('price') * F('stock')))['total'] or 0
    
    total_projected = float(total_sold) + float(total_stock)
    progress_percentage = (float(total_sold) / total_projected * 100) if total_projected > 0 else 0
    avg_ticket = Order.objects.filter(status__in=['paid', 'shipped', 'completed']).aggregate(avg=Avg('total_amount'))['avg'] or 0
    
    context = {
        'products': products, 
        'orders': orders, 
        'total_sold': total_sold,
        'total_stock': total_stock,
        'total_projected': total_projected,
        'progress_percentage': progress_percentage,
        'progress_percentage': progress_percentage,
        'avg_ticket': avg_ticket,
        'users': users,
        'categories': categories
    }
    return render(request, 'produtos/gerenciar_lista.html', context)

@user_passes_test(lambda u: u.is_superuser)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.slug = slugify(product.name)
            product.save()
            return redirect('products:manage_products')
    else:
        form = ProductForm()
    return render(request, 'produtos/formulario_produto.html', {'form': form, 'title': 'Adicionar Produto'})

@user_passes_test(lambda u: u.is_superuser)
def edit_product(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            if 'remove_image' in request.POST:
                product.image = None
            if 'remove_image2' in request.POST:
                product.image2 = None
            if 'remove_image3' in request.POST:
                product.image3 = None
            if 'remove_image4' in request.POST:
                product.image4 = None
            if 'remove_image5' in request.POST:
                product.image5 = None
            product.slug = slugify(product.name)
            product.save()
            return redirect('products:manage_products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'produtos/formulario_produto.html', {'form': form, 'title': 'Editar Produto'})

@user_passes_test(lambda u: u.is_superuser)
def delete_product(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        product.delete()
        return redirect('products:manage_products')
    return render(request, 'produtos/confirmar_exclusao_produto.html', {'product': product})

@user_passes_test(lambda u: u.is_superuser)
def delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == 'POST':
        category.delete()
        return redirect('products:manage_products')
    return redirect('products:manage_products')

# API for Modal
from django.http import JsonResponse
import json

@user_passes_test(lambda u: u.is_superuser)
def api_add_category(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        if name:
            slug = slugify(name)
            category, created = Category.objects.get_or_create(slug=slug, defaults={'name': name})
            return JsonResponse({'success': True, 'id': category.id, 'name': category.name})
    return JsonResponse({'success': False})

@user_passes_test(lambda u: u.is_superuser)
def api_delete_category(request, id):
    if request.method == 'DELETE':
        category = get_object_or_404(Category, id=id)
        if category.products.count() > 0:
            return JsonResponse({'success': False, 'error': 'Categoria possui produtos vinculados.'})
        category.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def api_list_categories(request):
    categories = Category.objects.all().values('id', 'name', 'slug')
    return JsonResponse({'categories': list(categories)})

@user_passes_test(lambda u: u.is_superuser)
def product_list_rows_api(request):
    products = Product.objects.all()
    return render(request, 'produtos/parcial_linha_produto.html', {'products': products})

def product_grid_api(request):
    products = Product.objects.filter(available=True)
    return render(request, 'produtos/parcial_grade_produtos.html', {'products': products})

from django.utils import timezone
import datetime

@user_passes_test(lambda u: u.is_superuser)
def api_orders_by_date(request):
    date_str = request.GET.get('date')
    if date_str:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            orders = Order.objects.filter(created__date=date_obj).order_by('-created')
        except ValueError:
            orders = []
    else:
        orders = Order.objects.filter(created__date=timezone.now().date()).order_by('-created')
    
    return render(request, 'pedidos/parcial_lista_pedidos.html', {'orders': orders})
