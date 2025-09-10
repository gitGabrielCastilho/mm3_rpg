from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
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
            'de_item', 'item_origem', 'de_vantagem', 'vantagem_origem', 'ligados'
        ]
        widgets = {
            'id': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'ligados' in self.fields:
            if self.instance and getattr(self.instance, 'personagem_id', None):
                self.fields['ligados'].queryset = Poder.objects.filter(personagem_id=self.instance.personagem_id).exclude(pk=self.instance.pk)
            else:
                self.fields['ligados'].queryset = Poder.objects.none()
                self.fields['ligados'].help_text = 'Salve o personagem para encadear poderes.'
            # Exibir como dropdown-like via JS (mantém múltipla seleção)
            try:
                self.fields['ligados'].widget.attrs.update({'size': 1, 'class': (self.fields['ligados'].widget.attrs.get('class','') + ' multi-dropdown').strip(), 'data-multi-dropdown': '1'})
            except Exception:
                pass

    def clean(self):
        cleaned_data = super().clean()
        de_item = cleaned_data.get('de_item')
        item_origem = cleaned_data.get('item_origem')
        de_vantagem = cleaned_data.get('de_vantagem')
        vantagem_origem = cleaned_data.get('vantagem_origem')
        nome = cleaned_data.get('nome')

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
        ligados = cleaned_data.get('ligados') or []
        modo = cleaned_data.get('modo')
        duracao = cleaned_data.get('duracao')
        for lp in ligados:
            if self.instance.pk and lp.personagem_id != self.instance.personagem_id:
                raise forms.ValidationError(f"Poder ligado '{lp.nome}' não pertence ao mesmo personagem.")
            if lp.modo != modo or lp.duracao != duracao:
                raise forms.ValidationError(f"Poder ligado '{lp.nome}' deve ter mesmo modo e duração ({modo}/{duracao}).")
            if self.instance.pk and lp.pk == self.instance.pk:
                raise forms.ValidationError("Um poder não pode estar ligado a si mesmo.")
            if nome and lp.nome != nome:
                raise forms.ValidationError(f"Poder ligado '{lp.nome}' deve ter o mesmo nome ('{nome}').")
        return cleaned_data

# Validação no formset: proíbe poderes com mesmo nome, mas modos/durações diferentes
class _PoderesConsistentesFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # Se qualquer formulário individual falhou, pule para não duplicar mensagens
        # Ainda assim, conseguimos validar com os que possuem cleaned_data
        variantes_por_nome = {}
        nomes_originais = {}
        for form in getattr(self, 'forms', []):
            if not hasattr(form, 'cleaned_data'):
                continue
            cd = form.cleaned_data or {}
            if cd.get('DELETE'):
                continue
            nome = (cd.get('nome') or '').strip()
            if not nome:
                continue
            modo = cd.get('modo')
            duracao = cd.get('duracao')
            key = nome.lower()
            nomes_originais.setdefault(key, nome)
            variantes_por_nome.setdefault(key, set()).add((modo, duracao))
        conflitos = [nomes_originais[k] for k, vs in variantes_por_nome.items() if len(vs) > 1]
        if conflitos:
            raise forms.ValidationError(
                "Não é possível salvar: existem poderes com o mesmo nome mas com modo e/ou duração diferentes: "
                + ", ".join(sorted(set(conflitos)))
            )

PoderFormSet = inlineformset_factory(
    Personagem,
    Poder,
    form=PoderForm,
    formset=_PoderesConsistentesFormSet,
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
            'defesa_ativa', 'defesa_passiva', 'casting_ability', 'ligados'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'ligados' in self.fields:
            if self.instance and getattr(self.instance, 'personagem_id', None):
                self.fields['ligados'].queryset = Poder.objects.filter(personagem_id=self.instance.personagem_id).exclude(pk=self.instance.pk)
            else:
                self.fields['ligados'].queryset = Poder.objects.none()
                self.fields['ligados'].help_text = 'Salve o NPC para encadear poderes.'
            # Exibir como dropdown-like via JS (mantém múltipla seleção)
            try:
                self.fields['ligados'].widget.attrs.update({'size': 1, 'class': (self.fields['ligados'].widget.attrs.get('class','') + ' multi-dropdown').strip(), 'data-multi-dropdown': '1'})
            except Exception:
                pass

    def clean(self):
        cleaned_data = super().clean()
        ligados = cleaned_data.get('ligados') or []
        modo = cleaned_data.get('modo')
        duracao = cleaned_data.get('duracao')
        nome = cleaned_data.get('nome')
        for lp in ligados:
            if self.instance.pk and lp.personagem_id != self.instance.personagem_id:
                raise forms.ValidationError(f"Poder ligado '{lp.nome}' não pertence ao mesmo personagem.")
            if lp.modo != modo or lp.duracao != duracao:
                raise forms.ValidationError(f"Poder ligado '{lp.nome}' deve ter mesmo modo e duração ({modo}/{duracao}).")
            if self.instance.pk and lp.pk == self.instance.pk:
                raise forms.ValidationError("Um poder não pode estar ligado a si mesmo.")
            if nome and lp.nome != nome:
                raise forms.ValidationError(f"Poder ligado '{lp.nome}' deve ter o mesmo nome ('{nome}').")
        return cleaned_data


PoderNPCFormSet = inlineformset_factory(
    Personagem,
    Poder,
    form=PoderNPCForm,
    formset=_PoderesConsistentesFormSet,
    extra=1,
    can_delete=True
)

