from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from .models import Order, OrderItem
from produtos.models import Product
import json

@user_passes_test(lambda u: u.is_superuser)
def edit_order_modal(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    products = Product.objects.filter(available=True)
    
    context = {
        'order': order,
        'produtos': products,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'pedidos/modal_editar_pedido.html', context)

@user_passes_test(lambda u: u.is_superuser)
def save_edited_order(request, order_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método inválido.'})
        
    try:
        from django.db.models import F
        order = get_object_or_404(Order, id=order_id)
        data = json.loads(request.body)
        
        old_status = order.status
        
        # RESTORE STOCK if old_status meant stock was previously deducted
        is_returning_stock = old_status in ['shipped', 'delivered']
        if is_returning_stock:
            for item in order.items.all():
                if item.product:
                    item.product.stock = F('stock') + item.quantity
                    item.product.save()

                    # RESTORE Bundle components
                    for bundle_item in item.product.bundle_items.all():
                        bundle_sub = bundle_item.sub_product
                        bundle_sub.stock = F('stock') + (bundle_item.quantity * item.quantity)
                        bundle_sub.save()

                if item.metadata and 'items' in item.metadata:
                    for sub_item in item.metadata['items']:
                        try:
                            sub_prod = Product.objects.get(id=sub_item['id'])
                            sub_prod.stock = F('stock') + (int(sub_item['quantity']) * item.quantity)
                            sub_prod.save()
                        except: pass

        # Edit Basic Info
        order.guest_name = data.get('guest_name', order.guest_name)
        order.guest_phone = data.get('guest_phone', order.guest_phone)
        order.payment_method = data.get('payment_method', order.payment_method)
        order.status = data.get('status', order.status)
        order.observations = data.get('observations', order.observations)
        
        tip = data.get('tip_amount')
        if tip is not None:
            order.tip_amount = float(tip)
            
        items_data = data.get('items', [])
        
        existing_item_ids = [item.id for item in order.items.all()]
        submitted_item_ids = [int(i['id']) for i in items_data if str(i.get('id')).isdigit()]
        
        # Remove items not in the submitted list
        for old_item_id in existing_item_ids:
            if old_item_id not in submitted_item_ids:
                OrderItem.objects.filter(id=old_item_id).delete()
                
        # Subtotal Tracker
        new_total_amount = 0
                
        for i_data in items_data:
            item_id = str(i_data.get('id'))
            prod_id = i_data.get('product_id')
            qty = int(i_data.get('quantity', 1))
            price = float(i_data.get('price', 0))
            
            product = None
            if prod_id:
                try: product = Product.objects.get(id=prod_id)
                except: pass
                
            if item_id.isdigit():
                # Edit Existing
                item = OrderItem.objects.filter(id=int(item_id)).first()
                if item:
                    if product: item.product = product
                    item.quantity = qty
                    item.price = price
                    item.save()
                    new_total_amount += (item.price * item.quantity)
            else:
                # Add New Item
                if product:
                    new_item = OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=qty,
                        price=price
                    )
                    new_total_amount += (new_item.price * new_item.quantity)
                    
        # Apply Discount and Tip
        new_total_amount += float(order.tip_amount)
        if order.discount:
            new_total_amount -= float(order.discount)
            
        old_total = order.total_amount
        order.total_amount = new_total_amount
        order.save()
        
        # --- ATUALIZAÇÃO AUTOMÁTICA DO MERCADO PAGO ---
        # Se o pedido continuar pendente e for Pix Automático, refaz a cobrança se o valor mudou
        if order.status == 'pending' and order.mercado_pago_id and str(order.payment_method) not in ['pix_manual', 'cash', 'card']:
            if float(old_total) != float(new_total_amount):
                try:
                    from .mp_utils import create_pix_payment
                    payment = create_pix_payment(order)
                    mp_status = payment.get('status')
                    if mp_status and mp_status not in [400, 404]: 
                        order.mercado_pago_id = str(payment.get('id'))
                        order.mercado_pago_status = payment.get('status')
                        order.save()
                except Exception as e:
                    print(f"Erro ao refazer Pix automático na edição: {e}")
        # ---------------------------------------------
        
        # DEDUCT STOCK if new_status means stock should be deducted
        new_status = order.status
        is_deducting_stock = new_status in ['shipped', 'delivered']
        if is_deducting_stock:
            # We must refresh the relation since we added/deleted items
            for item in order.items.all():
                if item.product:
                    item.product.stock = F('stock') - item.quantity
                    item.product.save()

                    # DEDUCT Bundle components
                    for bundle_item in item.product.bundle_items.all():
                        bundle_sub = bundle_item.sub_product
                        bundle_sub.stock = F('stock') - (bundle_item.quantity * item.quantity)
                        bundle_sub.save()

                if item.metadata and 'items' in item.metadata:
                    for sub_item in item.metadata['items']:
                        try:
                            sub_prod = Product.objects.get(id=sub_item['id'])
                            sub_prod.stock = F('stock') - (int(sub_item['quantity']) * item.quantity)
                            sub_prod.save()
                        except: pass
        
        return JsonResponse({'status': 'success', 'message': 'Pedido atualizado com sucesso!'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
