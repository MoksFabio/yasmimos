from django.shortcuts import render, redirect, get_object_or_404
from .models import Order, OrderItem, Coupon
from produtos.models import Product
from carrinho.cart import Cart
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.db.models import F, Q
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import io
import traceback
from datetime import datetime
from decimal import Decimal
from PIL import Image, ImageDraw, ImageFont
import urllib.parse
from .telegram_utils import send_telegram_message, generate_action_token
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.http import HttpResponse, JsonResponse

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if order.status != 'deleted':
        # Restore stock if the order was Shipped or Delivered (presumably stock was deducted)
        if order.status in ['shipped', 'delivered']:
            for item in order.items.all():
                item.product.stock = F('stock') + item.quantity
                item.product.save()
                
        order.status = 'deleted'
        order.save()
    else:
        # Se já estava na lixeira (deleted), executa a exclusão definitiva
        order.delete()
        
    return JsonResponse({'status': 'success'})

@login_required
@require_GET
def my_orders_poll(request):
    all_orders = request.user.pedidos.all().order_by('-created')
    active_statuses = ['pending', 'paid', 'preparing', 'ready', 'shipped']
    
    active_orders = all_orders.filter(status__in=active_statuses)
    history_orders_all = all_orders.exclude(status__in=active_statuses)
    
    context = {
        'active_orders': active_orders,
        'history_orders': history_orders_all[:5],
        'has_more_history': history_orders_all.count() > 5
    }
    return render(request, 'pedidos/parcial_meus_pedidos.html', context)

@login_required
def order_detail(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return render(request, 'pedidos/pedido_nao_encontrado.html')
    # Ensure current user owns the order, or is admin
    if not request.user.is_superuser:
        if order.user:
            if request.user != order.user:
                return redirect('usuarios:profile')
        else:
            if request.session.get('guest_order_id') != order.id:
                return redirect('usuarios:profile')
    
    return render(request, 'pedidos/detalhe.html', {'order': order})

def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        from sistema.models import StoreSettings
        if not StoreSettings.get_settings().is_open and not request.user.is_superuser:
            return render(request, 'loja_fechada.html')

        if len(cart) == 0:
            from django.contrib import messages
            messages.error(request, 'Seu carrinho está vazio. Adicione produtos antes de finalizar o pedido.')
            return redirect('carrinho:cart_detail')

        # Determine if this is a personal order or a client order (for superusers)
        order_type = request.POST.get('order_type', 'self')
        if request.user.is_superuser and order_type == 'client':
            client_user_id = request.POST.get('client_user_id')
            if client_user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(id=client_user_id, is_superuser=False)
                except User.DoesNotExist:
                    user = None
            else:
                user = None
        else:
            user = request.user if request.user.is_authenticated else None

        guest_name = request.POST.get('name', '').strip()
        guest_phone = request.POST.get('phone', '').strip()
        
        if user and not guest_name:
            guest_name = user.get_full_name() or user.username
            
        payment_method = request.POST.get('payment_method', 'pix')
        
        from sistema.models import StoreSettings
        if payment_method == 'pix' and StoreSettings.get_settings().pix_manual_enabled:
            payment_method = 'pix_manual'
            
        observations = request.POST.get('observations', '').strip()
        
        if not user and not guest_name:
            guest_name = "Visitante"

        coupon = cart.coupon
        order = Order.objects.create(
            user=user, 
            guest_name=guest_name,
            guest_phone=guest_phone,
            total_amount=cart.get_total_price_after_discount(),
            payment_method=payment_method,
            coupon=coupon,
            discount=cart.get_discount(),
            tip_amount=cart.get_tip(),
            observations=observations
        )
        
        if coupon:
            coupon.used_count += 1
            coupon.save()
        # Stock is now deducted only when status becomes 'shipped'
        for item in cart:
            OrderItem.objects.create(order=order, product=item['product'], price=item['price'], quantity=item['quantity'], metadata=item.get('metadata'))
            
        # Securing Guest Order Access
        if not request.user.is_authenticated:
            request.session['guest_order_id'] = order.id

        # Notify Push (Web)
        try:
             from sistema.utils_push import send_push_to_admins
             send_push_to_admins(
                 title="Novo Pedido!",
                 body=f"Pedido #{order.id} de R$ {order.total_amount} recebido.",
                 url="https://www.yasmimos.com.br/manage/" # Should ideally default to manage page
             )
        except Exception as e:
             print(f"Push Error: {e}")

        cart.clear()
        return redirect('pedidos:order_created', order_id=order.id)
    else:
        context = {'carrinho': cart}
        if request.user.is_superuser:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            context['clients'] = User.objects.filter(is_superuser=False).order_by('username')
        return render(request, 'pedidos/criar.html', context)

def order_created(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return render(request, 'pedidos/pedido_nao_encontrado.html')
        
    if not request.user.is_superuser:
        if order.user:
            if request.user != order.user:
                return render(request, 'pedidos/pedido_nao_encontrado.html')
        else:
            if request.session.get('guest_order_id') != order.id:
                return render(request, 'pedidos/pedido_nao_encontrado.html')
    
    try:
        # Mercado Pago Integration
        from .mp_utils import create_pix_payment
        
        pix_copia_cola = None
        qr_code_base64 = None
        
        from sistema.models import StoreSettings
        store_settings = StoreSettings.get_settings()
        
        if order.payment_method == 'point':
            # Generate Deep Link for Point Mini NFC 2
            # https://www.mercadopago.com.br/developers/pt/docs/your-integrations/point/integrations-api/integrate-app
            

            callback = "https://www.yasmimos.com.br/pedidos/created/" + str(order.id) + "/"
            
            # Construct parameters dict and encode
            # Revert to https (Universal Link) but REMOVE callback_url for testing
            # If callback is causing the "bounce back", removing it should keep App open.
            params = {
                'amount': str(order.total_amount),
                'description': f"Pedido {order.id}",
                'external_reference': str(order.id),
                'notification_url': "https://www.yasmimos.com.br/pedidos/webhook/",
                'payer_email': "email@email.com",
            }
            query_string = urllib.parse.urlencode(params)
            
            # Back to HTTPS (Universal Link)
            # We removed callback_url. Now it should open App or Web Page.
            # If Web Page opens, user can click "Open App".
            deep_link = f"https://www.mercadopago.com.br/point/integrations?{query_string}"
            
            return render(request, 'pedidos/criado.html', {
                'order': order,
                'deep_link': deep_link,
                'is_point_payment': True,
                'store_settings': store_settings
            })

        is_manual_pix = order.payment_method == 'pix_manual' or order.mercado_pago_status == 'pending_manual'



        if is_manual_pix:
            if order.payment_method != 'pix_manual':
                order.payment_method = 'pix_manual'
                order.save()
            # Generate Manual BR Code (Pix Copia e Cola)
            from .pix_utils import PixPayload
            import re
            
            raw_key = store_settings.pix_key.strip()
            
            if '@' in raw_key:
                clean_key = raw_key
            elif len(raw_key) > 30 and '-' in raw_key: 
                clean_key = raw_key
            else:
                digits_only = re.sub(r'\D', '', raw_key)
                is_likely_phone = False
                if raw_key.startswith('+') or ('(' in raw_key and ')' in raw_key) or (len(digits_only) == 11 and digits_only[2] == '9'):
                    is_likely_phone = True
                
                if is_likely_phone:
                    clean_key = f"+55{digits_only}" if not digits_only.startswith('55') else f"+{digits_only}"
                else:
                    clean_key = digits_only

            pix_gen = PixPayload(key=clean_key, name="YASMIM P F NASCIMENTO", city="RECIFE", amount=order.total_amount, order_id=order.id)
            pix_copia_cola = pix_gen.get_payload()
            qr_code_base64 = None 
            order.mercado_pago_status = 'pending_manual'
            order.save()
        else:
            # Check if token exists for the selected account
            access_token = settings.MERCADOPAGO_ACCESS_TOKEN
            if store_settings.mp_active_account == 'fabio' and store_settings.mp_access_token_fabio:
                access_token = store_settings.mp_access_token_fabio
            elif store_settings.mp_active_account == 'yasmim' and store_settings.mp_access_token_yasmim:
                access_token = store_settings.mp_access_token_yasmim
            
            if not access_token or len(access_token) < 10:
                return HttpResponse(f"<h1>Erro de Configuração</h1><p>O token do Mercado Pago para a conta <b>{store_settings.mp_active_account}</b> não foi configurado no painel administrativo.</p>", status=400)

            # SWITCH ACCOUNT LOGIC: If account changed, reset MP ID to generate new one for correct person
            if order.mercado_pago_id and order.mp_beneficiary != store_settings.mp_active_account and order.status == 'pending':
                order.mercado_pago_id = None
                order.mercado_pago_status = None
                order.save()

            if not order.mercado_pago_id:
                try:
                    payment = create_pix_payment(order)
                    
                    mp_status = payment.get('status')
                    
                    # Se status for approved ou pending (200, 201 etc)
                    if mp_status and mp_status != 400 and mp_status != 404: 
                        order.mercado_pago_id = str(payment.get('id'))
                        order.mercado_pago_status = payment.get('status')
                        order.mp_beneficiary = store_settings.mp_active_account # Mark who received it
                        order.save()
                        
                        point = payment.get('point_of_interaction', {}).get('transaction_data', {})
                        pix_copia_cola = point.get('qr_code')
                        qr_code_base64 = point.get('qr_code_base64')
                    else:
                         print(f"Erro ao criar Pix MP: {mp_status}")
                except Exception as e:
                    print(f"Erro Pix MP: {e}")
                    pass
            else:
                # Se ja tem ID, recupera o Status atualizado
                import mercadopago 
                
                # Use THE SAME token logic as mp_utils.py to ensure we check the correct account
                access_token = settings.MERCADOPAGO_ACCESS_TOKEN # Default backup
                if store_settings.mp_active_account == 'fabio' and store_settings.mp_access_token_fabio:
                    access_token = store_settings.mp_access_token_fabio
                elif store_settings.mp_active_account == 'yasmim' and store_settings.mp_access_token_yasmim:
                    access_token = store_settings.mp_access_token_yasmim
                
                sdk = mercadopago.SDK(access_token)
                try:
                    payment_info = sdk.payment().get(str(order.mercado_pago_id))
                    if payment_info["status"] == 200:
                        payment = payment_info["response"]
                        
                        # SELF-HEALING: If paid via MP but webhook failed, update here!
                        current_status = payment.get('status')
                        if current_status == 'approved' and order.status == 'pending':
                            order.status = 'paid'
                            order.mercado_pago_status = current_status
                            order.save()
                            # Redirect to same page to trigger "Paid" view logic
                            return redirect('pedidos:order_created', order_id=order.id)
                        
                        point = payment.get('point_of_interaction', {}).get('transaction_data', {})
                        pix_copia_cola = point.get('qr_code')
                        qr_code_base64 = point.get('qr_code_base64')
                except Exception as e:
                     print(f"Erro ao recuperar status MP: {e}")

        # Determine Beneficiary Name for Automatic Pix (MP) based on ORDER info (or settings if new)
        beneficiary_name = None
        current_beneficiary = order.mp_beneficiary or store_settings.mp_active_account
        
        if not is_manual_pix:
             if current_beneficiary == 'yasmim':
                  beneficiary_name = "YASMIM POLIANA FRANÇA NASCIMENTO"
             elif current_beneficiary == 'fabio':
                  beneficiary_name = "FÁBIO SILVA DE LIMA"
             else:
                  beneficiary_name = "YASMIM POLIANA FRANÇA NASCIMENTO" # Default fallback
        else:
             # Manual Pix Beneficiary (Used for manual mode context if needed)
             beneficiary_name = "YASMIM P F NASCIMENTO"

        # Message for WhatsApp receipt sending
        if is_manual_pix:
            message = f"Olá Yasmim! Realizei o pagamento do pedido #{order.id} via Pix Manual.\n"
        else:
            message = f"Olá Yasmim! O pedido #{order.id} foi pago via Pix Automático (Mercado Pago).\n"
        message += f"Total: R$ {order.total_amount}"
        whatsapp_url = f"https://wa.me/5581983964906?text={urllib.parse.quote(message)}"
        
        return render(request, 'pedidos/criado.html', {
            'order': order, 
            'pix_copia_cola': pix_copia_cola,
            'qr_code_base64': qr_code_base64,
            'whatsapp_url': whatsapp_url,
            'store_settings': store_settings,
            'is_manual_pix': is_manual_pix,
            'beneficiary_name': beneficiary_name
        })
    except Exception as e:
        import traceback
        return HttpResponse(f"<h1>Erro Interno (Debug)</h1><pre>{traceback.format_exc()}</pre>", status=500)

def check_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if not request.user.is_superuser:
        if order.user:
            if request.user != order.user:
                return JsonResponse({'error': 'Not found'}, status=404)
        else:
            if request.session.get('guest_order_id') != order.id:
                return JsonResponse({'error': 'Not found'}, status=404)
    
    # Active Polling: If pending, verify directly with MP (Bypasses delayed Webhooks)
    if order.status == 'pending' and order.mercado_pago_id:
        try:
            from sistema.models import StoreSettings
            from django.conf import settings
            import mercadopago
            
            store_settings = StoreSettings.get_settings()
            
            # Select correct token (Fabio or Yasmim)
            access_token = settings.MERCADOPAGO_ACCESS_TOKEN
            if store_settings.mp_active_account == 'fabio' and store_settings.mp_access_token_fabio:
                access_token = store_settings.mp_access_token_fabio
            elif store_settings.mp_active_account == 'yasmim' and store_settings.mp_access_token_yasmim:
                access_token = store_settings.mp_access_token_yasmim
                
            sdk = mercadopago.SDK(access_token)
            
            payment_info = sdk.payment().get(str(order.mercado_pago_id))
            if payment_info["status"] == 200:
                mp_status = payment_info["response"]["status"]
                if mp_status == 'approved':
                    order.status = 'paid'
                    order.mercado_pago_status = mp_status
                    order.save()
        except Exception as e:
            print(f"Polling Check Error: {e}")
            pass

    return JsonResponse({'status': order.status})

@user_passes_test(lambda u: u.is_superuser)
def order_list_api(request):
    orders = Order.objects.all().order_by('-created')
    return render(request, 'pedidos/parcial_lista_pedidos.html', {'orders': orders})

# --- GERAÇÃO DO COMPROVANTE (PILLOW) ---

from playwright.sync_api import sync_playwright
import io
from django.http import HttpResponse

@require_GET
def order_receipt_image(request, order_id):
    import os
    bot_token = request.GET.get('bot_token')
    valid_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', os.environ.get('TELEGRAM_BOT_TOKEN', ''))
    if not request.user.is_superuser and (not bot_token or bot_token != valid_token):
        return HttpResponse("Acesso negado", status=403)

    order = get_object_or_404(Order, id=order_id)
    
    # URL interna especial que renderiza o HTML já formatado para print
    url = request.build_absolute_uri(f'/pedidos/receipt-html/{order.id}/?bot_token={bot_token}')
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
            page = browser.new_page()
            
            # Vai para a URL interna escondida
            page.goto(url, wait_until='networkidle')
            
            # Pega o elemento do card
            card = page.locator('.premium-receipt-card')
            screenshot_bytes = card.screenshot(type='png')
            
            browser.close()
            
        return HttpResponse(screenshot_bytes, content_type="image/png")
    except Exception as e:
        import traceback
        print(f"Erro ao gerar print com Playwright: {e}")
        # Retorna imagem vazia ou erro 500 se o Playwright falhar
        return HttpResponse(status=500)

@require_GET
def receipt_html_for_bot(request, order_id):
    import os
    bot_token = request.GET.get('bot_token')
    valid_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', os.environ.get('TELEGRAM_BOT_TOKEN', ''))
    
    if not request.user.is_superuser and (not bot_token or bot_token != valid_token):
        return HttpResponse("Acesso negado", status=403)

    order = get_object_or_404(Order, id=order_id)
    # Renderiza o HTML dizendo que é para o bot (oculta barras, força paisagem)
    return render(request, 'pedidos/detalhe.html', {'order': order, 'is_bot_print': True})


# Removed duplicate import here

from produtos.models import Product

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
                if item.product:
                    # Se o produto for "Caixinha da Felicidade (Personalizada)", não abaixa estoque
                    is_personalized_box = "Personalizada" in item.product.name or item.product.is_customizable
                    
                    if not is_personalized_box:
                        if item.product.stock >= item.quantity:
                            item.product.stock -= item.quantity
                        else:
                            item.product.stock = 0
                        item.product.save()
                    
        elif is_restoring:
            for item in order.items.all():
                if item.product:
                    is_personalized_box = "Personalizada" in item.product.name or item.product.is_customizable
                    if not is_personalized_box:
                        item.product.stock += item.quantity
                        item.product.save()

        order.status = new_status
        order.save()

        # Custom logic for "Preparing" - Create Chat Message for registered users
        if new_status == 'preparing' and order.user:
            try:
                from chat.models import ChatSession, Message
                from django.utils import timezone
                
                session, created = ChatSession.objects.get_or_create(
                    client=order.user,
                    topic='Dúvida sobre um Pedido',
                    status='ACTIVE'
                )
                
                msg_content = f"📦 Atualização do seu Pedido #{order.id}: Suas caixinhas personalizadas entraram em produção AGORA! 👩‍🍳✨ Você pode acompanhar o progresso em tempo real na seção 'Minha Conta'."
                
                # Avoid duplicate messages if already sent recently for this order
                last_msg = Message.objects.filter(session=session, content__contains=f"Pedido #{order.id}").first()
                if not last_msg or (timezone.now() - last_msg.timestamp).seconds > 60:
                    Message.objects.create(
                        session=session,
                        sender=request.user,
                        content=msg_content
                    )
                    
                    # Notify via WebSockets
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'chat_{session.id}',
                        {
                            'type': 'chat_message',
                            'message': msg_content,
                            'sender': request.user.username,
                            'timestamp': timezone.now().strftime('%H:%M')
                        }
                    )
            except Exception as e:
                print(f"Chat Notification Error: {e}")

        # Custom logic for "Ready" - Create Chat Message for registered users
        if new_status == 'ready' and order.user:
            try:
                from chat.models import ChatSession, Message
                from django.utils import timezone
                
                session, created = ChatSession.objects.get_or_create(
                    client=order.user,
                    topic='Dúvida sobre um Pedido',
                    status='ACTIVE'
                )
                
                msg_content = f"✅ Boas notícias! Seu Pedido #{order.id} está PRONTO! 🎁✨ Você já pode acompanhar os detalhes e retirar seu pedido. Veja o status atualizado em 'Minha Conta'."
                
                Message.objects.create(
                    session=session,
                    sender=request.user,
                    content=msg_content
                )
                
                # Notify via WebSockets
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'chat_{session.id}',
                    {
                        'type': 'chat_message',
                        'message': msg_content,
                        'sender': request.user.username,
                        'timestamp': timezone.now().strftime('%H:%M')
                    }
                )
            except Exception as e:
                print(f"Chat Notification Error: {e}")

    return JsonResponse({'status': 'success', 'new_status': new_status})

from django.db import connection

@user_passes_test(lambda u: u.is_superuser)
def clear_all_orders(request):
    # Restore stock for all shipped/delivered orders before clearing
    orders = Order.objects.all()
    for order in orders:
        if order.status in ['shipped', 'delivered']:
             for item in order.items.all():
                item.product.stock = F('stock') + item.quantity
                item.product.save()

    orders.delete()
    
    # Reset AutoIncrement Sequence based on database engine
    with connection.cursor() as cursor:
        if connection.vendor == 'sqlite':
            # Reset SQLite
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='pedidos_order';")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='pedidos_orderitem';")
        elif connection.vendor == 'postgresql':
            # Reset PostgreSQL
            cursor.execute("ALTER SEQUENCE pedidos_order_id_seq RESTART WITH 1;")
            cursor.execute("ALTER SEQUENCE pedidos_orderitem_id_seq RESTART WITH 1;")
        
    return JsonResponse({'success': True})

from .models import Coupon
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime
from decimal import Decimal

@user_passes_test(lambda u: u.is_superuser)
def manage_coupons(request):
    return render(request, 'pedidos/gerenciar_cupons.html')

@user_passes_test(lambda u: u.is_superuser)
def api_list_coupons(request):
    coupons = Coupon.objects.all().order_by('-valid_to')
    data = []
    for c in coupons:
        data.append({
            'id': c.id,
            'code': c.code,
            'discount': float(c.discount_percentage),
            'valid_from': c.valid_from.strftime('%Y-%m-%d'),
            'valid_to': c.valid_to.strftime('%Y-%m-%d'),
            'active': c.active,
            'min_purchase': float(c.min_purchase),
            'max_uses': c.max_uses,
            'used_count': c.used_count
        })
    return JsonResponse({'coupons': data})

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def api_add_coupon(request):
    data = json.loads(request.body)
    try:
        from django.utils.timezone import make_aware
        
        valid_from = datetime.strptime(data['valid_from'], '%Y-%m-%d')
        valid_to = datetime.strptime(data['valid_to'], '%Y-%m-%d')
        
        # Set valid_to to end of day (23:59:59)
        valid_to = valid_to.replace(hour=23, minute=59, second=59)

        # Basic validation
        if valid_from > valid_to:
            return JsonResponse({'success': False, 'error': 'A data de início não pode ser maior que a data de fim.'})

        # Make aware
        try:
            valid_from = make_aware(valid_from)
            valid_to = make_aware(valid_to)
        except:
            pass
        
        max_uses_val = data.get('max_uses')
        if max_uses_val == '': max_uses_val = None

        Coupon.objects.create(
            code=data['code'].upper(),
            discount_percentage=Decimal(data['discount']),
            valid_from=valid_from,
            valid_to=valid_to,
            active=True,
            min_purchase=data.get('min_purchase') or 0,
            max_uses=max_uses_val
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["DELETE"])
def api_delete_coupon(request, coupon_id):
    c = get_object_or_404(Coupon, id=coupon_id)
    c.delete()
    return JsonResponse({'success': True})

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def api_toggle_coupon(request, coupon_id):
    c = get_object_or_404(Coupon, id=coupon_id)
    c.active = not c.active
    c.save()
    return JsonResponse({'success': True})

@csrf_exempt
def mp_webhook(request):
    if request.method == 'POST':
        try:
            # MP can send data in GET params or Body
            topic = request.GET.get('topic') or request.GET.get('type')
            p_id = request.GET.get('id') or request.GET.get('data.id')

            # We only care about payments
            if topic == 'payment' or topic == 'merchant_order':
                import mercadopago
                from sistema.models import StoreSettings
                store_settings = StoreSettings.get_settings()
                
                # Use correct token based on who received the payment (if we can tell) or current active
                access_token = settings.MERCADOPAGO_ACCESS_TOKEN
                if store_settings.mp_active_account == 'fabio' and store_settings.mp_access_token_fabio:
                    access_token = store_settings.mp_access_token_fabio
                elif store_settings.mp_active_account == 'yasmim' and store_settings.mp_access_token_yasmim:
                    access_token = store_settings.mp_access_token_yasmim

                sdk = mercadopago.SDK(access_token)
                payment_info = sdk.payment().get(str(p_id))
                
                if payment_info["status"] == 200:
                    payment = payment_info['response']
                    status = payment.get('status')
                    
                    # Search by MP ID (Most reliable)
                    order = Order.objects.filter(mercado_pago_id=str(p_id)).first()
                    
                    if not order:
                        # Fallback: Search by external_reference if set
                        ext_ref = payment.get('external_reference')
                        if ext_ref:
                            order = Order.objects.filter(id=ext_ref).first()

                    if order:
                        order.mercado_pago_status = status
                        if status == 'approved' and order.status == 'pending':
                            order.status = 'paid'
                            order.save()
                            
                            # NOTIFY TELEGRAM
                            try:
                                from .telegram_utils import send_telegram_message
                                msg = (
                                    f"✅ *PAGAMENTO CONFIRMADO!* 💰\n\n"
                                    f"O Pedido *#{order.id}* foi pago via Pix Automático.\n\n"
                                    f"👤 Cliente: {order.guest_name}\n"
                                    f"💲 Valor: R$ {order.total_amount}\n"
                                    f"📱 Conta: {order.mp_beneficiary.upper() if order.mp_beneficiary else 'PADRÃO'}"
                                )
                                send_telegram_message(msg)
                            except: pass
                        else:
                            order.save()

            return HttpResponse(status=200)
        except Exception as e:
            print(f"Webhook Error: {e}")
            return HttpResponse(status=200) # Always 200 to MP
    return HttpResponse(status=200)

@user_passes_test(lambda u: u.is_superuser)
def global_order_search(request):
    query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'recent')
    filter_type = request.GET.get('filter', 'all')
    
    orders = Order.objects.all()
    from django.db.models import Q
    
    if query:
        orders = orders.filter(
            Q(id__icontains=query) |
            Q(guest_name__icontains=query) |
            Q(guest_phone__icontains=query) |
            Q(user__username__icontains=query) |
            Q(items__product__name__icontains=query)
        ).distinct()
        
    if filter_type == 'paid':
        orders = orders.filter(status__in=['paid', 'preparing', 'ready', 'shipped', 'delivered', 'completed'])
    elif filter_type == 'pending':
        orders = orders.filter(status='pending')
        
    if sort_by == 'price_desc':
        orders = orders.order_by('-total_amount', '-created')
    elif sort_by == 'price_asc':
        orders = orders.order_by('total_amount', '-created')
    elif sort_by == 'oldest':
        orders = orders.order_by('created')
    else:
        orders = orders.order_by('-created')
        
    limit = request.GET.get('limit', '50')
    if limit != 'all':
        try:
            orders = orders[:int(limit)]
        except:
            orders = orders[:50]
        
    return render(request, 'pedidos/parcial_lista_pedidos.html', {'orders': orders})