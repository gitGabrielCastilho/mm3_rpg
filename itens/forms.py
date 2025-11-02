from .models import Item, ItemPoder
from django import forms
from django.forms import inlineformset_factory

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
        # remove vazios
        for section in list(mods.keys()):
            if not mods[section]:
                mods.pop(section)
        return mods


class ItemPoderForm(forms.ModelForm):
    class Meta:
        model = ItemPoder
        exclude = ['item']


ItemPoderFormSet = inlineformset_factory(
    Item,
    ItemPoder,
    form=ItemPoderForm,
    extra=1,
    can_delete=True,
)