from django.urls import path
from . import views

app_name = 'fidelidade'

urlpatterns = [
    path('', views.loyalty_card_page, name='loyalty_card_page'),
    path('create/', views.loyalty_card_create, name='loyalty_card_create'),
    path('stamp-add/<int:card_id>/', views.loyalty_stamp_add, name='loyalty_stamp_add'),
    path('stamp-remove/<int:card_id>/', views.loyalty_stamp_remove, name='loyalty_stamp_remove'),
    path('update/<int:card_id>/', views.loyalty_card_update, name='loyalty_card_update'),
    path('delete/<int:card_id>/', views.loyalty_card_delete, name='loyalty_card_delete'),
    path('api/<str:id_code>/', views.loyalty_card_api, name='loyalty_card_api'),
]
