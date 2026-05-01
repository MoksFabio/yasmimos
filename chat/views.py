from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import ChatSession, Message
from django.db import connection
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def start_chat(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        if request.method == 'POST':
            topic = request.POST.get('topic', 'Assunto Geral')
            
            # Check if user already has an active session for THIS topic
            existing_session = ChatSession.objects.filter(client=request.user, topic=topic, status='ACTIVE').first()
            if existing_session:
                return redirect('chat:room', session_id=existing_session.id)
                
            session = ChatSession.objects.create(
                client=request.user, 
                topic=topic,
                status='ACTIVE'
            )
            
            # Create primary summary message
            initial_msg = f"Olá Suporte! Este cliente deseja falar sobre: {topic}"
            Message.objects.create(session=session, sender=None, content=initial_msg)

            # Notify dashboard
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "support_dashboard",
                {
                    "type": "dashboard_update",
                    "data": {
                        "type": "new_session",
                        "session_id": session.id,
                        "client_name": session.client_name,
                        "timestamp": session.created_at.strftime('%d/%m %H:%M')
                    }
                }
            )

            # --- Push Notification for Admins ---
            try:
                from sistema.utils_push import send_push_to_admins
                send_push_to_admins(
                    title="Novo Atendimento! 💬",
                    body=f"{session.client_name} abriu um chamado: {topic}",
                    url=f"https://www.yasmimos.com.br/chat/admin/"
                )
            except Exception as e:
                print(f"Chat Push Error: {e}")
            # ------------------------------------

            return redirect('chat:room', session_id=session.id)
            
        # Explicitly pass the user name to the template to avoid context processor issues
        user_name = request.user.first_name if request.user.first_name else request.user.username
        active_sessions = ChatSession.objects.filter(client=request.user, status='ACTIVE').order_by('-created_at')
        return render(request, 'chat/selecionar_assunto.html', {
            'client_name': user_name,
            'active_sessions': active_sessions
        })
    elif request.user.is_superuser:
        return redirect('chat:dashboard')
    else:
        # Check if guest already has a session
        existing_id = request.session.get('chat_session_id')
        if existing_id:
            # check if valid and active
            if ChatSession.objects.filter(id=existing_id, status='ACTIVE').exists():
                 return redirect('chat:room', session_id=existing_id)
        
        return render(request, 'chat/identificacao.html')

def start_chat_guest(request):
    if request.method == 'POST':
        name = request.POST.get('visitor_name')
        topic = request.POST.get('topic', 'Assunto Geral')
        
        if name:
            # Check if guest already has a session for THIS topic
            # We use session to track guest identity
            guest_session_id = request.session.get('chat_session_id')
            if guest_session_id:
                existing_session = ChatSession.objects.filter(id=guest_session_id, topic=topic, status='ACTIVE').first()
                if existing_session:
                    return redirect('chat:room', session_id=existing_session.id)

            session = ChatSession.objects.create(
                visitor_name=name,
                topic=topic,
                status='ACTIVE'
            )
            request.session['chat_session_id'] = session.id
            
            # Create primary summary message
            initial_msg = f"Olá Suporte! Este visitante ({name}) deseja falar sobre: {topic}"
            Message.objects.create(session=session, sender=None, content=initial_msg)

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "support_dashboard",
                {
                    "type": "dashboard_update",
                    "data": {
                        "type": "new_session",
                        "session_id": session.id,
                        "client_name": session.client_name,
                        "timestamp": session.created_at.strftime('%d/%m %H:%M')
                    }
                }
            )
            
            # --- Push Notification for Admins ---
            try:
                from sistema.utils_push import send_push_to_admins
                send_push_to_admins(
                    title="Novo Atendimento (Visitante)! 💬",
                    body=f"{session.client_name} abriu um chamado: {topic}",
                    url=f"https://www.yasmimos.com.br/chat/admin/"
                )
            except Exception as e:
                print(f"Chat Push Error: {e}")
            # ------------------------------------

            return redirect('chat:room', session_id=session.id)
    return redirect('chat:start_chat')

def chat_room(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        messages.info(request, "Este atendimento não está mais ativo ou foi removido.")
        return redirect('chat:start_chat')
    
    # Simple access control
    can_access = False
    if request.user.is_superuser:
        can_access = True
    elif request.user.is_authenticated and session.client == request.user:
        can_access = True
    elif request.session.get('chat_session_id') == session.id:
        can_access = True
        
    if not can_access:
        return redirect('produtos:lista')

    chat_messages = session.messages.all().order_by('timestamp')
    return render(request, 'chat/sala_atendimento.html', {
        'chat_session': session,
        'messages': chat_messages,
        'is_support': request.user.is_superuser
    })

@staff_member_required
def admin_dashboard(request):
    # Retrieve all active sessions, annotate with last message or just list
    active_sessions = ChatSession.objects.filter(status='ACTIVE').order_by('-created_at')
    resolved_sessions = ChatSession.objects.filter(status='RESOLVED').order_by('-created_at')[:20]  # Show last 20 resolved
    return render(request, 'chat/painel_suporte.html', {
        'active_sessions': active_sessions,
        'resolved_sessions': resolved_sessions
    })

@staff_member_required
def delete_chat(request, session_id):
    # Notify chat participants that session is deleted
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{session_id}',
        {
            'type': 'chat_deleted'
        }
    )
    
    session = get_object_or_404(ChatSession, id=session_id)
    session.delete()
    
    # If no sessions left, reset sequence to start from 1 again
    if not ChatSession.objects.exists():
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='chat_chatsession'")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='chat_message'")
            elif connection.vendor == 'postgresql':
                cursor.execute("ALTER SEQUENCE chat_chatsession_id_seq RESTART WITH 1;")
                cursor.execute("ALTER SEQUENCE chat_message_id_seq RESTART WITH 1;")
                
    messages.success(request, "O chat foi excluído com sucesso.")
    return redirect('chat:dashboard')

@staff_member_required
def end_chat(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    session.status = 'RESOLVED'
    session.save()
    
    # Notify chat participants
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{session.id}',
        {
            'type': 'chat_ended'
        }
    )
    
    messages.success(request, "O atendimento foi marcado como resolvido.")
    return redirect('chat:dashboard')
