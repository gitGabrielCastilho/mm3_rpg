from django.shortcuts import render, redirect
from django.db import models
from .models import Item
from .forms import ItemForm, ItemModsForm, ItemPoderFormSet

# Create your views here.
def calcular_valor(rarity):
    # Deprecated: preço agora calculado no save() do modelo a partir da raridade base.
    return 0

def itens(request):
    # Handle users without PerfilUsuario gracefully
    sala_atual = None
    try:
        sala_atual = request.user.perfilusuario.sala_atual  # ajuste conforme seu modelo de perfil
    except Exception:
        sala_atual = None
    if not sala_atual:
        # Usuário fora de sala: só pode ver itens base; sem criar
        itens = Item.objects.filter(sala__isnull=True)
        pode_criar = False
    else:
        # Usuário em sala: vê itens base + da sala
        itens = Item.objects.filter(models.Q(sala__isnull=True) | models.Q(sala=sala_atual))
        pode_criar = True

    form = ItemForm(request.POST or None)
    mods_form = ItemModsForm(request.POST or None)
    formset = ItemPoderFormSet(request.POST or None, prefix='itempoder')
    if pode_criar and request.method == 'POST' and form.is_valid() and mods_form.is_valid() and formset.is_valid():
        item = form.save(commit=False)
        item.sala = sala_atual
        # Preço será atribuído no save() se estiver 0
        item.save()
        # Salva mods estruturados no JSON
        item.mods = mods_form.to_mods()
        item.save()
        # Salva poderes do item
        formset.instance = item
        formset.save()
        return redirect('itens')

    tipos = Item._meta.get_field('tipo').choices
    raridades = Item._meta.get_field('raridade').choices
    return render(request, 'itens/itens.html', {
        'form': form,
        'mods_form': mods_form,
        'formset': formset,
        'itens': itens,
        'tipos': tipos,
        'raridades': raridades,
        'pode_criar': pode_criar,
    })