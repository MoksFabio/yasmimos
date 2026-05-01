import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatSession, Message
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'chat_{self.session_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')
        
        if msg_type == 'chat_message':
            message = data['message']
            
            # Save message
            saved_msg = await self.save_message(self.session_id, message, self.scope['user'])

            # Send to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_name': (saved_msg.sender.get_full_name() or saved_msg.sender.username) if saved_msg.sender else (saved_msg.session.visitor_name or "Visitante"),
                    'is_support': saved_msg.sender.is_superuser if saved_msg.sender else False,
                    'timestamp': timezone.localtime(saved_msg.timestamp).strftime('%H:%M') if saved_msg.timestamp else timezone.localtime().strftime('%H:%M')
                }
            )
            
            # Notify dashboard about new message
            await self.channel_layer.group_send(
                "support_dashboard",
                {
                    "type": "dashboard_update",
                    "data": {
                        "type": "new_message",
                        "session_id": self.session_id,
                        "message_preview": message[:30]
                    }
                }
            )
            
        elif msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_typing',
                    'sender_name': "Suporte YasMimos" if self.scope['user'].is_superuser else ((self.scope['user'].get_full_name() or self.scope['user'].username) if self.scope['user'].is_authenticated else "Visitante"),
                    'sender_id': self.scope['user'].id,
                    'is_support': self.scope['user'].is_superuser,
                    'socket_id': data.get('socket_id'),
                    'is_typing': data['is_typing']
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_name': event['sender_name'],
            'is_support': event['is_support'],
            'timestamp': event['timestamp']
        }))
        
    async def user_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_typing',
            'sender_name': event['sender_name'],
            'sender_id': event.get('sender_id'),
            'is_support': event.get('is_support', False),
            'socket_id': event.get('socket_id'),
            'is_typing': event['is_typing']
        }))

    async def chat_ended(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_ended',
        }))

    async def chat_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_deleted',
        }))



    @database_sync_to_async
    def save_message(self, session_id, message, user):
        session = ChatSession.objects.get(id=session_id)
        sender = user if user.is_authenticated else None
        return Message.objects.create(session=session, sender=sender, content=message)


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_superuser:
            self.group_name = "support_dashboard"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if self.scope["user"].is_superuser:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def dashboard_update(self, event):
        await self.send(text_data=json.dumps(event['data']))
