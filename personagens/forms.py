from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Personagem, Poder, Inventario, Item


class CadastroForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class PersonagemForm(forms.ModelForm):
    class Meta:
        model = Personagem
        fields = [
            'foto',
            'nome',
            'nivel_poder',
            # Características
            'forca', 'vigor', 'destreza', 'agilidade', 'luta', 'inteligencia', 'prontidao', 'presenca',
            # Defesas
            'aparar', 'esquivar', 'fortitude', 'vontade', 'resistencia', 'penalidade_resistencia', 'condicao',
            # Perícias
            'acrobacias', 'atletismo', 'combate_distancia', 'combate_corpo', 'enganacao', 'especialidade',
            'furtividade', 'intimidacao', 'intuicao', 'investigacao', 'percepcao', 'persuasao',
            'prestidigitacao', 'tecnologia', 'tratamento', 'veiculos', 'historia', 'sobrevivencia',
            # Campo especialidade_casting_ability
            'especialidade_casting_ability',
        ]
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

from .models import Inventario, Item

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['itens', 'ouro', 'dragon_shard']
        widgets = {
            'itens': forms.SelectMultiple(attrs={'size': 10}),  # ou CheckboxSelectMultiple
        }