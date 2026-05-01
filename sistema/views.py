from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from .models import StoreSettings, PushSubscription
import pandas as pd
from django.http import HttpResponse
from io import BytesIO

from django.utils import timezone

# NOT IFICATION KEYS (Should be env vars in production)
# Generated via pywebpush
VAPID_PUBLIC_KEY = "BIsE_3a2YlhDY-Mf6l1k6Du54kKPsJTxHvNc6-N9mAhlMgz2GgC-m55J-4f1t9N9f7Y5t8X5q7Z5w7y5x7z5Q" # DUMMY PLACEHOLDER adjusted from output
VAPID_PRIVATE_KEY = "..." # Do not hardcode private key in view if possible, but for this step we might need to.

def get_store_status(request):
    settings = StoreSettings.get_settings()
    
    last_update_str = None
    if settings.last_gps_update:
        local_dt = timezone.localtime(settings.last_gps_update)
        last_update_str = local_dt.strftime('%H:%M:%S')

    response_data = {
        'is_open': settings.is_open,
        'notice': settings.delivery_notice,
        'details': settings.delivery_details,
        'gps_enabled': settings.gps_enabled,
        'latitude': settings.latitude,
        'longitude': settings.longitude,
        'last_update': last_update_str,
        'pix_manual_enabled': settings.pix_manual_enabled
    }
    
    if request.user.is_authenticated and request.user.is_superuser:
        from chat.models import ChatSession
        response_data['has_active_chats'] = ChatSession.objects.filter(status='ACTIVE').exists()
        
        from pedidos.models import Order
        response_data['has_pending_orders'] = Order.objects.filter(status='pending').exists()
        
    return JsonResponse(response_data)

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_store_status(request):
    settings = StoreSettings.get_settings()
    settings.is_open = not settings.is_open
    settings.save()
    return JsonResponse({'status': 'success', 'is_open': settings.is_open})

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_pix_mode(request):
    settings = StoreSettings.get_settings()
    settings.pix_manual_enabled = not settings.pix_manual_enabled
    settings.save()
    return JsonResponse({'status': 'success', 'pix_manual_enabled': settings.pix_manual_enabled})

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_mp_account(request):
    import json
    try:
        data = json.loads(request.body)
        account = data.get('account') 
        if account not in ['fabio', 'yasmim']:
             return JsonResponse({'status': 'error', 'message': 'Conta inválida'}, status=400)

        settings = StoreSettings.get_settings()
        settings.mp_active_account = account
        settings.save()
        return JsonResponse({'status': 'success', 'active_account': settings.mp_active_account})
    except Exception as e:
         return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def update_mp_tokens(request):
    import json
    try:
        data = json.loads(request.body)
        token_fabio = data.get('token_fabio')
        token_yasmim = data.get('token_yasmim')
        
        settings = StoreSettings.get_settings()
        
        if token_fabio is not None:
            settings.mp_access_token_fabio = token_fabio.strip()
        
        if token_yasmim is not None:
            settings.mp_access_token_yasmim = token_yasmim.strip()
            
        settings.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def update_delivery_notice(request):
    import json
    try:
        data = json.loads(request.body)
        notice = data.get('notice')
        details = data.get('details')
        settings = StoreSettings.get_settings()
        
        if notice is not None:
            settings.delivery_notice = notice
        
        if details is not None:
            settings.delivery_details = details
            
        settings.save()
        return JsonResponse({'status': 'success', 'notice': settings.delivery_notice, 'details': settings.delivery_details})
    except:
        pass
    return JsonResponse({'status': 'error'}, status=400)

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def update_gps_location(request):
    import json
    from django.utils import timezone
    try:
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        enabled = data.get('enabled')
        
        settings = StoreSettings.get_settings()
        
        if enabled is not None:
            settings.gps_enabled = enabled
            
        if latitude is not None and longitude is not None:
            settings.latitude = float(latitude)
            settings.longitude = float(longitude)
            settings.last_gps_update = timezone.now()
            
        settings.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

from django.shortcuts import redirect

@user_passes_test(lambda u: u.is_superuser)
def update_about_photo(request):
    if request.method == 'POST' and request.FILES.get('about_photo'):
        settings = StoreSettings.get_settings()
        settings.about_photo = request.FILES['about_photo']
        settings.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))

@user_passes_test(lambda u: u.is_superuser)
def get_drawer_balance(request):
    settings = StoreSettings.get_settings()
    return JsonResponse({
        'balance': settings.cash_in_drawer,
        'breakdown': settings.cash_breakdown
    })

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def update_drawer_balance(request):
    import json
    try:
        data = json.loads(request.body)
        new_balance = data.get('balance')
        new_breakdown = data.get('breakdown')
        
        settings = StoreSettings.get_settings()
        
        if new_balance is not None:
             settings.cash_in_drawer = float(new_balance)
        
        if new_breakdown is not None:
             settings.cash_breakdown = new_breakdown
             
        settings.save()
        return JsonResponse({
            'status': 'success', 
            'balance': settings.cash_in_drawer,
            'breakdown': settings.cash_breakdown
        })
             
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)


def about_view(request):
    settings = StoreSettings.get_settings() # ensure context has settings usually base.html handles this but good to be sure
    return render(request, 'sistema/sobre.html', {'store_settings': settings})


# --- WEB PUSH LOGIC ---
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def save_subscription(request):
    import json
    try:
        data = json.loads(request.body)
        subscription_info = data.get('subscription_info')
        
        # Upsert subscription
        endpoint = subscription_info.get('endpoint')
        keys = subscription_info.get('keys', {})
        
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh': keys.get('p256dh'),
                'auth': keys.get('auth')
            }
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@user_passes_test(lambda u: u.is_superuser)
def get_vapid_public_key(request):
    return JsonResponse({'publicKey': settings.VAPID_PUBLIC_KEY})


# PWA Views
from django.conf import settings
from django.http import HttpResponse 
import os

def service_worker(request):
    filepath = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
    else:
        content = ""
    return HttpResponse(content, content_type='application/javascript')

def manifest(request):
    filepath = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
    else:
        content = "{}"
    return HttpResponse(content, content_type='application/json')

def offline_view(request):
    return render(request, 'offline.html')

def settings_view(request):
    """
    Renders the accessibility/settings page.
    """
    settings = StoreSettings.get_settings()
    return render(request, 'sistema/configuracoes.html', {'title': 'Acessibilidade', 'store_settings': settings})

@user_passes_test(lambda u: u.is_superuser)
def export_database_xlsx(request):
    # Import all models locally to avoid circular imports
    from usuarios.models import CustomUser
    from produtos.models import Product, Category
    from pedidos.models import Order, OrderItem, Coupon
    from chat.models import ChatSession, Message
    from fidelidade.models import LoyaltyCard
    from sistema.models import StoreSettings
    
    # Create an in-memory buffer
    output = BytesIO()

    def clean_df(df):
        """Excel does not support datetimes with timezones."""
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.tz_localize(None)
        return df
    
    # Generate Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 1. Users
        users = CustomUser.objects.all().values()
        if users.exists():
            df_users = pd.DataFrame(list(users))
            # Remove sensitive info
            if 'password' in df_users.columns:
                df_users.drop(columns=['password'], inplace=True)
            clean_df(df_users).to_excel(writer, sheet_name='Clientes', index=False)
            
        # 2. Products
        products = Product.objects.all().values()
        if products.exists():
            df_products = pd.DataFrame(list(products))
            clean_df(df_products).to_excel(writer, sheet_name='Produtos', index=False)
            
        categories = Category.objects.all().values()
        if categories.exists():
            df_cats = pd.DataFrame(list(categories))
            clean_df(df_cats).to_excel(writer, sheet_name='Categorias', index=False)
            
        # 3. Orders
        orders = Order.objects.all().values()
        if orders.exists():
            df_orders = pd.DataFrame(list(orders))
            clean_df(df_orders).to_excel(writer, sheet_name='Pedidos', index=False)
            
        items = OrderItem.objects.all().values()
        if items.exists():
            df_items = pd.DataFrame(list(items))
            clean_df(df_items).to_excel(writer, sheet_name='Itens de Pedido', index=False)
            
        coupons = Coupon.objects.all().values()
        if coupons.exists():
            df_coupons = pd.DataFrame(list(coupons))
            clean_df(df_coupons).to_excel(writer, sheet_name='Cupons', index=False)
            
        # 4. Chat
        sessions = ChatSession.objects.all().values()
        if sessions.exists():
            df_sessions = pd.DataFrame(list(sessions))
            clean_df(df_sessions).to_excel(writer, sheet_name='Sessões de Chat', index=False)
            
        messages = Message.objects.all().values()
        if messages.exists():
            df_messages = pd.DataFrame(list(messages))
            clean_df(df_messages).to_excel(writer, sheet_name='Mensagens', index=False)
            
        # 5. Fidelity
        fidelity = LoyaltyCard.objects.all().values()
        if fidelity.exists():
            df_fidelity = pd.DataFrame(list(fidelity))
            clean_df(df_fidelity).to_excel(writer, sheet_name='Cartões Fidelidade', index=False)
            
        # 6. Settings
        settings_data = StoreSettings.objects.all().values()
        if settings_data.exists():
            df_settings = pd.DataFrame(list(settings_data))
            clean_df(df_settings).to_excel(writer, sheet_name='Configurações', index=False)

    # Prepare response
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=yasmimos_backup_{timezone.now().strftime("%Y-%m-%d")}.xlsx'
    return response


# --- API PARA O ROBÔ DO WHATSAPP ---
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def bot_store_info(request):
    settings = StoreSettings.get_settings()
    from produtos.models import Category
    cats = list(Category.objects.values('name', 'slug'))
    
    # Se estiver fechado, usamos o aviso padrão do site.
    # Se estiver aberto, usamos o local cadastrado no banco.
    notice = settings.delivery_notice if settings.is_open else "Voltamos em breve! (Ter, Qui e Sex)"
    details = settings.delivery_details if settings.is_open else ""

    return JsonResponse({
        'is_open': settings.is_open,
        'notice': notice,
        'details': details,
        'categories': cats
    })

@csrf_exempt
def bot_order_status(request, order_id):
    from pedidos.models import Order
    try:
        order = Order.objects.get(id=order_id)
        
        status_map = {
            'pending': 'Aguardando Pagamento ⏳',
            'paid': 'Pago! Na fila de preparo 💰',
            'preparing': 'Em Preparo 👩‍🍳',
            'ready': 'Pronto para Retirada 🎁',
            'shipped': 'Saiu para Entrega 🛵',
            'delivered': 'Entregue ✅',
            'cancelled': 'Cancelado ❌',
            'refunded': 'Reembolsado 💸',
            'deleted': 'Deletado 🗑️'
        }
        
        return JsonResponse({
            'status': 'success',
            'order_id': order.id,
            'status_code': order.status,
            'status_display': status_map.get(order.status, order.status),
            'total': float(order.total_amount)
        })
    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Pedido não encontrado.'}, status=404)

@csrf_exempt
def bot_all_products(request):
    from produtos.models import Product
    # Busca todos os produtos disponíveis, limitando para evitar spam massivo
    products = Product.objects.filter(available=True).order_by('category', 'name')[:20]
    data = []
    base_url = "https://www.yasmimos.com.br"
    for p in products:
        image_url = None
        if p.image:
            image_url = base_url + p.image.url
        data.append({
            'name': p.name,
            'price': float(p.price),
            'stock': p.stock,
            'url': f"{base_url}/{p.id}/{p.slug}/",
            'image_url': image_url,
            'category': p.category.name
        })
    return JsonResponse({'status': 'success', 'products': data})

@csrf_exempt
def bot_category_products(request, slug):
    from produtos.models import Product
    products = Product.objects.filter(category__slug=slug, available=True)[:10]
    data = []
    base_url = "https://www.yasmimos.com.br"
    for p in products:
        image_url = None
        if p.image:
            image_url = base_url + p.image.url
        data.append({
            'name': p.name,
            'price': float(p.price),
            'stock': p.stock,
            'url': f"{base_url}/{p.id}/{p.slug}/",
            'image_url': image_url
        })
    return JsonResponse({'status': 'success', 'products': data})

@csrf_exempt
def bot_fidelity_status(request, id_code):
    from fidelidade.models import LoyaltyCard
    try:
        card = LoyaltyCard.objects.get(id_code__iexact=id_code)
        
        # Lógica de ciclo de 7 selos
        current_stamps = card.stamps % 7
        missing = 7 - current_stamps
        total_rewards = card.stamps // 7
        
        return JsonResponse({
            'status': 'success',
            'customer_name': card.customer_name,
            'stamps': current_stamps,
            'missing': missing,
            'total_rewards': total_rewards,
            'total_stamps': card.stamps
        })
    except LoyaltyCard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Cartão não encontrado.'}, status=404)

