from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from .models import LoyaltyCard
from django.contrib import messages
from django.http import JsonResponse

from django.utils import timezone
from django.db.models import Q

def loyalty_card_page(request):
    """Página de consulta e gerenciamento de cartões com filtros e ordenação avançada."""
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')
    sort_by = request.GET.get('sort', 'stamps_desc')
    
    card = None
    all_cards = LoyaltyCard.objects.all()
    
    # 1. Filtros de Status (Convertendo para QuerySet)
    if status_filter == 'rewards':
        all_cards = all_cards.filter(stamps__gte=7)
    elif status_filter == 'active':
        all_cards = all_cards.filter(stamps__gt=0, stamps__lt=7)
    elif status_filter == 'empty':
        all_cards = all_cards.filter(stamps=0)

    # 2. Busca por ID, Nome ou Telefone
    if search_query:
        all_cards = all_cards.filter(
            Q(id_code__icontains=search_query) | 
            Q(customer_name__icontains=search_query) | 
            Q(customer_phone__icontains=search_query)
        )
        card = LoyaltyCard.objects.filter(id_code=search_query.strip().upper()).first()

    # 3. Ordenação Magnífica
    if sort_by == 'stamps_desc':
        all_cards = all_cards.order_by('-stamps', '-updated_at')
    elif sort_by == 'stamps_asc':
        all_cards = all_cards.order_by('stamps', '-updated_at')
    elif sort_by == 'oldest':
        all_cards = all_cards.order_by('updated_at')
    else: # default: stamps_desc
        all_cards = all_cards.order_by('-stamps', '-updated_at')

    # Estatísticas rápidas para o Dashboard
    stats = {
        'total': LoyaltyCard.objects.count(),
        'ready_to_reward': LoyaltyCard.objects.filter(stamps__gte=7).count(),
        'active_today': LoyaltyCard.objects.filter(updated_at__date=timezone.now().date()).count()
    }
        
    return render(request, 'fidelidade/fidelidade.html', {
        'card': card,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'all_cards': all_cards,
        'stats': stats
    })

@user_passes_test(lambda u: u.is_superuser)
def loyalty_card_create(request):
    if request.method == 'POST':
        id_code = request.POST.get('id_code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        if not id_code:
            messages.error(request, "O ID do cartão é obrigatório.")
            return redirect('fidelidade:loyalty_card_page')
            
        if LoyaltyCard.objects.filter(id_code=id_code).exists():
            messages.error(request, f"O ID '{id_code}' já está registrado.")
            return redirect('fidelidade:loyalty_card_page')
            
        LoyaltyCard.objects.create(id_code=id_code, customer_name=name, customer_phone=phone)
        messages.success(request, f"Cartão {id_code} registrado com sucesso!")
        
    return redirect('fidelidade:loyalty_card_page')

@user_passes_test(lambda u: u.is_superuser)
def loyalty_stamp_add(request, card_id):
    card = get_object_or_404(LoyaltyCard, id=card_id)
    if request.method == 'POST':
        x = request.POST.get('x')
        y = request.POST.get('y')
        ajax = request.POST.get('ajax') or request.headers.get('x-requested-with') == 'XMLHttpRequest'
        
        if x is not None and y is not None:
            card.add_stamp_pos(float(x), float(y))
            if ajax:
                return JsonResponse({'success': True, 'positions': card.get_positions(), 'stamps': card.stamps})
            messages.success(request, f"Selo adicionado manualmente!")
        else:
            # Fallback for old simple clicks or tests
            card.stamps += 1
            card.save()
            if ajax:
                return JsonResponse({'success': True, 'stamps': card.stamps})
            messages.success(request, "Selo adicionado (sem coordenada).")
            
    return redirect('fidelidade:loyalty_card_page')

@user_passes_test(lambda u: u.is_superuser)
def loyalty_stamp_remove(request, card_id):
    card = get_object_or_404(LoyaltyCard, id=card_id)
    card.remove_last_stamp()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
        return JsonResponse({'success': True, 'positions': card.get_positions(), 'stamps': card.stamps})
    messages.success(request, "Último selo removido!")
    return redirect('fidelidade:loyalty_card_page')

@user_passes_test(lambda u: u.is_superuser)
def loyalty_card_update(request, card_id):
    card = get_object_or_404(LoyaltyCard, id=card_id)
    if request.method == 'POST':
        id_code = request.POST.get('id_code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        if not id_code:
            messages.error(request, "O ID do cartão é obrigatório.")
            return redirect('fidelidade:loyalty_card_page')
            
        if LoyaltyCard.objects.filter(id_code=id_code).exclude(id=card.id).exists():
            messages.error(request, f"O ID '{id_code}' já está sendo usado por outro cartão.")
            return redirect('fidelidade:loyalty_card_page')
            
        card.id_code = id_code
        card.customer_name = name
        card.customer_phone = phone
        card.save()
        
        messages.success(request, f"Dados do cartão {card.id_code} atualizados!")
        
    return redirect('fidelidade:loyalty_card_page')

@user_passes_test(lambda u: u.is_superuser)
def loyalty_card_delete(request, card_id):
    card = get_object_or_404(LoyaltyCard, id=card_id)
    id_code = card.id_code
    card.delete()
    messages.success(request, f"Cartão {id_code} removido.")
    return redirect('fidelidade:loyalty_card_page')

def loyalty_card_api(request, id_code):
    """Retorna os dados do cartão em JSON para atualização em tempo real."""
    card = LoyaltyCard.objects.filter(id_code=id_code.upper()).first()
    if not card:
        return JsonResponse({'exists': False})
    
    return JsonResponse({
        'exists': True,
        'stamps': card.stamps,
        'current_cycle_stamps': card.current_cycle_stamps,
        'reward_count': card.reward_count,
        'customer_name': card.customer_name or "Cliente Amigo",
        'positions': card.get_positions()
    })
