from .models import Item
from django import forms

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['nome', 'tipo', 'raridade', 'descricao']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 2}),
        }