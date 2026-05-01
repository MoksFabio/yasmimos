from django.contrib import admin
from django.urls import path, include
from sistema.views import service_worker, manifest, offline_view
from django.conf import settings
from django.conf.urls.static import static
from allauth.socialaccount.views import SignupView

class CustomSocialSignupView(SignupView):
    template_name = 'usuarios/social/cadastro_google.html'

urlpatterns = [
    path('painel-seguro-admin/', admin.site.urls),
    path('accounts/social/signup/', CustomSocialSignupView.as_view(), name='socialaccount_signup'),
    path('accounts/', include('allauth.urls')),
    path('sistema/', include('sistema.urls', namespace='sistema')),
    path('carrinho/', include('carrinho.urls', namespace='carrinho')),
    path('pedidos/', include('pedidos.urls', namespace='pedidos')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
    path('chat/', include('chat.urls', namespace='chat')),
    path('fidelidade/', include('fidelidade.urls', namespace='fidelidade')),

    path('sw.js', service_worker, name='service_worker'),
    path('manifest.json', manifest, name='manifest'),
    path('offline/', offline_view, name='offline'),
    path('', include('produtos.urls', namespace='produtos')),
]

from django.urls import re_path
from django.views.static import serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
