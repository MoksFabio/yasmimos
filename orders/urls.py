from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('create/', views.order_create, name='order_create'),
    path('confirmed/<int:order_id>/', views.order_created, name='order_created'),
    path('status/<int:order_id>/', views.check_order_status, name='check_order_status'),
    path('list-api/', views.order_list_api, name='order_list_api'),
    path('update-status/<int:order_id>/<str:new_status>/', views.update_order_status, name='update_order_status'),
    path('delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('clear-all/', views.clear_all_orders, name='clear_all_orders'),
]
