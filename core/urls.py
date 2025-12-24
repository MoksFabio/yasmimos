from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('api/status/', views.get_store_status, name='get_status'),
    path('api/status/toggle/', views.toggle_store_status, name='toggle_status'),
]
