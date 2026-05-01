from django.urls import path
from . import views

app_name = 'sistema'

urlpatterns = [
    path('api/status/', views.get_store_status, name='get_status'),
    path('api/status/toggle/', views.toggle_store_status, name='toggle_status'),
    path('api/pix/toggle/', views.toggle_pix_mode, name='toggle_pix_mode'),
    path('api/toggle-mp-account/', views.toggle_mp_account, name='toggle_mp_account'),
    path('api/update-mp-tokens/', views.update_mp_tokens, name='update_mp_tokens'),
    path('api/update-notice/', views.update_delivery_notice, name='update_notice'),
    path('api/status/update_gps/', views.update_gps_location, name='update_gps'),
    path('update-about-photo/', views.update_about_photo, name='update_about_photo'),
    path('update-developer-photo/', views.update_developer_photo, name='update_developer_photo'),
    path('sobre/', views.about_view, name='about'),
    path('configuracoes/', views.settings_view, name='settings'),

    path('api/drawer/balance/', views.get_drawer_balance, name='get_drawer_balance'),
    path('api/drawer/update/', views.update_drawer_balance, name='update_drawer_balance'),
    
    # WebPush
    path('api/push/save/', views.save_subscription, name='save_subscription'),
    path('api/push/key/', views.get_vapid_public_key, name='get_vapid_public_key'),
    
    path('offline/', views.offline_view, name='offline'),
    path('export-database/', views.export_database_xlsx, name='export_database'),
    
    # Bot API
    path('api/bot/info/', views.bot_store_info, name='bot_info'),
    path('api/bot/order/<int:order_id>/', views.bot_order_status, name='bot_order'),
    path('api/bot/products/all/', views.bot_all_products, name='bot_products_all'),
    path('api/bot/category/<slug:slug>/', views.bot_category_products, name='bot_category'),
    path('api/bot/fidelity/<str:id_code>/', views.bot_fidelity_status, name='bot_fidelity'),
]
