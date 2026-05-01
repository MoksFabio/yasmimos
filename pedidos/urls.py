from django.urls import path
from . import views
from . import views_quick
from . import views_edit

app_name = 'pedidos'

urlpatterns = [
    path('create/', views.order_create, name='order_create'),
    path('confirmed/<int:order_id>/', views.order_created, name='order_created'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('status/<int:order_id>/', views.check_order_status, name='check_order_status'),
    path('list-api/', views.order_list_api, name='order_list_api'),
    path('update-status/<int:order_id>/<str:new_status>/', views.update_order_status, name='update_order_status'),
    path('delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('edit/<int:order_id>/', views_edit.edit_order_modal, name='edit_order_modal'),
    path('edit/<int:order_id>/save/', views_edit.save_edited_order, name='save_edited_order'),
    path('clear-all/', views.clear_all_orders, name='clear_all_orders'),
    path('quick-action/', views_quick.quick_order_action, name='quick_order_action'),
    path('coupons/', views.manage_coupons, name='manage_coupons'),
    path('api/my-pedidos/', views.my_orders_poll, name='my_orders_poll'),
    path('api/coupons/list/', views.api_list_coupons, name='api_list_coupons'),
    path('api/coupons/add/', views.api_add_coupon, name='api_add_coupon'),
    path('api/coupons/delete/<int:coupon_id>/', views.api_delete_coupon, name='api_delete_coupon'),
    path('api/coupons/toggle/<int:coupon_id>/', views.api_toggle_coupon, name='api_toggle_coupon'),
    path('webhook/mercadopago/', views.mp_webhook, name='mp_webhook'),
    path('receipt-image/<int:order_id>/', views.order_receipt_image, name='order_receipt_image'),
    path('receipt-html/<int:order_id>/', views.receipt_html_for_bot, name='receipt_html_for_bot'),
    path('global-search/', views.global_order_search, name='global_order_search'),
]
