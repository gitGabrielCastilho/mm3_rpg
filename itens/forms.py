from .models import Item, ItemPoder
from django import forms
from django.forms import inlineformset_factory
from personagens.models import DANO_TIPO_CHOICES

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['nome', 'tipo', 'raridade', 'descricao']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 2}),
        }


# Form to capture structured modifiers into Item.mods JSON
class ItemModsForm(forms.Form):
    # Características
    forca = forms.IntegerField(initial=0, required=False)
    vigor = forms.IntegerField(initial=0, required=False)
    destreza = forms.IntegerField(initial=0, required=False)
    agilidade = forms.IntegerField(initial=0, required=False)
    luta = forms.IntegerField(initial=0, required=False)
    inteligencia = forms.IntegerField(initial=0, required=False)
    prontidao = forms.IntegerField(initial=0, required=False)
    presenca = forms.IntegerField(initial=0, required=False)
    # Defesas
    aparar = forms.IntegerField(initial=0, required=False)
    esquivar = forms.IntegerField(initial=0, required=False)
    fortitude = forms.IntegerField(initial=0, required=False)
    vontade = forms.IntegerField(initial=0, required=False)
    resistencia = forms.IntegerField(initial=0, required=False)
    # Perícias
    acrobacias = forms.IntegerField(initial=0, required=False)
    atletismo = forms.IntegerField(initial=0, required=False)
    combate_distancia = forms.IntegerField(initial=0, required=False)
    combate_corpo = forms.IntegerField(initial=0, required=False)
    enganacao = forms.IntegerField(initial=0, required=False)
    especialidade = forms.IntegerField(initial=0, required=False)
    furtividade = forms.IntegerField(initial=0, required=False)
    intimidacao = forms.IntegerField(initial=0, required=False)
    intuicao = forms.IntegerField(initial=0, required=False)
    investigacao = forms.IntegerField(initial=0, required=False)
    percepcao = forms.IntegerField(initial=0, required=False)
    persuasao = forms.IntegerField(initial=0, required=False)
    prestidigitacao = forms.IntegerField(initial=0, required=False)
    tecnologia = forms.IntegerField(initial=0, required=False)
    tratamento = forms.IntegerField(initial=0, required=False)
    veiculos = forms.IntegerField(initial=0, required=False)
    historia = forms.IntegerField(initial=0, required=False)
    sobrevivencia = forms.IntegerField(initial=0, required=False)
    arcana = forms.IntegerField(initial=0, required=False)
    religiao = forms.IntegerField(initial=0, required=False)
    resistencias_dano = forms.MultipleChoiceField(
        choices=DANO_TIPO_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Resistências a dano"
    )
    imunidades_dano = forms.MultipleChoiceField(
        choices=DANO_TIPO_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Imunidades a dano"
    )

    def clean(self):
        cleaned_data = super().clean()
        res = cleaned_data.get('resistencias_dano') or []
        imu = cleaned_data.get('imunidades_dano') or []
        res_set = set(res)
        imu_set = set(imu)
        conflito = res_set & imu_set
        if conflito:
            raise forms.ValidationError(
                "Não é possível ter Resistência e Imunidade ao mesmo tipo de dano: "
                + ", ".join(sorted(conflito))
            )
        cleaned_data['resistencias_dano'] = list(res_set)
        cleaned_data['imunidades_dano'] = list(imu_set)
        return cleaned_data

    def to_mods(self):
        cd = self.cleaned_data
        carac_keys = ['forca','vigor','destreza','agilidade','luta','inteligencia','prontidao','presenca']
        def_keys = ['aparar','esquivar','fortitude','vontade','resistencia']
        per_keys = [
            'acrobacias','atletismo','combate_distancia','combate_corpo','enganacao','especialidade',
            'furtividade','intimidacao','intuicao','investigacao','percepcao','persuasao',
            'prestidigitacao','tecnologia','tratamento','veiculos','historia','sobrevivencia','arcana','religiao'
        ]
        mods = {
            'caracteristicas': {k: int(cd.get(k) or 0) for k in carac_keys if cd.get(k)},
            'defesas': {k: int(cd.get(k) or 0) for k in def_keys if cd.get(k)},
            'pericias': {k: int(cd.get(k) or 0) for k in per_keys if cd.get(k)},
        }
        # Resistências e imunidades ficam no topo do JSON para fácil leitura
        res = cd.get('resistencias_dano') or []
        imu = cd.get('imunidades_dano') or []
        if res:
            mods['resistencias_dano'] = list(res)
        if imu:
            mods['imunidades_dano'] = list(imu)
        # remove vazios
        for section in list(mods.keys()):
            if not mods[section]:
                mods.pop(section)
        return mods


class ItemPoderForm(forms.ModelForm):
    class Meta:
        model = ItemPoder
        exclude = ['item']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se o modelo subjacente tiver caminho_aflicao (Poder ligado ao item), exponha o campo.
        try:
            if hasattr(self.instance, 'poder') and hasattr(self.instance.poder, 'caminho_aflicao'):
                # Garante que o campo exista nos fields do form (ModelForm já deve criá-lo se o FK incluir Poder)
                fld = self.fields.get('poder')
                if fld is not None:
                    # Nada especial aqui; a escolha do caminho é feita no form de Poder do personagem.
                    # Este form continua apenas escolhendo qual Poder o item concede.
                    pass
        except Exception:
            pass


ItemPoderFormSet = inlineformset_factory(
    Item,
    ItemPoder,
    form=ItemPoderForm,
    extra=1,
    can_delete=True,
)