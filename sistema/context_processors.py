from .models import StoreSettings
from chat.models import ChatSession

def store_settings(request):
    return {'store_settings': StoreSettings.get_settings()}

def active_chats_monitor(request):
    has_active = False
    if request.user.is_authenticated and request.user.is_superuser:
        has_active = ChatSession.objects.filter(status='ACTIVE').exists()
    return {'has_active_chats': has_active}

def pending_order_monitor(request):
    from pedidos.models import Order
    pedidos_pendentes = Order.objects.none()
    if request.user.is_authenticated:
        pedidos_pendentes = Order.objects.filter(user=request.user, status__in=['pending', 'pending_manual']).order_by('-created')
    
    return {
        'pending_orders_list': pedidos_pendentes,
        'user_pending_order': pedidos_pendentes.first(),
        'pending_orders_count': pedidos_pendentes.count() if request.user.is_authenticated else 0
    }
