from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from produtos.models import Product
from .cart import Cart

@require_POST
def cart_add(request, product_id):
    carrinho = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    if quantity < 1:
        quantity = 1
    import json
    metadata_raw = request.POST.get('metadata')
    metadata = None
    if metadata_raw:
        try:
            metadata = json.loads(metadata_raw)
        except:
            pass
            
    # Bloquear compra de Clube repetido se já estiver ativo
    if product.category and 'clube' in product.category.name.lower():
        # Bloquear se já estiver no carrinho
        if str(product.id) in carrinho.carrinho:
            msg = f'O {product.name} já está no seu carrinho!'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json'):
                return JsonResponse({'success': False, 'message': msg})
            from django.contrib import messages
            messages.warning(request, msg)
            referer = request.META.get('HTTP_REFERER')
            return redirect(referer) if referer else redirect('carrinho:cart_detail')
            
        if request.user.is_authenticated:
            from pedidos.models import OrderItem
            from django.utils import timezone
            from datetime import timedelta
            import calendar
            
            sixty_days_ago = timezone.now() - timedelta(days=60)
            valid_statuses = ['paid', 'preparing', 'ready', 'shipped', 'delivered']
            
            # Fetch recent orders of THIS EXACT product
            recent_same_clubs = OrderItem.objects.filter(
                order__user=request.user,
                order__status__in=valid_statuses,
                order__created__gte=sixty_days_ago,
                product=product
            )
            
            for item in recent_same_clubs:
                current_date = item.order.created
                if 'grand' in item.product.name.lower():
                    if current_date.month == 12:
                        nm, ny = 1, current_date.year + 1
                    else:
                        nm, ny = current_date.month + 1, current_date.year
                    last_day = calendar.monthrange(ny, nm)[1]
                    exp_date = current_date.replace(year=ny, month=nm, day=last_day, hour=23, minute=59)
                else:
                    exp_date = current_date + timedelta(days=30)
                
                if (exp_date - timezone.now()).days >= 0:
                    msg = f'Você já possui uma assinatura ativa do {product.name}!'
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json'):
                        return JsonResponse({'success': False, 'message': msg})
                    from django.contrib import messages
                    messages.error(request, msg)
                    referer = request.META.get('HTTP_REFERER')
                    return redirect(referer) if referer else redirect('produtos:lista')
                    
    # Stock verification
    if not request.user.is_superuser:
        if product.stock < quantity:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json'):
                return JsonResponse({
                    'success': False, 
                    'message': f'Desculpe, {product.name} está esgotado ou sem estoque suficiente.'
                })
            from django.contrib import messages
            messages.error(request, f'Desculpe, {product.name} está esgotado ou sem estoque suficiente.')
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
            return redirect('produtos:lista')

    carrinho.add(product=product, quantity=quantity, metadata=metadata)
    
    # Check for AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json'):
        return JsonResponse({
            'success': True, 
            'message': f'{product.name} adicionado ao carrinho! 🧁',
            'cart_quantity': len(carrinho)
        })
        
    from django.contrib import messages
    messages.success(request, f'{product.name} adicionado ao carrinho! 🧁')
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('produtos:lista')

@require_POST
def cart_remove(request, item_key):
    carrinho = Cart(request)
    product_id = item_key.split('_')[0]
    product = get_object_or_404(Product, id=product_id)
    carrinho.remove(product, item_key=item_key)
    
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json')
    if is_ajax:
        return JsonResponse({
            'success': True,
            'cart_quantity': len(carrinho),
            'cart_total': carrinho.get_total_price_display(),
            'cart_total_after_discount': f"{carrinho.get_total_price_after_discount():.2f}".replace('.', ','),
            'discount': f"{carrinho.get_discount():.2f}".replace('.', ',')
        })
        
    return redirect('carrinho:cart_detail')

@require_POST
def cart_update(request, item_key):
    carrinho = Cart(request)
    product_id = item_key.split('_')[0]
    product = get_object_or_404(Product, id=product_id)
    action = request.POST.get('action')
    
    item = carrinho.carrinho.get(item_key, {})
    current_qty = item.get('quantity', 0)
    
    if action == 'increase':
        carrinho.update_quantity(product=product, item_key=item_key, quantity=current_qty + 1)
    elif action == 'decrease':
        if current_qty > 1:
            carrinho.update_quantity(product=product, item_key=item_key, quantity=current_qty - 1)
        else:
            carrinho.remove(product, item_key=item_key)
            
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json')
    if is_ajax:
        # Calculate new item state
        new_item = carrinho.carrinho.get(item_key, {})
        new_qty = new_item.get('quantity', 0)
        item_price = new_item.get('price', 0)
        item_total = float(item_price) * new_qty
        
        return JsonResponse({
            'success': True,
            'cart_quantity': len(carrinho),
            'item_quantity': new_qty,
            'item_total': f"{item_total:.2f}".replace('.', ','),
            'cart_total': carrinho.get_total_price_display(),
            'cart_total_after_discount': f"{carrinho.get_total_price_after_discount():.2f}".replace('.', ','),
            'discount': f"{carrinho.get_discount():.2f}".replace('.', ',')
        })
            
    return redirect('carrinho:cart_detail')

def cart_detail(request):
    carrinho = Cart(request)
    # Get IDs of products already in the cart
    cart_product_ids = [item['product'].id for item in carrinho]
    
    # Query base para todos: produtos disponíveis (ativos) e com estoque (> 0) que não estão no carrinho
    base_query = Product.objects.filter(
        available=True, 
        stock__gt=0,
        is_customizable=False
    ).exclude(
        id__in=cart_product_ids
    ).exclude(
        name__icontains="Personalizada"
    )
    
    if request.user.is_superuser:
        # Superuser: Vê TODOS os produtos da loja que possuem estoque, em ordem alfabética
        suggested_products = base_query.order_by('name')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        clients = User.objects.filter(is_superuser=False).order_by('username')
    else:
        # Clientes comuns: 3 produtos aleatórios com estoque
        suggested_products = base_query.order_by('?')[:3]
        clients = None
    
    return render(request, 'carrinho/detalhes.html', {
        'cart': carrinho, 
        'carrinho': carrinho, # for compatibility with coupon/tip logic in template
        'suggested_products': suggested_products, 
        'clients': clients
    })

from pedidos.models import Coupon
from django.utils import timezone
from django.contrib import messages

@require_POST
def coupon_apply(request):
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json')
    
    if not request.user.is_authenticated:
        msg = "Apenas usuários logados podem aplicar cupons. Faça login ou cadastre-se."
        if is_ajax:
            return JsonResponse({'success': False, 'message': msg}, status=403)
        messages.error(request, msg)
        return redirect('carrinho:cart_detail')

    now = timezone.now()
    code = request.POST.get('code')
    
    try:
        coupon = Coupon.objects.get(code__iexact=code,
                                    valid_from__lte=now,
                                    valid_to__gte=now,
                                    active=True)
        
        # 1. Check Global Usage Limit
        if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
            msg = "Este cupom atingiu o limite máximo de usos."
            if is_ajax: return JsonResponse({'success': False, 'message': msg})
            messages.error(request, msg)
            return redirect('carrinho:cart_detail')

        # 2. Check Per-User Usage (Enhanced Anti-Abuse)
        from pedidos.models import Order
        from django.db.models import Q
        
        # Check by User ID OR Phone Number
        usage_query = Q(user=request.user, coupon=coupon)
        
        if request.user.phone_number:
            usage_query = usage_query | Q(guest_phone=request.user.phone_number, coupon=coupon) | Q(user__phone_number=request.user.phone_number, coupon=coupon)
            
        if Order.objects.filter(usage_query).exists():
             msg = "Este cupom não é válido, expirou ou não existe."
             if is_ajax: return JsonResponse({'success': False, 'message': msg})
             messages.error(request, msg)
             return redirect('carrinho:cart_detail')

        # 3. Check Minimum Purchase
        carrinho = Cart(request)
        if carrinho.get_total_price() < coupon.min_purchase:
             msg = f"Este cupom requer um valor mínimo de R$ {coupon.min_purchase}."
             if is_ajax: return JsonResponse({'success': False, 'message': msg})
             messages.error(request, msg)
             return redirect('carrinho:cart_detail')

        request.session['coupon_id'] = coupon.id
        
        # Recalculate cart totals for AJAX response
        carrinho = Cart(request) # Reload to get updated coupon
        msg = f"Cupom '{coupon.code}' aplicado com sucesso! Desconto de {coupon.discount_percentage}%"
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': msg,
                'subtotal': carrinho.get_total_price(),
                'discount': carrinho.get_discount(),
                'total': carrinho.get_total_price_after_discount(),
                'coupon_code': coupon.code
            })
            
        messages.success(request, msg)
    except Coupon.DoesNotExist:
        request.session['coupon_id'] = None
        msg = "Este cupom não é válido, expirou ou não existe."
        if is_ajax: return JsonResponse({'success': False, 'message': msg})
        messages.error(request, msg)
        
    return redirect('carrinho:cart_detail')

@require_POST
def set_tip(request):
    carrinho = Cart(request)
    tip_amount = request.POST.get('tip_amount', '0.00').strip().replace(',', '.')
    if not tip_amount:
        tip_amount = '0.00'
    try:
        from decimal import Decimal
        parsed_tip = Decimal(tip_amount)
        if parsed_tip < Decimal('0.00'):
            parsed_tip = Decimal('0.00')
        carrinho.set_tip(parsed_tip)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json')
        if is_ajax:
            return JsonResponse({
                'success': True,
                'cart_total': carrinho.get_total_price_display(),
                'cart_total_after_discount': f"{carrinho.get_total_price_after_discount():.2f}".replace('.', ','),
                'discount': f"{carrinho.get_discount():.2f}".replace('.', ','),
                'tip': f"{carrinho.get_tip():.2f}".replace('.', ',')
            })
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
             return JsonResponse({'success': False, 'error': str(e)})
    return redirect('carrinho:cart_detail')

def cart_status(request):
    """API to return current cart count and status for polling"""
    carrinho = Cart(request)
    
    # Compute a simple hash of the cart state to detect changes
    cart_state_str = "".join([f"{item['product'].id}:{item['quantity']}" for item in carrinho])
    cart_state_str += str(carrinho.get_total_price())
    cart_hash = hash(cart_state_str)

    return JsonResponse({
        'cart_count': len(carrinho),
        'cart_total': carrinho.get_total_price(),
        'cart_hash': str(cart_hash),
        'success': True
    })
