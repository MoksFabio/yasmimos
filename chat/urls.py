from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('start/', views.start_chat, name='start_chat'),
    path('start/guest/', views.start_chat_guest, name='start_chat_guest'),
    path('room/<int:session_id>/', views.chat_room, name='room'),
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    path('end/<int:session_id>/', views.end_chat, name='end_chat'),
    path('delete/<int:session_id>/', views.delete_chat, name='delete_chat'),
]
