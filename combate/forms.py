from django import forms
from django.conf import settings
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

    def clean_imagem(self):
        f = self.cleaned_data.get('imagem')
        if not f:
            return f
        # Tamanho máximo configurável (MB)
        max_mb = int(getattr(settings, 'MAPA_MAX_UPLOAD_MB', 10))
        max_bytes = max_mb * 1024 * 1024
        try:
            size = getattr(f, 'size', None)
        except Exception:
            size = None
        if size and size > max_bytes:
            raise forms.ValidationError(f"O arquivo excede o limite de {max_mb}MB.")
        # Tipo de conteúdo básico
        ctype = getattr(f, 'content_type', '') or ''
        if not ctype.startswith('image/'):
            raise forms.ValidationError('Envie um arquivo de imagem válido.')
        return f