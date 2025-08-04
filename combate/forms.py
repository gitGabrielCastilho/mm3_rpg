from django import forms
from personagens.models import Personagem
from .models import Mapa

class AtaqueForm(forms.Form):
    atacante = forms.ModelChoiceField(queryset=Personagem.objects.all())
    alvo = forms.ModelChoiceField(queryset=Personagem.objects.all())
    tipo = forms.ChoiceField(choices=[("dano", "Dano"), ("aflicao", "Aflição")])
    alcance = forms.ChoiceField(choices=[("comum", "Comum"), ("area", "Área"), ("percepcao", "Percepção")])
    nivel = forms.IntegerField(min_value=1, max_value=20)
    bonus_ataque = forms.IntegerField()
    defesa = forms.ChoiceField(choices=[("aparar", "aparar"), ("esquivar", "esquivar")])
    resistencia = forms.ChoiceField(choices=[("fortitude", "fortitude"),("vontade", "vontade"), ("resistencia", "resistencia")])



class MapaForm(forms.ModelForm):
    class Meta:
        model = Mapa
        fields = ['nome', 'imagem']