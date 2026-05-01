from django.db import models
from django.conf import settings

class StoreSettings(models.Model):
    is_open = models.BooleanField(default=True)
    about_photo = models.ImageField(upload_to='about/', blank=True, null=True)
    developer_photo = models.ImageField(upload_to='about/', blank=True, null=True, verbose_name="Foto do Desenvolvedor")
    delivery_notice = models.TextField(default="Não realizamos entregas no momento. Apenas retirada.", verbose_name="Aviso de Entrega / Localização")
    delivery_details = models.TextField(blank=True, null=True, verbose_name="Detalhes da Localização")
    
    # GPS Tracking Fields
    gps_enabled = models.BooleanField(default=False, verbose_name="Rastreamento em Tempo Real")
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    last_gps_update = models.DateTimeField(blank=True, null=True)
    
    # Financial Control
    cash_in_drawer = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Dinheiro em Gaveta")
    cash_breakdown = models.JSONField(default=dict, blank=True, verbose_name="Detalhamento das Notas")
    
    # Payment Settings
    pix_manual_enabled = models.BooleanField(default=False, verbose_name="Pix Manual (Estático)")
    pix_key = models.CharField(max_length=255, default="118.190.084-01", verbose_name="Chave Pix Manual")
    
    # Mercado Pago Settings
    mp_access_token_fabio = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token Pix Fabio (MP)")
    mp_access_token_yasmim = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token Pix Yasmim (MP)")
    mp_active_account = models.CharField(
        max_length=10, 
        choices=[('fabio', 'Fabio'), ('yasmim', 'Yasmim')], 
        default='fabio',
        verbose_name="Conta Pix Ativa (MP)"
    )

    class Meta:
        verbose_name = "Configuração da Loja"
        verbose_name_plural = "Configurações da Loja"
    
    def save(self, *args, **kwargs):
        if not self.pk and StoreSettings.objects.exists():
            # Se tentar criar um novo, pegamos o ID do que já existe para atualizar ele
            self.pk = StoreSettings.objects.first().pk
        
        super(StoreSettings, self).save(*args, **kwargs)

        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            from django.utils import timezone
            
            channel_layer = get_channel_layer()
            if channel_layer:
                last_update_str = None
                if self.last_gps_update:
                    local_dt = timezone.localtime(self.last_gps_update)
                    last_update_str = local_dt.strftime('%H:%M:%S')

                data = {
                    'type': 'store_status_update',
                    'is_open': self.is_open,
                    'notice': self.delivery_notice,
                    'details': self.delivery_details,
                    'gps_enabled': self.gps_enabled,
                    'latitude': self.latitude,
                    'longitude': self.longitude,
                    'last_update': last_update_str,
                    'pix_manual_enabled': self.pix_manual_enabled
                }
                async_to_sync(channel_layer.group_send)('store_status_group', data)
        except Exception as e:
            print(f"Erro ao enviar WS signal: {e}")

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Store is {'Open' if self.is_open else 'Closed'}"

class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inscrição Push"
        verbose_name_plural = "Inscrições Push"

    def __str__(self):
        return f"PushSub for {self.user.username}"
