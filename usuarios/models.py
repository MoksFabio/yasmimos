from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
import random
import string
from django.utils import timezone
from datetime import timedelta

class SpaceUnicodeUsernameValidator(UnicodeUsernameValidator):
    regex = r'^[\w.@+\- ]+\Z'
    message = _(
        'Informe um nome de usuário válido. Este valor pode conter apenas letras, '
        'números, espaços e os caracteres @/./+/-/_.'
    )

class CustomUser(AbstractUser):
    username_validator = SpaceUnicodeUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Obrigatório. 150 caracteres ou menos. Letras, números e @/./+/-/_/espaços.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return self.username

class PasswordResetCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='password_reset_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Código de Recuperação"
        verbose_name_plural = "Códigos de Recuperação"

    def is_valid(self):
        # Code is valid for 15 minutes
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=15)

    @classmethod
    def create_for_user(cls, user):
        # Invalidate previous codes
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        # Generate new code (6 Hex-like chars: 0-9, A-F)
        code = ''.join(random.choices('0123456789ABCDEF', k=6))
        return cls.objects.create(user=user, code=code)
