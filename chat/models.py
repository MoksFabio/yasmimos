from django.db import models
from django.conf import settings

class ChatSession(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Ativo'),
        ('RESOLVED', 'Resolvido'),
    ]
    
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions')
    visitor_name = models.CharField(max_length=100, blank=True, null=True)
    topic = models.CharField(max_length=100, default='Assunto Geral')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def client_name(self):
        if self.client:
            return self.client.get_full_name() or self.client.username
        return self.visitor_name or "Visitante"

    def __str__(self):
        return f"{self.client_name} - {self.get_status_display()}"

class Message(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        sender_name = self.sender.get_full_name() if self.sender else (self.session.visitor_name or "Visitante")
        return f"{sender_name}: {self.content[:20]}"
