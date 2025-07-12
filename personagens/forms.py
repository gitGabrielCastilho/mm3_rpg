from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Personagem, Poder

class CadastroForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class PersonagemForm(forms.ModelForm):
    class Meta:
        model = Personagem
        exclude = ['usuario']


class PoderForm(forms.ModelForm):
    class Meta:
        model = Poder
        fields = [
            'nome', 'tipo', 'modo', 'nivel_efeito', 'bonus_ataque',
            'defesa_ativa', 'defesa_passiva', 'casting_ability'
        ]

PoderFormSet = inlineformset_factory(
    Personagem,
    Poder,
    form=PoderForm,
    extra=1,
    can_delete=True
)