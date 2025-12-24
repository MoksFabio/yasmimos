from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
import re

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

    def __str__(self):
        return self.username
