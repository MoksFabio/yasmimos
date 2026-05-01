import mercadopago
from django.conf import settings
from datetime import datetime, timedelta, timezone

from sistema.models import StoreSettings

def create_pix_payment(order):
    store_settings = StoreSettings.get_settings()
    
    # Diagnostic Logging
    print(f"[PIX] Gerando pagamento para conta ativa: {store_settings.mp_active_account}")
    
    access_token = None
    if store_settings.mp_active_account == 'fabio':
        access_token = store_settings.mp_access_token_fabio
        print(f"[PIX] Usando token do Fábio (Tamanho: {len(access_token) if access_token else 0})")
    elif store_settings.mp_active_account == 'yasmim':
        access_token = store_settings.mp_access_token_yasmim
        print(f"[PIX] Usando token da Yasmim (Tamanho: {len(access_token) if access_token else 0})")
    
    if not access_token:
        access_token = settings.MERCADOPAGO_ACCESS_TOKEN
        print(f"[PIX] FALLBACK: Usando token padrão do sistema (Settings)")

    if not access_token or len(access_token) < 10:
        raise ValueError(f"O token do Mercado Pago para a conta '{store_settings.mp_active_account}' não está configurado.")



    sdk = mercadopago.SDK(access_token)
    
    # Define a expiração do PIX para 5 dias (120 horas) a partir de agora
    expiration_date = datetime.now(timezone.utc) + timedelta(days=5)
    formatted_expiration = expiration_date.isoformat(timespec='milliseconds')
    
    payment_data = {
        "transaction_amount": float(order.total_amount),
        "description": f"Pedido {order.id} - YasMimos",
        "payment_method_id": "pix",
        "date_of_expiration": formatted_expiration,
        "payer": {
            "email": order.user.email if order.user else "cliente@yasmimos.com",
            "first_name": order.guest_name.split()[0] if order.guest_name else (order.user.first_name if order.user else "Cliente"),
            "last_name": order.guest_name.split()[-1] if order.guest_name and len(order.guest_name.split()) > 1 else "YasMimos",
            "identification": {
                "type": "CPF",
                "number": "16770946483" 
            },
            "address": {
                "zip_code": "06233200",
                "street_name": "Av. das Nações Unidas",
                "street_number": "3003",
                "neighborhood": "Bonfim",
                "city": "Osasco",
                "federal_unit": "SP"
            }
        },
        "notification_url": "https://www.yasmimos.com.br/pedidos/webhook/mercadopago/" 
    }

    # Garantir email válido
    payer_email = "cliente@yasmimos.com"
    if order.user and order.user.email:
        payer_email = order.user.email
    elif hasattr(order, 'guest_email') and order.guest_email:
        payer_email = order.guest_email
    else:
        # Email ficticio único por pedido para evitar rejeição
        payer_email = f"cliente_{order.id}@yasmimos.com"

    payment_data['payer']['email'] = payer_email

    payment_response = sdk.payment().create(payment_data)
    payment = payment_response["response"]
    
    return payment
