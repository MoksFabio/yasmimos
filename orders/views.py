from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from .models import Order, OrderItem
from cart.cart import Cart
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
import urllib.parse

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Restore stock if the order was Shipped or Delivered (presumably stock was deducted)
    if order.status in ['shipped', 'delivered']:
        for item in order.items.all():
            item.product.stock += item.quantity
            item.product.save()
            
    order.delete()
    return JsonResponse({'status': 'success'})

def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        from core.models import StoreSettings
        if not StoreSettings.get_settings().is_open and not request.user.is_superuser:
            return redirect('cart:cart_detail') # Or some error page

        user = request.user if request.user.is_authenticated else None
        guest_name = request.POST.get('name')
        guest_phone = request.POST.get('phone')
        
        if not user and (not guest_name or not guest_phone):
             # Should handle error, but assuming frontend validation for now
             pass

        order = Order.objects.create(
            user=user, 
            guest_name=guest_name,
            guest_phone=guest_phone,
            total_amount=cart.get_total_price()
        )
        # Stock is now deducted only when status becomes 'shipped'
        for item in cart:
            OrderItem.objects.create(order=order, product=item['product'], price=item['price'], quantity=item['quantity'])
            
        cart.clear()
        return redirect('orders:order_created', order_id=order.id)
    else:
        return render(request, 'pedidos/criar.html', {'cart': cart})

def order_created(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Generate Pix Payload
    from .utils import PixPayload
    pix = PixPayload(
        key=settings.PIX_KEY, 
        name=settings.PIX_NAME, 
        city=settings.PIX_CITY, 
        amount=float(order.total_amount), 
        txt_id="***"
    )
    pix_copia_cola = pix.generate_payload()
    
    # Message for WhatsApp receipt sending
    message = f"Olá Yasmim! Acabei de fazer o pagamento do pedido #{order.id}.\n"
    message += f"Total: R$ {order.total_amount}\nSegue o comprovante:"
    whatsapp_url = f"https://wa.me/5581984086846?text={urllib.parse.quote(message)}"
    
    return render(request, 'pedidos/criado.html', {
        'order': order, 
        'pix_copia_cola': pix_copia_cola,
        'whatsapp_url': whatsapp_url
    })

def check_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return JsonResponse({'status': order.status})

@user_passes_test(lambda u: u.is_superuser)
def order_list_api(request):
    orders = Order.objects.all().order_by('-created')
    return render(request, 'pedidos/parcial_lista_pedidos.html', {'orders': orders})

# Removed duplicate import here

@user_passes_test(lambda u: u.is_superuser)
def update_order_status(request, order_id, new_status):
    order = get_object_or_404(Order, id=order_id)
    if new_status in dict(Order.STATUS_CHOICES):
        # 1. Deduct Stock: When changing to 'shipped' from a non-shipped status
        
        old_status = order.status
        is_shipping = new_status == 'shipped' and old_status != 'shipped'
        is_restoring = old_status == 'shipped' and new_status in ['cancelled', 'refunded']
        
        if is_shipping:
            for item in order.items.all():
                if item.product.stock >= item.quantity:
                    item.product.stock -= item.quantity
                    item.product.save()
                else:
                    # Stock insufficient but admin is forcing it. 
                    item.product.stock -= item.quantity
                    item.product.save()
                    
        elif is_restoring:
            for item in order.items.all():
                item.product.stock += item.quantity
                item.product.save()

        order.status = new_status
        order.save()
    return JsonResponse({'status': 'success', 'new_status': new_status})

from django.db import connection

@user_passes_test(lambda u: u.is_superuser)
def clear_all_orders(request):
    # Restore stock for all shipped/delivered orders before clearing
    orders = Order.objects.all()
    for order in orders:
        if order.status in ['shipped', 'delivered']:
             for item in order.items.all():
                item.product.stock += item.quantity
                item.product.save()

    orders.delete()
    
    # Reset SQLite AutoIncrement Sequence
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='orders_order';")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='orders_orderitem';")
        
    return redirect('products:manage_products')
