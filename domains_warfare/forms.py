from django import forms
from .models import Domain
from salas.models import Sala
from personagens.models import Personagem


class DomainForm(forms.ModelForm):
    """Formulário para criar/editar domínios."""
    
    class Meta:
        model = Domain
        fields = [
            'nome', 'descricao', 'brasao', 'governante', 'sala', 'jogadores_acesso',
            'nivel', 'diplomacy', 'espionage', 'lore', 'operations',
            'ouro', 'dragonshards',
            'keep', 'tower', 'temple', 'establishment'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'brasao': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'governante': forms.Select(attrs={'class': 'form-control'}),
            'sala': forms.Select(attrs={'class': 'form-control'}),
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
        
        # Filtrar salas disponíveis
        if user:
            from personagens.models import Perfil
            perfil = Perfil.objects.filter(user=user).first()
            
            if user.is_staff or user.is_superuser:
                salas = Sala.objects.all()
            elif perfil and perfil.sala_atual:
                # Jogadores veem apenas sua sala atual
                salas = Sala.objects.filter(id=perfil.sala_atual.id)
            else:
                salas = Sala.objects.none()
            
            self.fields['sala'].queryset = salas
            
            # Se está editando, define a sala atual
            if not self.instance.pk and perfil and perfil.sala_atual:
                self.fields['sala'].initial = perfil.sala_atual
            
            # Filtrar governantes (apenas personagens das salas disponíveis)
            if salas.exists():
                self.fields['governante'].queryset = Personagem.objects.filter(sala__in=salas)
            else:
                self.fields['governante'].queryset = Personagem.objects.none()
        
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
