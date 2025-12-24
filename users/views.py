from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test

User = get_user_model()

def logout_view(request):
    logout(request)
    return redirect('products:product_list')
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('products:product_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'usuarios/cadastro.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'usuarios/perfil.html')

@login_required
def delete_account(request):
    if request.user.is_superuser:
        return redirect('users:profile')
        
    if request.method == 'POST':
        user = request.user
        user.delete()
        return redirect('products:product_list')
    return render(request, 'usuarios/excluir_conta.html')

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def delete_user_api(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser:
         return JsonResponse({'status': 'error', 'message': 'Cannot delete superuser'}, status=403)
    user.delete()
    return JsonResponse({'status': 'success'})

@user_passes_test(lambda u: u.is_superuser)
def user_list_api(request):
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    return render(request, 'usuarios/parcial_lista_usuarios.html', {'users': users})
