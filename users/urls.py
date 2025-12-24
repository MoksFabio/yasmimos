from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='usuarios/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='usuarios/alterar_senha.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='usuarios/alterar_senha_concluido.html'), name='password_change_done'),
    path('profile/', views.profile, name='profile'),
    path('delete/', views.delete_account, name='delete_account'),
    path('delete-api/<int:user_id>/', views.delete_user_api, name='delete_user_api'),
    path('list-api/', views.user_list_api, name='user_list_api'),
]
