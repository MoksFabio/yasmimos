from django.contrib import admin
from .models import StoreSettings, PushSubscription

@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_open', 'mp_active_account', 'pix_manual_enabled')
    list_editable = ('is_open', 'mp_active_account', 'pix_manual_enabled')
    fieldsets = (
        ('Status da Loja', {
            'fields': ('is_open', 'delivery_notice', 'delivery_details')
        }),
        ('Controle Pix (Manual)', {
            'fields': ('pix_manual_enabled', 'pix_key')
        }),
        ('Controle Pix (Mercado Pago)', {
            'fields': ('mp_active_account', 'mp_access_token_fabio', 'mp_access_token_yasmim')
        }),
        ('Caixa', {
            'fields': ('cash_in_drawer', 'cash_breakdown')
        }),
        ('GPS', {
            'fields': ('gps_enabled', 'latitude', 'longitude', 'last_gps_update')
        }),
         ('Geral', {
            'fields': ('about_photo',)
        }),
    )

@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'endpoint', 'created_at')
