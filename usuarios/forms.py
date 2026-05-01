from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model
from .models import CustomUser, PasswordResetCode
from allauth.socialaccount.forms import SignupForm as SocialSignupForm

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone_number')
        labels = {
            'username': 'Usuário',
            'email': 'E-mail',
            'phone_number': 'Telefone (WhatsApp)',
        }

class CodeVerificationForm(forms.Form):
    code = forms.CharField(label='Código de Verificação', max_length=8, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000000', 'maxlength': '8', 'style': 'text-transform: uppercase; letter-spacing: 12px; text-align: center; font-size: 2.2rem; font-weight: bold;'}))

    def clean_code(self):
        code = self.cleaned_data.get('code', '').upper()
        # Validation happens in the view usually involving the user, but we can do some basic format check here
        return code

class CustomPasswordResetForm(forms.Form):
    email = forms.EmailField(label='E-mail', max_length=254, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'seu@email.com', 'style': 'padding: 15px; border-radius: 8px; font-size: 1.1rem; text-align: center; background-color: var(--input-bg); color: var(--text-color); border: 2px solid var(--input-border);'}))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        User = get_user_model()
        if not User.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError("Este e-mail não está cadastrado no YasMimos.")
        return email

class CustomSocialSignupForm(SocialSignupForm):
    phone_number = forms.CharField(max_length=15, label='Telefone (WhatsApp)', required=True)

    def __init__(self, *args, **kwargs):
        super(CustomSocialSignupForm, self).__init__(*args, **kwargs)
        if 'username' in self.fields:
            self.fields['username'].label = 'Como você quer ser chamado (Usuário)'
            self.fields['username'].help_text = 'Este será seu nome público no site.'
        self.fields['phone_number'].label = 'Seu WhatsApp para contato'
        self.fields['phone_number'].widget.attrs.update({'placeholder': '(XX) XXXXX-XXXX'})

    def save(self, request):
        user = super(CustomSocialSignupForm, self).save(request)
        user.phone_number = self.cleaned_data['phone_number']
        user.save()
        return user
