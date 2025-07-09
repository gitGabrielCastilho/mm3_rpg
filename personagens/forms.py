from django import forms
from django.forms import modelformset_factory
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

PoderFormSet = modelformset_factory(
    Poder,
    fields=('nome', 'bonus_ataque', 'nivel_efeito'),
    extra=1,
    can_delete=True
)

class PoderForm(forms.ModelForm):
    class Meta:
        model = Poder
        fields = ['nome', 'bonus_ataque', 'nivel_efeito']