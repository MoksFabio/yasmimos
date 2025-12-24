from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from .models import StoreSettings

def get_store_status(request):
    settings = StoreSettings.get_settings()
    return JsonResponse({'is_open': settings.is_open})

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_store_status(request):
    settings = StoreSettings.get_settings()
    settings.is_open = not settings.is_open
    settings.save()
    return JsonResponse({'status': 'success', 'is_open': settings.is_open})
