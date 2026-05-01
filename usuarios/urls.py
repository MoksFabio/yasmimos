from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomPasswordResetForm

app_name = 'usuarios'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='usuarios/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='usuarios/alterar_senha.html', success_url=reverse_lazy('usuarios:password_change_done')), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='usuarios/alterar_senha_concluido.html'), name='password_change_done'),
    path('profile/', views.profile, name='profile'),
    path('profile/manage-subscription/', views.manage_subscription, name='manage_subscription'),
    path('profile/manage-subscription/poll/', views.manage_subscription_poll, name='manage_subscription_poll'),
    path('profile/manage-subscription/save-flavors/', views.save_day_flavors, name='save_day_flavors'),
    path('delete/', views.delete_account, name='delete_account'),
    path('delete-api/<int:user_id>/', views.delete_user_api, name='delete_user_api'),
    path('demote-api/<int:user_id>/', views.demote_admin_api, name='demote_admin_api'),
    path('promote-api/<int:user_id>/', views.promote_to_admin_api, name='promote_to_admin_api'),
    path('list-api/', views.user_list_api, name='user_list_api'),
    path('admin-list-api/', views.admin_list_api, name='admin_list_api'),

    # Password Reset (OTP Code)
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    path('client-history/<int:user_id>/', views.client_history_api, name='client_history_api'),
    path('toggle-club-tracking/<int:item_id>/', views.toggle_club_tracking, name='toggle_club_tracking'),
]
