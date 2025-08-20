from django import forms
from django.conf import settings
from personagens.models import Personagem
from .models import Mapa
from .utils import process_image_upload

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
            # Em vez de falhar, tentamos recomprimir durante o save()
            # Mantemos o arquivo por ora e substituiremos no save.
            # Também armazenamos um sinalizador para forçar recompressão.
            self._needs_recompress = True
        # Tipo de conteúdo básico
        ctype = getattr(f, 'content_type', '') or ''
        if not ctype.startswith('image/'):
            raise forms.ValidationError('Envie um arquivo de imagem válido.')
        return f

    def save(self, commit=True):
        instance = super().save(commit=False)
        f = self.cleaned_data.get('imagem')
        max_mb = int(getattr(settings, 'MAPA_MAX_UPLOAD_MB', 10))
        max_bytes = max_mb * 1024 * 1024
        if f:
            try:
                size = getattr(f, 'size', None) or 0
            except Exception:
                size = 0
            if size > max_bytes or getattr(self, '_needs_recompress', False):
                try:
                    instance.imagem = process_image_upload(f, max_bytes=max_bytes)
                except Exception:
                    # Se falhar a recompressão, deixe o arquivo original e permita que o storage trate
                    pass
        if commit:
            instance.save()
        return instance