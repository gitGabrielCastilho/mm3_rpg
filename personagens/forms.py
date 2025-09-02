from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Personagem, Poder, Inventario, Vantagem


class CadastroForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class PersonagemForm(forms.ModelForm):
    vantagens = forms.ModelMultipleChoiceField(
        queryset=Vantagem.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Vantagens"
    )
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
            'vantagens',
        ]
        exclude = ['usuario']


class PoderForm(forms.ModelForm):
    class Meta:
        model = Poder
        fields = [
            'id',
            'nome', 'tipo', 'modo', 'duracao', 'nivel_efeito', 'bonus_ataque',
            'defesa_ativa', 'defesa_passiva', 'casting_ability',
            'de_item', 'item_origem', 'de_vantagem', 'vantagem_origem'
        ]
        widgets = {
            'id': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        de_item = cleaned_data.get('de_item')
        item_origem = cleaned_data.get('item_origem')
        de_vantagem = cleaned_data.get('de_vantagem')
        vantagem_origem = cleaned_data.get('vantagem_origem')

        # Não pode ter duas origens
        if de_item and de_vantagem:
            raise forms.ValidationError("Selecione apenas uma origem: Item ou Vantagem.")
        if de_item and not item_origem:
            raise forms.ValidationError("Selecione o item de origem.")
        if de_vantagem and not vantagem_origem:
            raise forms.ValidationError("Selecione a vantagem de origem.")
        if not de_item and item_origem:
            raise forms.ValidationError("Marque 'Poder de Item?' para selecionar um item de origem.")
        if not de_vantagem and vantagem_origem:
            raise forms.ValidationError("Marque 'Poder de Vantagem?' para selecionar uma vantagem de origem.")
        return cleaned_data

PoderFormSet = inlineformset_factory(
    Personagem,
    Poder,
    form=PoderForm,
    extra=1,
    can_delete=True
)


class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['itens', 'ouro', 'dragon_shard']
        widgets = {
            'itens': forms.SelectMultiple(attrs={'size': 10}),  # ou CheckboxSelectMultiple
        }


# ---- NPC Forms (sem vantagens e sem inventário; poderes sem origens) ----
class PersonagemNPCForm(forms.ModelForm):
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


class PoderNPCForm(forms.ModelForm):
    class Meta:
        model = Poder
        fields = [
            'nome', 'tipo', 'modo', 'duracao', 'nivel_efeito', 'bonus_ataque',
            'defesa_ativa', 'defesa_passiva', 'casting_ability',
        ]


PoderNPCFormSet = inlineformset_factory(
    Personagem,
    Poder,
    form=PoderNPCForm,
    extra=1,
    can_delete=True
)

