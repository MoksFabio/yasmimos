from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm

from .forms import UserRegistrationForm, CustomPasswordResetForm, CodeVerificationForm
from .models import PasswordResetCode

User = get_user_model()

def logout_view(request):
    logout(request)
    return redirect('produtos:lista')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Specify the backend since we have multiple backends configured
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            return redirect('produtos:lista')
    else:
        form = UserRegistrationForm()
    return render(request, 'usuarios/cadastro.html', {'form': form})

@login_required
def profile(request):
    from pedidos.models import Order
    from datetime import timedelta
    from django.utils import timezone
    import calendar
    
    all_pedidos = request.user.pedidos.all().order_by('-created')
    active_statuses = ['pending', 'paid', 'preparing', 'ready', 'shipped']
    
    active_orders = all_pedidos.filter(status__in=active_statuses)
    history_orders_all = all_pedidos.exclude(status__in=active_statuses)
    
    # --- Logic for Clube YasMimos Dashboard ---
    active_plan_name = "Sem Plano"
    days_remaining = 0
    
    valid_statuses_for_plan = ['paid', 'preparing', 'ready', 'shipped', 'delivered']
    sixty_days_ago = timezone.now() - timedelta(days=60)
    
    recent_plan_pedidos = all_pedidos.filter(
        status__in=valid_statuses_for_plan, 
        created__gte=sixty_days_ago
    )
    
    for order in recent_plan_pedidos:
        for item in order.items.all():
            if item.product.category and 'clube' in item.product.category.name.lower():
                current_date = order.created
                
                if 'grand' in item.product.name.lower():
                    if current_date.month == 12:
                        next_month = 1
                        next_year = current_date.year + 1
                    else:
                        next_month = current_date.month + 1
                        next_year = current_date.year
                    last_day_next_month = calendar.monthrange(next_year, next_month)[1]
                    expiration_date = current_date.replace(year=next_year, month=next_month, day=last_day_next_month, hour=23, minute=59)
                else:
                    expiration_date = current_date + timedelta(days=30)
                
                days_left = (expiration_date - timezone.now()).days
                
                if days_left >= 0:
                    active_plan_name = item.product.name
                    days_remaining = days_left
                    break
                    
        if active_plan_name != "Sem Plano":
            break
            
    context = {
        'active_orders': active_orders,
        'history_orders': history_orders_all[:5],
        'has_more_history': history_orders_all.count() > 5,
        'active_plan_name': active_plan_name,
        'plan_days_remaining': max(0, days_remaining) if days_remaining > 0 else 0
    }
    return render(request, 'usuarios/perfil.html', context)

@login_required
def manage_subscription(request):
    from pedidos.models import Order
    from datetime import timedelta
    from django.utils import timezone
    import calendar
    
    all_pedidos = request.user.pedidos.all().order_by('-created')
    active_plan_name = "Sem Plano"
    active_plan_obj = None
    days_remaining = 0
    expiration_date = None
    start_date = None
    
    valid_statuses_for_plan = ['paid', 'preparing', 'ready', 'shipped', 'delivered']
    sixty_days_ago = timezone.now() - timedelta(days=60)
    
    recent_plan_pedidos = all_pedidos.filter(
        status__in=valid_statuses_for_plan, 
        created__gte=sixty_days_ago
    )
    
    for order in recent_plan_pedidos:
        for item in order.items.all():
            if item.product.category and 'clube' in item.product.category.name.lower():
                current_date = order.created
                
                if 'grand' in item.product.name.lower():
                    if current_date.month == 12:
                        next_month = 1
                        next_year = current_date.year + 1
                    else:
                        next_month = current_date.month + 1
                        next_year = current_date.year
                    last_day_next_month = calendar.monthrange(next_year, next_month)[1]
                    expiration_date = current_date.replace(year=next_year, month=next_month, day=last_day_next_month, hour=23, minute=59)
                else:
                    expiration_date = current_date + timedelta(days=30)
                
                days_left = (expiration_date - timezone.now()).days
                
                if days_left >= 0:
                    active_plan_name = item.product.name
                    active_plan_obj = item.product
                    start_date = current_date
                    days_remaining = days_left
                    
                    # --- Generate Tracking Days ---
                    if not isinstance(item.metadata, dict):
                        item.metadata = {}
                    tracked_dates_str = item.metadata.get('club_tracking', [])
                    weekdays_pt = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
                    
                    d = current_date.date()
                    end_d = expiration_date.date()
                    tracking_days = []
                    
                    while d <= end_d:
                        wd = d.weekday()
                        is_valid_day = False
                        
                        if 'diário' in active_plan_name.lower() or 'diario' in active_plan_name.lower():
                            if wd in [1, 3]: # Terça e Quinta
                                is_valid_day = True
                        elif 'duo' in active_plan_name.lower():
                            if wd == 4: # Sexta
                                is_valid_day = True
                        elif 'grand' in active_plan_name.lower():
                            if wd < 5: # Segunda-Sexta
                                is_valid_day = True
                        else:
                            is_valid_day = True

                        if is_valid_day:
                            d_str = d.strftime('%Y-%m-%d')
                            is_past = d < timezone.now().date()
                            tracking_days.append({
                                'date_str': d_str,
                                'date_obj': d,
                                'label': f"{d.strftime('%d/%m')} ({weekdays_pt[wd]})",
                                'is_completed': d_str in tracked_dates_str,
                                'is_past': is_past
                            })
                        d += timedelta(days=1)
                    
                    # --- Day Flavors ---
                    day_flavors = item.metadata.get('day_flavors', {})
                    active_item_id = item.id
                    
                    break
                    
        if active_plan_obj:
            break
            
    if not active_plan_obj:
        from django.contrib import messages
        messages.info(request, "Você não possui uma assinatura ativa no momento.")
        return redirect('usuarios:profile')
        
    schedule_text = "Disponível conforme regras da loja e do plano."
    plan_lower = active_plan_name.lower()
    
    slots_per_day = 1
    if 'diário' in plan_lower or 'diario' in plan_lower:
        schedule_text = "Retirada todas as Terças e Quintas-feiras."
    elif 'duo' in plan_lower:
        schedule_text = "Retirada exclusiva nas Sextas-feiras (Caixinha com 4)."
        slots_per_day = 4
    elif 'grand' in plan_lower:
        schedule_text = "Retirada em todos os dias de atendimento da YasMimos no Campus."

    can_renew = days_remaining <= 5 and active_plan_obj.stock > 0
        
    from produtos.models import Product
    brigadeiros = Product.objects.filter(category__name__icontains='Brigadeiro', available=True)
        
    future_tracking_days = []
    for td in tracking_days:
        if not td['is_past'] and not td['is_completed']:
            d_str = td['date_str']
            selected_slots = day_flavors.get(d_str, [])
            slots_data = []
            for i in range(slots_per_day):
                val = selected_slots[i] if i < len(selected_slots) else None
                slots_data.append(val)
            # Create a copy to not modify original tracking_days format unexpectedly
            ftd = dict(td)
            ftd['slots_data'] = slots_data
            future_tracking_days.append(ftd)

    context = {
        'active_plan_name': active_plan_name,
        'active_plan_obj': active_plan_obj,
        'active_item_id': active_item_id,
        'start_date': start_date,
        'expiration_date': expiration_date,
        'days_remaining': days_remaining,
        'schedule_text': schedule_text,
        'can_renew': can_renew,
        'tracking_days': tracking_days,
        'future_tracking_days': future_tracking_days,
        'brigadeiros': brigadeiros,
        'slots_per_day': slots_per_day,
        'slots_range': range(slots_per_day)
    }
    return render(request, 'usuarios/gerenciar_assinatura.html', context)

@login_required
def manage_subscription_poll(request):
    from pedidos.models import Order
    from datetime import timedelta
    from django.utils import timezone
    import calendar
    
    all_pedidos = request.user.pedidos.all().order_by('-created')
    active_plan_name = "Sem Plano"
    active_plan_obj = None
    days_remaining = 0
    expiration_date = None
    start_date = None
    
    valid_statuses_for_plan = ['paid', 'preparing', 'ready', 'shipped', 'delivered']
    sixty_days_ago = timezone.now() - timedelta(days=60)
    
    recent_plan_pedidos = all_pedidos.filter(
        status__in=valid_statuses_for_plan, 
        created__gte=sixty_days_ago
    )
    
    for order in recent_plan_pedidos:
        for item in order.items.all():
            if item.product.category and 'clube' in item.product.category.name.lower():
                current_date = order.created
                
                if 'grand' in item.product.name.lower():
                    if current_date.month == 12:
                        next_month = 1
                        next_year = current_date.year + 1
                    else:
                        next_month = current_date.month + 1
                        next_year = current_date.year
                    last_day_next_month = calendar.monthrange(next_year, next_month)[1]
                    expiration_date = current_date.replace(year=next_year, month=next_month, day=last_day_next_month, hour=23, minute=59)
                else:
                    expiration_date = current_date + timedelta(days=30)
                
                days_left = (expiration_date - timezone.now()).days
                
                if days_left >= 0:
                    active_plan_name = item.product.name
                    active_plan_obj = item.product
                    start_date = current_date
                    days_remaining = days_left
                    
                    # --- Generate Tracking Days ---
                    if not isinstance(item.metadata, dict):
                        item.metadata = {}
                    tracked_dates_str = item.metadata.get('club_tracking', [])
                    weekdays_pt = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
                    
                    d = current_date.date()
                    end_d = expiration_date.date()
                    tracking_days = []
                    
                    while d <= end_d:
                        wd = d.weekday()
                        is_valid_day = False
                        
                        if 'diário' in active_plan_name.lower() or 'diario' in active_plan_name.lower():
                            if wd in [1, 3]: # Terça e Quinta
                                is_valid_day = True
                        elif 'duo' in active_plan_name.lower():
                            if wd == 4: # Sexta
                                is_valid_day = True
                        elif 'grand' in active_plan_name.lower():
                            if wd < 5: # Segunda-Sexta
                                is_valid_day = True
                        else:
                            is_valid_day = True

                        if is_valid_day:
                            d_str = d.strftime('%Y-%m-%d')
                            is_past = d < timezone.now().date()
                            tracking_days.append({
                                'date_str': d_str,
                                'date_obj': d,
                                'label': f"{d.strftime('%d/%m')} ({weekdays_pt[wd]})",
                                'is_completed': d_str in tracked_dates_str,
                                'is_past': is_past
                            })
                        d += timedelta(days=1)
                    
                    break
                    
        if active_plan_obj:
            break
            
    if not active_plan_obj:
        return JsonResponse({'error': 'no active plan'}, status=400)
        
    context = {
        'tracking_days': tracking_days
    }
    return render(request, 'usuarios/parcial_album_doces.html', context)

@login_required
@require_POST
def save_day_flavors(request):
    import json
    from pedidos.models import OrderItem
    from django.http import JsonResponse
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        day_flavors = data.get('day_flavors', {})
        item = OrderItem.objects.get(id=item_id, order__user=request.user)
        if not isinstance(item.metadata, dict):
            item.metadata = {}
        item.metadata['day_flavors'] = day_flavors
        item.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def delete_account(request):
    if request.user.is_superuser:
        return redirect('usuarios:profile')
        
    if request.method == 'POST':
        user = request.user
        user.delete()
        return redirect('produtos:lista')
    return render(request, 'usuarios/excluir_conta.html')

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def delete_user_api(request, user_id):
    user = get_object_or_404(User, id=user_id)
    # Prevent deleting self
    if user.id == request.user.id:
         return JsonResponse({'status': 'error', 'message': 'Você não pode excluir sua própria conta.'}, status=403)
    
    user.delete()
    return JsonResponse({'status': 'success'})

@user_passes_test(lambda u: u.is_superuser)
def user_list_api(request):
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Exists, OuterRef
    from pedidos.models import OrderItem
    
    thirty_days_ago = timezone.now() - timedelta(days=60)
    
    clube_items = OrderItem.objects.filter(
        order__user=OuterRef('pk'),
        order__status__in=['paid', 'preparing', 'ready', 'shipped', 'delivered'],
        order__created__gte=thirty_days_ago,
        product__category__name__icontains='clube'
    )
    
    users = User.objects.annotate(is_assinante=Exists(clube_items)).order_by('-date_joined')
    return render(request, 'usuarios/parcial_lista_usuarios.html', {'users': users})

@user_passes_test(lambda u: u.is_superuser)
def admin_list_api(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'usuarios/parcial_lista_admins.html', {'users': users})

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def promote_to_admin_api(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'User is already a superuser'}, status=400)
    
    user.is_superuser = True
    user.is_staff = True
    user.save()
    return JsonResponse({'status': 'success'})

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def demote_admin_api(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if user.id == request.user.id:
         return JsonResponse({'status': 'error', 'message': 'Você não pode remover seus próprios privilégios de administrador.'}, status=403)
         
    if not user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Usuário não é um administrador.'}, status=400)
    
    user.is_superuser = False
    user.is_staff = False
    user.save()
    return JsonResponse({'status': 'success'})

# --- PASSWORD RESET VIEWS (OTP) ---

def password_reset_request(request):
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Generate code
            reset_code = PasswordResetCode.create_for_user(user)
            
            # Send Email
            subject = 'Seu código de acesso - YasMimos'
            html_message = render_to_string('usuarios/email_redefinicao.html', {
                'user': user,
                'code': reset_code.code,
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject, 
                plain_message, 
                settings.DEFAULT_FROM_EMAIL, 
                [user.email], 
                html_message=html_message
            )
            
            # Save email in session to verify later
            request.session['reset_email'] = email
            return redirect('usuarios:password_reset_verify')
    else:
        form = CustomPasswordResetForm()
    
    return render(request, 'usuarios/esqueci_senha.html', {'form': form})

def password_reset_verify(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('usuarios:password_reset')
    
    if request.method == 'POST':
        form = CodeVerificationForm(request.POST)
        if form.is_valid():
            code_input = form.cleaned_data['code']
            user = User.objects.get(email=email)
            
            # Check most recent unused code
            valid_code = PasswordResetCode.objects.filter(user=user, is_used=False).order_by('-created_at').first()
            
            if valid_code and valid_code.code == code_input and valid_code.is_valid():
                valid_code.is_used = True
                valid_code.save()
                
                request.session['reset_verified_user_id'] = user.id
                return redirect('usuarios:password_reset_confirm')
            else:
                form.add_error('code', 'Código inválido ou expirado.')
    else:
        form = CodeVerificationForm()
        
    return render(request, 'usuarios/verificar_codigo.html', {'form': form, 'email': email})

def password_reset_confirm(request):
    user_id = request.session.get('reset_verified_user_id')
    if not user_id:
        return redirect('usuarios:password_reset')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            # Clear session
            del request.session['reset_email']
            del request.session['reset_verified_user_id']
            messages.success(request, 'Sua senha foi redefinida com sucesso! Faça login.')
            return redirect('usuarios:login')
    else:
        form = SetPasswordForm(user)
        
    return render(request, 'usuarios/confirmar_nova_senha.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def client_history_api(request, user_id):
    from pedidos.models import Order
    from django.db.models import Sum
    from datetime import timedelta
    from django.utils import timezone
    import calendar
    
    client = get_object_or_404(User, id=user_id)
    orders = Order.objects.filter(user=client).order_by('-created')
    total_spent = orders.filter(status__in=['paid', 'preparing', 'ready', 'shipped', 'delivered', 'completed']).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Check for active Clube Plan
    active_plan = None
    active_plan_item = None
    days_remaining = 0
    tracking_days = []
    
    valid_statuses_for_plan = ['paid', 'preparing', 'ready', 'shipped', 'delivered']
    thirty_days_ago = timezone.now() - timedelta(days=60) # Increased lookback for Grand Mimo
    recent_plan_pedidos = orders.filter(
        status__in=valid_statuses_for_plan, 
        created__gte=thirty_days_ago
    )
    
    for order in recent_plan_pedidos:
        for item in order.items.all():
            if item.product.category and 'clube' in item.product.category.name.lower():
                active_plan = item.product.name
                active_plan_item = item
                
                current_date = order.created
                if 'grand' in item.product.name.lower():
                    if current_date.month == 12:
                        next_month = 1
                        next_year = current_date.year + 1
                    else:
                        next_month = current_date.month + 1
                        next_year = current_date.year
                    last_day_next_month = calendar.monthrange(next_year, next_month)[1]
                    expiration_date = current_date.replace(year=next_year, month=next_month, day=last_day_next_month, hour=23, minute=59)
                else:
                    expiration_date = current_date + timedelta(days=30)
                    
                days_remaining = (expiration_date - timezone.now()).days
                
                # Check if it has expired (days_remaining < 0). If not, we keep it as active.
                if days_remaining < 0:
                    active_plan = None
                    continue

                if not isinstance(item.metadata, dict):
                    item.metadata = {}
                tracked_dates_str = item.metadata.get('club_tracking', [])
                weekdays_pt = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
                
                d = current_date.date()
                end_d = expiration_date.date()
                
                while d <= end_d:
                    wd = d.weekday()
                    is_valid_day = False
                    
                    if 'diário' in active_plan.lower() or 'diario' in active_plan.lower():
                        if wd in [1, 3]: # Terça(1) e Quinta(3)
                            is_valid_day = True
                    elif 'duo' in active_plan.lower():
                        if wd == 4: # Sexta(4)
                            is_valid_day = True
                    elif 'grand' in active_plan.lower():
                        if wd < 5: # Seg-Sex(0-4)
                            is_valid_day = True
                    else:
                        is_valid_day = True

                    if is_valid_day:
                        d_str = d.strftime('%Y-%m-%d')
                        tracking_days.append({
                            'date_str': d_str,
                            'label': f"{d.strftime('%d/%m')} ({weekdays_pt[wd]})",
                            'is_completed': d_str in tracked_dates_str
                        })
                    d += timedelta(days=1)
                    
                break
        if active_plan:
            break

    day_flavors_formatted = []
    if active_plan_item and isinstance(active_plan_item.metadata, dict):
        day_flavors = active_plan_item.metadata.get('day_flavors', {})
        if day_flavors:
            from produtos.models import Product
            # Get all unique IDs
            all_f_ids = [fid for fids in day_flavors.values() for fid in fids if fid]
            if all_f_ids:
                products_dict = {p.id: p.name for p in Product.objects.filter(id__in=all_f_ids)}
                for day_dict in tracking_days:
                    d_str = day_dict['date_str']
                    if d_str in day_flavors:
                        f_names = []
                        for fid in day_flavors[d_str]:
                            if fid and int(fid) in products_dict:
                                f_names.append(products_dict[int(fid)])
                        if f_names:
                            day_flavors_formatted.append({
                                'date_str': d_str,
                                'label': day_dict['label'],
                                'is_completed': day_dict.get('is_completed', False),
                                'flavors': f_names
                            })

    return render(request, 'usuarios/parcial_historico_cliente.html', {
        'client': client,
        'pedidos': orders[:10],
        'total_orders': orders.count(),
        'total_spent': total_spent,
        'active_plan': active_plan,
        'active_plan_item': active_plan_item,
        'days_remaining': max(0, days_remaining),
        'tracking_days': tracking_days,
        'day_flavors': day_flavors_formatted
    })

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_club_tracking(request, item_id):
    from pedidos.models import OrderItem
    item = get_object_or_404(OrderItem, id=item_id)
    date_str = request.POST.get('date_str')
    
    metadata = item.metadata if isinstance(item.metadata, dict) else {}
    tracking = metadata.get('club_tracking', [])
    new_tracking = list(tracking) # Copiar para forçar o ORM a entender a mudança
    
    if date_str in new_tracking:
        new_tracking.remove(date_str)
        status = 'removed'
    else:
        new_tracking.append(date_str)
        status = 'added'
        
    metadata['club_tracking'] = new_tracking
    item.metadata = metadata
    item.save(update_fields=['metadata'])
    
    return JsonResponse({'status': 'success', 'action': status})
