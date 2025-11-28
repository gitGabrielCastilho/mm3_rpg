from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Personagem, Poder, Inventario, Vantagem


class CadastroForm(UserCreationForm):
    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            return email
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe um usuário com este e-mail.")
        return email

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
            'arcana', 'religiao',
            # Campo especialidade_casting_ability
            'especialidade_casting_ability',
            'vantagens',
        ]
        exclude = ['usuario']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # As perícias 'combate_distancia' e 'combate_corpo' foram removidas da UI.
        # Torná-las não obrigatórias evita erros de validação ao salvar.
        for f in ('combate_distancia', 'combate_corpo'):
            if f in self.fields:
                self.fields[f].required = False
        # Append attribute abbreviation to each skill label, e.g., "Atletismo (FOR)", "Arcana (INT)"
        attr_abbr = {
            'forca': 'FOR', 'vigor': 'VIG', 'destreza': 'DES', 'agilidade': 'AGI',
            'luta': 'LUT', 'inteligencia': 'INT', 'prontidao': 'PRO', 'presenca': 'PRE',
        }
        skill_attr = {
            'acrobacias': 'agilidade',
            'atletismo': 'forca',
            'combate_distancia': 'destreza',
            'combate_corpo': 'luta',
            'enganacao': 'presenca',
            # especialidade is dynamic below
            'furtividade': 'agilidade',
            'intimidacao': 'presenca',
            'intuicao': 'prontidao',
            'investigacao': 'inteligencia',
            'percepcao': 'prontidao',
            'persuasao': 'presenca',
            'prestidigitacao': 'destreza',
            'tecnologia': 'inteligencia',
            'tratamento': 'inteligencia',
            'veiculos': 'destreza',
            'historia': 'inteligencia',
            'sobrevivencia': 'prontidao',
            'arcana': 'inteligencia',
            'religiao': 'prontidao',
        }
        # Determine selected ability for Especialidade
        esp_ability = (
            (self.data.get('especialidade_casting_ability') if hasattr(self, 'data') else None)
            or getattr(getattr(self, 'instance', None), 'especialidade_casting_ability', None)
            or self.initial.get('especialidade_casting_ability', None)
            or 'inteligencia'
        )
        skill_attr['especialidade'] = esp_ability
        # Update labels present in this form
        for skill, ability in skill_attr.items():
            if skill in self.fields:
                base_label = self.fields[skill].label or skill.replace('_', ' ').capitalize()
                abbr = attr_abbr.get(ability, ability[:3].upper())
                self.fields[skill].label = f"{base_label} ({abbr})"

    def clean(self):
        cleaned_data = super().clean()
        # Se os campos não vierem no POST (pois não estão na UI), normalize para 0
        for f in ('combate_distancia', 'combate_corpo'):
            if cleaned_data.get(f) in (None, ''):
                cleaned_data[f] = 0
        return cleaned_data


class PoderForm(forms.ModelForm):
    class Meta:
        model = Poder
        fields = [
            'id',
            'nome', 'array', 'tipo', 'caminho_aflicao', 'modo', 'duracao', 'nivel_efeito', 'bonus_ataque', 'somar_forca_no_nivel', 'charges',
            'defesa_ativa', 'defesa_passiva', 'casting_ability',
            'de_item', 'item_origem', 'de_vantagem', 'vantagem_origem', 'ligados'
        ]
        widgets = {
            'id': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Charges: apenas números positivos (deixe em branco para não usar)
        if 'charges' in self.fields:
            try:
                self.fields['charges'].required = False
                self.fields['charges'].widget.attrs.update({
                    'min': 1,
                    'step': 1,
                    'inputmode': 'numeric',
                    'pattern': '[0-9]+'
                })
            except Exception:
                pass
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
        # Regras de CHARGES
        # 1) No máximo 1 poder com charges>0 por Array (mesmo nome de array, case-insensitive)
        # 2) Cada poder: charges <= floor(NP/2)
        # O NP vem de self.instance (Personagem) no inline formset
        try:
            np = int(getattr(self.instance, 'nivel_poder', 0) or 0)
        except Exception:
            np = 0
        max_charges = max(0, np // 2)
        charges_por_array = {}
        # Percorre para coletar conflitos por nome/modo/duracao e validar charges
        for form in getattr(self, 'forms', []):
            if not hasattr(form, 'cleaned_data'):
                continue
            cd = form.cleaned_data or {}
            if cd.get('DELETE'):
                continue
            nome = (cd.get('nome') or '').strip()
            if nome:
                modo = cd.get('modo')
                duracao = cd.get('duracao')
                key = nome.lower()
                nomes_originais.setdefault(key, nome)
                variantes_por_nome.setdefault(key, set()).add((modo, duracao))

            # Validar charges por poder
            charges = cd.get('charges')
            try:
                cval = int(charges) if charges not in (None, '') else 0
            except Exception:
                cval = 0
            if cval < 0:
                form.add_error('charges', 'Charges não pode ser negativo.')
            if cval > max_charges:
                form.add_error('charges', f"Charges máximo por poder é {max_charges} (NP/2).")

            # Regra 1: no máximo um poder com charges>0 por array
            arr = (cd.get('array') or '').strip().lower()
            if arr and cval > 0:
                charges_por_array[arr] = charges_por_array.get(arr, 0) + 1

        conflitos = [nomes_originais[k] for k, vs in variantes_por_nome.items() if len(vs) > 1]
        if conflitos:
            raise forms.ValidationError(
                "Não é possível salvar: existem poderes com o mesmo nome mas com modo e/ou duração diferentes: "
                + ", ".join(sorted(set(conflitos)))
            )
        arrays_invalidos = [arr for arr, cnt in charges_por_array.items() if cnt > 1]
        if arrays_invalidos:
            raise forms.ValidationError(
                "Cada Array pode ter no máximo 1 poder com Charges (>0). Arrays com conflito: "
                + ", ".join(sorted(set(arrays_invalidos)))
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
            'arcana', 'religiao',
            # Campo especialidade_casting_ability
            'especialidade_casting_ability',
        ]
        exclude = ['usuario']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornar não obrigatórias as perícias ocultas na UI
        for f in ('combate_distancia', 'combate_corpo'):
            if f in self.fields:
                self.fields[f].required = False
        attr_abbr = {
            'forca': 'FOR', 'vigor': 'VIG', 'destreza': 'DES', 'agilidade': 'AGI',
            'luta': 'LUT', 'inteligencia': 'INT', 'prontidao': 'PRO', 'presenca': 'PRE',
        }
        skill_attr = {
            'acrobacias': 'agilidade',
            'atletismo': 'forca',
            'combate_distancia': 'destreza',
            'combate_corpo': 'luta',
            'enganacao': 'presenca',
            'furtividade': 'agilidade',
            'intimidacao': 'presenca',
            'intuicao': 'prontidao',
            'investigacao': 'inteligencia',
            'percepcao': 'prontidao',
            'persuasao': 'presenca',
            'prestidigitacao': 'destreza',
            'tecnologia': 'inteligencia',
            'tratamento': 'inteligencia',
            'veiculos': 'destreza',
            'historia': 'inteligencia',
            'sobrevivencia': 'prontidao',
            'arcana': 'inteligencia',
            'religiao': 'prontidao',
        }
        esp_ability = (
            (self.data.get('especialidade_casting_ability') if hasattr(self, 'data') else None)
            or getattr(getattr(self, 'instance', None), 'especialidade_casting_ability', None)
            or self.initial.get('especialidade_casting_ability', None)
            or 'inteligencia'
        )
        skill_attr['especialidade'] = esp_ability
        for skill, ability in skill_attr.items():
            if skill in self.fields:
                base_label = self.fields[skill].label or skill.replace('_', ' ').capitalize()
                abbr = attr_abbr.get(ability, ability[:3].upper())
                self.fields[skill].label = f"{base_label} ({abbr})"

    def clean(self):
        cleaned_data = super().clean()
        # Normaliza para 0 quando ausentes
        for f in ('combate_distancia', 'combate_corpo'):
            if cleaned_data.get(f) in (None, ''):
                cleaned_data[f] = 0
        return cleaned_data


class PoderNPCForm(forms.ModelForm):
    class Meta:
        model = Poder
        fields = [
            'nome', 'array', 'tipo', 'modo', 'duracao', 'nivel_efeito', 'bonus_ataque', 'somar_forca_no_nivel', 'charges',
            'defesa_ativa', 'defesa_passiva', 'casting_ability', 'ligados'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Charges: apenas números positivos (deixe em branco para não usar)
        if 'charges' in self.fields:
            try:
                self.fields['charges'].required = False
                self.fields['charges'].widget.attrs.update({
                    'min': 1,
                    'step': 1,
                    'inputmode': 'numeric',
                    'pattern': '[0-9]+'
                })
            except Exception:
                pass
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

