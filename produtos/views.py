from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from .models import Category, Product, Review, Supply, ProductBatch, BatchIngredient
from .forms import ProductForm, ReviewForm
from pedidos.models import Order
from sistema.models import StoreSettings
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
User = get_user_model()

def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    return render(request, 'produtos/lista.html', {'category': category, 'categories': categories, 'produtos': products})

from django.db.models import Sum, F, Avg, Count

def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    reviews = product.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('usuarios:login')
        
        # Check for AJAX
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or \
                  request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' or \
                  request.POST.get('is_ajax') == 'true'

        review_id = request.POST.get('review_id')
        if review_id:
            review_instance = get_object_or_404(Review, id=review_id)
            if review_instance.user != request.user and not request.user.is_superuser:
                 return redirect('produtos:detalhes', id=product.id, slug=product.slug)
            form = ReviewForm(request.POST, instance=review_instance)
        else:
            form = ReviewForm(request.POST)

        if form.is_valid():
            try:
                review = form.save(commit=False)
                if not review_id:
                    review.product = product
                    review.user = request.user
                review.save()
                
                if is_ajax:
                    # Refresh context
                    reviews = product.reviews.all().order_by('-created_at')
                    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
                    html = render_to_string('produtos/parcial_secao_avaliacoes.html', {
                        'produto': product, 
                        'reviews': reviews, 
                        'review_form': ReviewForm(), # Fresh form on success
                        'avg_rating': round(avg_rating, 1),
                        'user': request.user,
                        'request': request
                    })
                    return JsonResponse({'success': True, 'html': html})

                return redirect('produtos:detalhes', id=product.id, slug=product.slug)
            except Exception as e:
                print(f"Error saving review: {e}")
                if is_ajax:
                     return JsonResponse({'success': False, 'error': str(e)})
                raise e # Let Django handle 500
        
        # If form is INVALID and AJAX
        if is_ajax:
             print(f"Form Errors: {form.errors}")
             reviews = product.reviews.all().order_by('-created_at')
             avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
             html = render_to_string('produtos/parcial_secao_avaliacoes.html', {
                'produto': product, 
                'reviews': reviews, 
                'review_form': form, # ERROR form
                'avg_rating': round(avg_rating, 1),
                'user': request.user,
                'request': request
             })
             # Return HTML of the form with errors, but mark success=False
             return JsonResponse({'success': False, 'html': html, 'errors': form.errors})

    else:
        form = ReviewForm()

    customizable_items = None
    if product.is_customizable and product.customization_category:
        customizable_items = Product.objects.filter(
            category=product.customization_category, 
            available=True
        )

    return render(request, 'produtos/detalhes.html', {
        'produto': product, 
        'reviews': reviews, 
        'review_form': form, 
        'avg_rating': round(avg_rating, 1),
        'customizable_items': customizable_items
    })

@user_passes_test(lambda u: u.is_authenticated)
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    product = review.product
    if request.user == review.user or request.user.is_superuser:
        review.delete()
    
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or \
              request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    if is_ajax:
        reviews = product.reviews.all().order_by('-created_at')
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        html = render_to_string('produtos/parcial_secao_avaliacoes.html', {
            'produto': product, 
            'reviews': reviews, 
            'review_form': ReviewForm(),
            'avg_rating': round(avg_rating, 1),
            'user': request.user,
            'request': request
        })
        return JsonResponse({'success': True, 'html': html})

    return redirect('produtos:detalhes', id=product.id, slug=product.slug)

@user_passes_test(lambda u: u.is_staff)
def manage_products(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    products = Product.objects.all()
    categories = Category.objects.all()
    orders = Order.objects.all().order_by('-created')
    users = User.objects.all().order_by('-date_joined')
    
    # Financial Metrics
    total_sold = Order.objects.filter(status__in=['paid', 'shipped', 'completed']).aggregate(total=Sum('total_amount'))['total'] or 0
    total_stock = Product.objects.aggregate(total=Sum(F('price') * F('stock')))['total'] or 0
    
    total_projected = float(total_sold) + float(total_stock)
    progress_percentage = (float(total_sold) / total_projected * 100) if total_projected > 0 else 0
    avg_ticket = Order.objects.filter(status__in=['paid', 'shipped', 'completed']).aggregate(avg=Avg('total_amount'))['avg'] or 0
    
    # Prepare Chart Data (Last 30 days daily sales)
    from django.utils import timezone
    from datetime import timedelta
    import json
    
    today = timezone.now().date()
    # Get last 14 days
    dates = [(today - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(13, -1, -1)]
    sales_data = [] # Stores total amount per day
    
    valid_orders = orders.filter(status__in=['paid', 'shipped', 'completed']) # Only counted paid sales
    
    # Inefficient but simple for small scale. For large scale, use TruncDay
    data_map = {}
    for o in valid_orders:
        d = o.created.astimezone(timezone.get_current_timezone()).date().strftime('%Y-%m-%d')
        if d not in data_map: data_map[d] = 0
        data_map[d] += float(o.total_amount)
        
    for d in dates:
        sales_data.append(data_map.get(d, 0))
        
    sales_data_json = json.dumps(sales_data)
    dates_labels = [(today - timedelta(days=x)).strftime('%d/%m') for x in range(13, -1, -1)]
    dates_json = json.dumps(dates_labels)
    
    # Top Products
    from pedidos.models import OrderItem
    top_products_data = OrderItem.objects.filter(order__status__in=['paid', 'shipped', 'delivered', 'completed', 'ready', 'preparing']) \
        .values('product__name', 'product__image') \
        .annotate(total_qty=Sum('quantity'), total_rev=Sum(F('quantity') * F('price'))) \
        .order_by('-total_qty')[:4]
    
    # Growth metrics (comparing last 14 days vs previous 14 days)
    period_1 = sum(sales_data)
    prev_dates = [(today - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(27, 13, -1)]
    period_2 = sum(data_map.get(d, 0) for d in prev_dates)
    
    if period_2 > 0:
        growth_sold = ((period_1 - period_2) / period_2) * 100
    else:
        growth_sold = 100 if period_1 > 0 else 0
        
    # Same for today vs yesterday
    today_str = today.strftime('%Y-%m-%d')
    yesterday_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    sold_today = data_map.get(today_str, 0)
    sold_yesterday = data_map.get(yesterday_str, 0)
    if sold_yesterday > 0:
        growth_today = ((sold_today - sold_yesterday) / sold_yesterday) * 100
    else:
        growth_today = 100 if sold_today > 0 else 0
        
    # PRE-LOAD USERS FOR INSTANT DISPLAY
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admins = User.objects.filter(is_staff=True).order_by('-date_joined')
    all_users = User.objects.all().order_by('-date_joined')
    
    context = {
        'products': products, 
        'orders': orders, 
        'total_sold': total_sold,
        'total_stock': total_stock,
        'total_projected': total_projected,
        'progress_percentage': progress_percentage,
        'avg_ticket': avg_ticket,
        'usuarios': users, # legacy
        'users': all_users,
        'admins': admins,
        'categories': categories,
        'supplies': Supply.objects.all().order_by('name'),
        'products_with_recipe': Product.objects.all().prefetch_related('batch_recipe'),
        'store_settings': StoreSettings.get_settings(),
        'sales_data_json': sales_data_json,
        'dates_json': dates_json,
        'top_products': top_products_data,
        'growth_sold': growth_sold,
        'growth_today': growth_today,
    }
    # Ensure current tab is preserved if needed, logic is client-side though.
    return render(request, 'produtos/gerenciar_lista.html', context)

@user_passes_test(lambda u: u.is_staff)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.slug = slugify(product.name)
            # Se for personalizada, garante que o estoque seja alto/infinito na prática (ou apenas ignorado pela view)
            if "Personalizada" in product.name:
                product.stock = 999 
            product.save()
            return redirect('produtos:gerenciar')
    else:
        form = ProductForm()
    
    return render(request, 'produtos/formulario_produto.html', {
        'form': form,
        'title': 'Adicionar Novo Produto',
        'all_products': Product.objects.all().order_by('name')
    })

@user_passes_test(lambda u: u.is_staff)
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
            if "Personalizada" in product.name:
                product.stock = 999
            product.save()
            return redirect('produtos:gerenciar')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'produtos/formulario_produto.html', {
        'form': form,
        'title': f'Editar {product.name}',
        'all_products': Product.objects.all().order_by('name')
    })

@user_passes_test(lambda u: u.is_staff)
def delete_product(request, id):
    product = get_object_or_404(Product, id=id)
    product.delete()
    return redirect('produtos:gerenciar')

@user_passes_test(lambda u: u.is_staff)
def empty_stock(request):
    if request.method == 'POST':
        from django.db.models import Q
        Product.objects.exclude(
            Q(is_customizable=True) | Q(name__icontains="Personalizada")
        ).update(stock=0)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Método inválido.'})

@user_passes_test(lambda u: u.is_staff)
def delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == 'POST':
        category.delete()
        return redirect('produtos:gerenciar')
    return redirect('produtos:gerenciar')

# API for Modal
from django.http import JsonResponse
import json

@user_passes_test(lambda u: u.is_staff)
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
        if category.produtos.count() > 0:
            return JsonResponse({'success': False, 'error': 'Categoria possui produtos vinculados.'})
        category.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def api_list_categories(request):
    categories = Category.objects.all().values('id', 'name', 'slug')
    return JsonResponse({'categories': list(categories)})

@user_passes_test(lambda u: u.is_staff)
def product_list_rows_api(request):
    products = Product.objects.all().order_by('name')
    return render(request, 'produtos/parcial_linha_produto.html', {'products': products})

@user_passes_test(lambda u: u.is_superuser)
def api_product_list_simple(request):
    products = Product.objects.all().values('id', 'name', 'price')
    return JsonResponse(list(products), safe=False)

def product_grid_api(request):
    products = Product.objects.filter(available=True)
    category_slug = request.GET.get('category')
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    return render(request, 'produtos/parcial_grade_produtos.html', {'produtos': products})

from django.utils import timezone
import datetime

@user_passes_test(lambda u: u.is_superuser)
def api_orders_by_date(request):
    orders = Order.objects.all().order_by('-created')
    
    # Date Filter
    date_str = request.GET.get('date')
    if date_str:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            orders = orders.filter(created__date=date_obj)
        except ValueError:
            pass
    
    # Status Filter
    status = request.GET.get('status')
    if status and status != 'all':
        orders = orders.filter(status=status)

    # Payment Method Filter
    payment_method = request.GET.get('payment_method')
    if payment_method and payment_method != 'all':
        orders = orders.filter(payment_method=payment_method)

    return render(request, 'pedidos/parcial_lista_pedidos.html', {'pedidos': orders})
@user_passes_test(lambda u: u.is_superuser)
def manage_categories(request):
    return_url = request.GET.get('return_url')
    return render(request, 'produtos/gerenciar_categorias.html', {'return_url': return_url})

# --- PROFITABILITY API ---
@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def api_add_supply(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            
            # Smart Upsert: Update if exists, else Create
            supply = Supply.objects.filter(name__iexact=name).first()
            
            new_stock = Decimal(str(data.get('stock_quantity', 0)))
            new_price = data.get('price')
            new_weight = data.get('quantity')
            new_unit = data.get('unit')

            if supply:
                # Update existing
                supply.price = new_price
                supply.quantity = new_weight
                supply.unit = new_unit
                supply.stock_quantity = supply.stock_quantity + new_stock
                supply.save()
            else:
                # Create new
                supply = Supply.objects.create(
                    name=name,
                    price=new_price,
                    quantity=new_weight,
                    unit=new_unit,
                    stock_quantity=new_stock
                )

            return JsonResponse({
                'success': True, 
                'id': supply.id, 
                'name': supply.name, 
                'unit': supply.unit,
                'stock_quantity': supply.stock_quantity,
                'price': supply.price,
                'quantity': supply.quantity,
                'price_per_unit': supply.price_per_unit()
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Method not allowed'})
@user_passes_test(lambda u: u.is_superuser)
def api_delete_supply(request, id):
    if request.method == 'DELETE':
        try:
            supply = Supply.objects.get(id=id)
            supply.delete()
            return JsonResponse({'success': True})
        except Supply.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Insumo não encontrado.'})
    return JsonResponse({'success': False, 'error': 'Método inválido'})

@user_passes_test(lambda u: u.is_superuser)
def api_save_batch_recipe(request):
    """
    Saves or updates a product's recipe (batch).
    Expected JSON: 
    {
        'product_id': 1,
        'unit_weight_g': 20,
        'evaporation': 15,
        'ingredients': [
            {'supply_id': 1, 'qty': 395},
            {'supply_id': 2, 'qty': 200}
        ]
    }
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            product = get_object_or_404(Product, id=product_id)
            
            # Create or Update Batch
            batch, created = ProductBatch.objects.get_or_create(product=product)
            batch.unit_weight_g = data.get('unit_weight_g', 0)
            batch.evaporation_percent = data.get('evaporation', 15)
            batch.save()
            
            # Clear existing ingredients (simple overwrite)
            batch.ingredients.all().delete()
            
            # Add new ingredients
            for item in data.get('ingredients', []):
                supply = get_object_or_404(Supply, id=item['supply_id'])
                BatchIngredient.objects.create(
                    batch=batch,
                    supply=supply,
                    quantity=item['qty']
                )
            
            metrics = batch.calculate_metrics()
            return JsonResponse({'success': True, 'metrics': metrics})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@user_passes_test(lambda u: u.is_superuser)
def api_get_batch_details(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        if hasattr(product, 'batch_recipe'):
            batch = product.batch_recipe
            metrics = batch.calculate_metrics()
            
            ingredients = []
            for item in batch.ingredients.all():
                ingredients.append({
                    'supply_id': item.supply.id,
                    'name': item.supply.name,
                    'qty': float(item.quantity),
                    'cost': float(item.get_cost())
                })
            
            return JsonResponse({
                'success': True,
                'found': True,
                'data': {
                    'unit_weight_g': float(batch.unit_weight_g),
                    'evaporation': batch.evaporation_percent,
                    'ingredients': ingredients,
                    'metrics': metrics
                }
            })
        else:
            return JsonResponse({'success': True, 'found': False})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
