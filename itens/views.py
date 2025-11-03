from django.shortcuts import render, redirect, get_object_or_404
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
    # Verifica permissão de GM na sala atual
    is_gm = False
    try:
        if sala_atual and sala_atual.game_master_id == request.user.id:
            is_gm = True
    except Exception:
        is_gm = False
    if not sala_atual:
        # Usuário fora de sala: só pode ver itens base; sem criar
        itens = Item.objects.filter(sala__isnull=True)
        pode_criar = False
    else:
        # Usuário em sala: vê itens base + da sala
        itens = Item.objects.filter(models.Q(sala__isnull=True) | models.Q(sala=sala_atual))
        pode_criar = True

    # Suporte a edição: quando ?edit=<id> e usuário é GM da sala do item
    edit_id = request.GET.get('edit')
    item_edit = None
    if edit_id:
        try:
            cand = get_object_or_404(Item, pk=edit_id)
            if is_gm and cand.sala_id == (sala_atual.id if sala_atual else None):
                item_edit = cand
        except Exception:
            item_edit = None

    # Helper para inicializar o ItemModsForm com base no JSON mods do item
    def mods_initial_from_item(it: Item):
        data = {}
        if not it or not it.mods:
            return data
        try:
            car = (it.mods or {}).get('caracteristicas', {})
            defe = (it.mods or {}).get('defesas', {})
            per = (it.mods or {}).get('pericias', {})
            for k, v in (car or {}).items():
                data[k] = v
            for k, v in (defe or {}).items():
                data[k] = v
            for k, v in (per or {}).items():
                data[k] = v
        except Exception:
            pass
        return data

    # Fluxo de POST: criação ou edição
    if request.method == 'POST':
        post_item_id = request.POST.get('item_id')
        if post_item_id:
            # Edição de item existente (restrita a GM e item da sala)
            alvo = get_object_or_404(Item, pk=post_item_id)
            if not (is_gm and sala_atual and alvo.sala_id == sala_atual.id):
                # Sem permissão: ignora edição e redireciona
                return redirect('itens')
            form = ItemForm(request.POST, instance=alvo)
            mods_form = ItemModsForm(request.POST)
            formset = ItemPoderFormSet(request.POST, instance=alvo, prefix='itempoder')
            if form.is_valid() and mods_form.is_valid() and formset.is_valid():
                item = form.save(commit=False)
                # Garante vinculação à sala atual (não permitir mover de sala)
                item.sala = sala_atual
                item.save()
                item.mods = mods_form.to_mods()
                item.save()
                formset.instance = item
                formset.save()
                return redirect('itens')
            else:
                # Renderiza com erros em modo edição
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
                    'is_gm': is_gm,
                    'sala_atual': sala_atual,
                    'item_edit': alvo,
                })
        else:
            # Criação padrão
            form = ItemForm(request.POST)
            mods_form = ItemModsForm(request.POST)
            formset = ItemPoderFormSet(request.POST, prefix='itempoder')
            if pode_criar and form.is_valid() and mods_form.is_valid() and formset.is_valid():
                item = form.save(commit=False)
                item.sala = sala_atual
                item.save()
                item.mods = mods_form.to_mods()
                item.save()
                formset.instance = item
                formset.save()
                return redirect('itens')
            # Se criação inválida, cai para render padrão com erros
    else:
        # GET: preenche formulários (com edição se presente e permitida)
        if item_edit:
            form = ItemForm(instance=item_edit)
            mods_form = ItemModsForm(initial=mods_initial_from_item(item_edit))
            formset = ItemPoderFormSet(instance=item_edit, prefix='itempoder')
        else:
            form = ItemForm()
            mods_form = ItemModsForm()
            formset = ItemPoderFormSet(prefix='itempoder')

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
        'is_gm': is_gm,
        'sala_atual': sala_atual,
        'item_edit': item_edit,
    })