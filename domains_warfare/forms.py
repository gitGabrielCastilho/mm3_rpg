from django import forms
from .models import Domain
from personagens.models import Personagem


class DomainForm(forms.ModelForm):
    """Formulário para criar/editar domínios."""
    
    class Meta:
        model = Domain
        fields = [
            'nome', 'descricao', 'brasao', 'governante', 'jogadores_acesso',
            'nivel', 'diplomacy', 'espionage', 'lore', 'operations',
            'ouro', 'dragonshards',
            'keep', 'tower', 'temple', 'establishment'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'brasao': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'governante': forms.Select(attrs={'class': 'form-control'}),
            'jogadores_acesso': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
            'nivel': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '5'}),
            'diplomacy': forms.NumberInput(attrs={'class': 'form-control', 'min': '-3', 'max': '3'}),
            'espionage': forms.NumberInput(attrs={'class': 'form-control', 'min': '-3', 'max': '3'}),
            'lore': forms.NumberInput(attrs={'class': 'form-control', 'min': '-3', 'max': '3'}),
            'operations': forms.NumberInput(attrs={'class': 'form-control', 'min': '-3', 'max': '3'}),
            'ouro': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'dragonshards': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'keep': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '5'}),
            'tower': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '5'}),
            'temple': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '5'}),
            'establishment': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '5'}),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Filtrar governantes disponíveis
        if user:
            try:
                from personagens.models import PerfilUsuario
                perfil = PerfilUsuario.objects.filter(user=user).first()
                
                # Governantes são personagens da sala do usuário
                if perfil and perfil.sala_atual:
                    self.fields['governante'].queryset = Personagem.objects.filter(sala=perfil.sala_atual)
                else:
                    self.fields['governante'].queryset = Personagem.objects.none()
            except Exception as e:
                # Se houver erro, deixa o queryset padrão
                pass
        
        # Valores padrão
        if not self.instance.pk:
            self.fields['nivel'].initial = 1
            self.fields['diplomacy'].initial = 0
            self.fields['espionage'].initial = 0
            self.fields['lore'].initial = 0
            self.fields['operations'].initial = 0
            self.fields['ouro'].initial = 0
            self.fields['dragonshards'].initial = 0
            self.fields['keep'].initial = 0
            self.fields['tower'].initial = 0
            self.fields['temple'].initial = 0
            self.fields['establishment'].initial = 0
