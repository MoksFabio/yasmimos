from django.urls import path
from . import views

app_name = 'carrinho'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('remove/<str:item_key>/', views.cart_remove, name='cart_remove'),
    path('update/<str:item_key>/', views.cart_update, name='cart_update'),
    path('coupon/apply/', views.coupon_apply, name='coupon_apply'),
    path('set-tip/', views.set_tip, name='set_tip'),
    path('status/', views.cart_status, name='cart_status'),
]
