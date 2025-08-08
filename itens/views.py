from django.shortcuts import render, redirect
from django.db import models
from .models import Item
from .forms import ItemForm
import random

# Create your views here.
def calcular_valor(rarity):
    rarity = (rarity or "").lower()
    if rarity == "common":
        return random.randint(2, 12) * 5
    elif rarity == "uncommon":
        return random.randint(2, 12) * 250
    elif rarity == "rare":
        return random.randint(2, 12) * 2500 + 5000
    elif rarity == "very rare":
        return random.randint(2, 12) * 8000 + 40000
    elif rarity == "legendary":
        return random.randint(2, 12) * 12500 + 150000
    elif rarity == "artifact":
        return (random.randint(2, 12) + 6) * 75000 + 3000000
    else:
        return 0

def itens(request):
    sala_atual = request.user.perfilusuario.sala_atual  # ajuste conforme seu modelo de perfil
    if not sala_atual:
        # Usuário fora de sala: só pode ver itens base
        itens = Item.objects.filter(sala__isnull=True)
        pode_criar = False
    else:
        # Usuário em sala: vê itens base + da sala
        itens = Item.objects.filter(models.Q(sala__isnull=True) | models.Q(sala=sala_atual))
        pode_criar = True

    form = ItemForm(request.POST or None)
    if pode_criar and request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.sala = sala_atual
        item.preco = calcular_valor(item.raridade)
        item.save()
        return redirect('itens')

    tipos = Item._meta.get_field('tipo').choices
    raridades = Item._meta.get_field('raridade').choices
    return render(request, 'itens/itens.html', {
        'form': form,
        'itens': itens,
        'tipos': tipos,
        'raridades': raridades,
        'pode_criar': pode_criar,
    })