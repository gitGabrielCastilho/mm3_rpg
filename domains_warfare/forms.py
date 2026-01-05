from django import forms
from .models import Domain, Unit, UnitAncestry, UnitTrait, UnitExperience, UnitEquipment, UnitType, UnitSize
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


class UnitForm(forms.ModelForm):
    """Formulário para criar/editar unidades."""
    
    class Meta:
        model = Unit
        fields = [
            'nome', 'descricao', 'imagem', 'ancestry', 'unit_type', 'size', 'experience', 'equipment',
            'is_mythic', 'ataque', 'poder', 'defesa', 'resistencia', 'moral', 'traits'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'imagem': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'ancestry': forms.Select(attrs={'class': 'form-control'}),
            'unit_type': forms.Select(attrs={'class': 'form-control'}),
            'size': forms.Select(attrs={'class': 'form-control'}),
            'experience': forms.Select(attrs={'class': 'form-control'}),
            'equipment': forms.Select(attrs={'class': 'form-control'}),
            'is_mythic': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ataque': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'poder': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'defesa': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'resistencia': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'moral': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 10}),
            'traits': forms.CheckboxSelectMultiple(attrs={'class': 'trait-checkbox'}),
        }
    
    def __init__(self, *args, domain=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.domain = domain
        
        # Valores padrão
        if not self.instance.pk:
            # Valores padrão de atributos base
            self.fields['is_mythic'].initial = False
            self.fields['ataque'].initial = 0
            self.fields['poder'].initial = 0
            self.fields['defesa'].initial = 10
            self.fields['resistencia'].initial = 10
            self.fields['moral'].initial = 0
            # Tenta definir experience como Green, ou deixa vazio se não existir
            try:
                green = UnitExperience.objects.get(nome='green')
                self.fields['experience'].initial = green
            except UnitExperience.DoesNotExist:
                pass


class MapaWargameForm(forms.ModelForm):
    """Formulário para criar mapas de warfare."""
    
    class Meta:
        from .models_warfare import MapaWarfare
        model = MapaWarfare
        fields = ['nome', 'imagem']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do mapa'
            }),
            'imagem': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
    
    def clean_imagem(self):
        f = self.cleaned_data.get('imagem')
        if not f:
            raise forms.ValidationError("Uma imagem é necessária.")
        
        # Verificar tamanho máximo (10MB por padrão)
        max_mb = 10
        max_bytes = max_mb * 1024 * 1024
        
        if hasattr(f, 'size') and f.size > max_bytes:
            raise forms.ValidationError(f"Arquivo muito grande. Máximo: {max_mb}MB")
        
        return f
