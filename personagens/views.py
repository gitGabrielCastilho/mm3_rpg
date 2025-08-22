from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import (
    CadastroForm, PersonagemForm, PoderForm, InventarioForm,
    PersonagemNPCForm, PoderNPCFormSet
)
from .models import Personagem, Poder, Inventario
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from salas.models import Sala


PoderFormSet = inlineformset_factory(
    Personagem,
    Poder,
    form=PoderForm,
    extra=1,
    can_delete=True
)

def home(request):
    return render(request, 'home.html')

def cadastrar_usuario(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CadastroForm()
    return render(request, 'registration/cadastro.html', {'form': form})


@login_required
def criar_personagem(request):
    if request.method == 'POST':
        form = PersonagemForm(request.POST, request.FILES)
        inventario_form = InventarioForm(request.POST)
        formset = PoderFormSet(request.POST, request.FILES, prefix='poder_set')
        if form.is_valid() and inventario_form.is_valid() and formset.is_valid():
            personagem = form.save(commit=False)
            personagem.usuario = request.user
            personagem.save()
            inventario = inventario_form.save(commit=False)
            inventario.personagem = personagem
            inventario.save()
            inventario_form.save_m2m()
            poderes = formset.save(commit=False)

            # Coleta vantagens selecionadas manualmente
            vantagens_ids = set(request.POST.getlist('vantagens'))
            personagem.vantagens.set(vantagens_ids)
            # Salva os poderes e coleta vantagens de origem dos poderes
            for poder in poderes:
                poder.personagem = personagem
                poder.save()
                if getattr(poder, 'de_vantagem', False) and getattr(poder, 'vantagem_origem', None):
                    vantagens_ids.add(str(poder.vantagem_origem.id))
                if getattr(poder, 'de_item', False) and getattr(poder, 'item_origem', None):
                    inventario.itens.add(poder.item_origem)

            # Salva todas as vantagens (sem duplicidade)
            personagem.vantagens.set(vantagens_ids)

            formset.save_m2m()
            return redirect('listar_personagens')
    else:
        form = PersonagemForm()
        inventario_form = InventarioForm()
        formset = PoderFormSet(prefix='poder_set')

    pericias = [
        'acrobacias', 'atletismo', 'combate_distancia', 'combate_corpo', 'enganacao',
        'especialidade', 'furtividade', 'intimidacao', 'intuicao', 'investigacao',
        'percepcao', 'persuasao', 'prestidigitacao', 'tecnologia', 'tratamento',
        'veiculos', 'historia', 'sobrevivencia'
    ]
    meio = len(pericias) // 2 + len(pericias) % 2
    pericias_col1 = pericias[:meio]
    pericias_col2 = pericias[meio:]
    context = {
        'form': form,
        'inventario_form': inventario_form,
        'formset': formset,
        'itens_possuido_ids': [],
        'caracteristicas': [
            'forca', 'vigor', 'destreza', 'agilidade', 'luta', 'inteligencia', 'prontidao', 'presenca'
        ],
        'defesas': ['aparar', 'esquivar', 'fortitude', 'vontade', 'resistencia'],
        'pericias_col1': pericias_col1,
        'pericias_col2': pericias_col2,
    }
    return render(request, 'personagens/criar_personagem.html', context)


@login_required
def listar_personagens(request):
    personagens = Personagem.objects.filter(usuario=request.user)
    return render(request, 'personagens/listar_personagens.html', {'personagens': personagens})


@login_required
def editar_personagem(request, personagem_id):
    personagem = get_object_or_404(Personagem, id=personagem_id, usuario=request.user)
    inventario, created = Inventario.objects.get_or_create(personagem=personagem)
    if request.method == 'POST':
        form = PersonagemForm(request.POST, request.FILES, instance=personagem)
        inventario_form = InventarioForm(request.POST, instance=inventario)
        formset = PoderFormSet(request.POST, request.FILES, instance=personagem, prefix='poder_set')
        if form.is_valid() and inventario_form.is_valid() and formset.is_valid():
            personagem = form.save()
            inventario = inventario_form.save()
            poderes = formset.save(commit=False)

            # Limpa itens de origem antes de atualizar
            inventario.itens.clear()

            # Coleta vantagens selecionadas manualmente
            vantagens_ids = set(request.POST.getlist('vantagens'))

            for poder in poderes:
                poder.personagem = personagem
                poder.save()
                # Adiciona vantagem ao personagem se for poder de vantagem
                if getattr(poder, 'de_vantagem', False) and getattr(poder, 'vantagem_origem', None):
                    vantagens_ids.add(str(poder.vantagem_origem.id))
                # Adiciona item ao inventário se for poder de item
                if getattr(poder, 'de_item', False) and getattr(poder, 'item_origem', None):
                    inventario.itens.add(poder.item_origem)

            # Salva todas as vantagens (sem duplicidade)
            personagem.vantagens.set(vantagens_ids)

            formset.save_m2m()
            return redirect('listar_personagens')
    # Se inválido, segue para renderização com dados atuais
    else:
        form = PersonagemForm(instance=personagem)
        inventario_form = InventarioForm(instance=inventario)
        formset = PoderFormSet(instance=personagem, prefix='poder_set')

    pericias = [
        'acrobacias', 'atletismo', 'combate_distancia', 'combate_corpo', 'enganacao',
        'especialidade', 'furtividade', 'intimidacao', 'intuicao', 'investigacao',
        'percepcao', 'persuasao', 'prestidigitacao', 'tecnologia', 'tratamento',
        'veiculos', 'historia', 'sobrevivencia'
    ]
    meio = len(pericias) // 2 + len(pericias) % 2
    pericias_col1 = pericias[:meio]
    pericias_col2 = pericias[meio:]
    # Pré-computa IDs de itens possuídos para evitar checagens caras no template
    itens_possuido_ids = set(inventario.itens.values_list('id', flat=True))

    context = {
        'form': form,
        'inventario_form': inventario_form,
        'formset': formset,
        'itens_possuido_ids': list(itens_possuido_ids),
        'caracteristicas': [
            'forca', 'vigor', 'destreza', 'agilidade', 'luta', 'inteligencia', 'prontidao', 'presenca'
        ],
        'defesas': ['aparar', 'esquivar', 'fortitude', 'vontade', 'resistencia'],
        'pericias_col1': pericias_col1,
        'pericias_col2': pericias_col2,
    }
    return render(request, 'personagens/editar_personagem.html', context)


@login_required
def excluir_personagem(request, personagem_id):
    personagem = get_object_or_404(Personagem, id=personagem_id, usuario=request.user)
    if request.method == 'POST':
        personagem.delete()
        return redirect('listar_personagens')
    return render(request, 'personagens/excluir_personagem.html', {'personagem': personagem})

@login_required
def visualizar_personagem(request, personagem_id):
    personagem = get_object_or_404(Personagem, id=personagem_id, usuario=request.user)
    return render(request, 'personagens/visualizar_personagem.html', {'personagem': personagem})

@login_required
def ficha_personagem(request, personagem_id):
    personagem = get_object_or_404(Personagem, pk=personagem_id, usuario=request.user)
    poderes_de_item = poderes_de_item = personagem.poderes.filter(de_item=True)
    categorias = {
        'caracteristicas': ['forca', 'destreza', 'agilidade', 'luta', 'vigor', 'inteligencia', 'prontidao', 'presenca'],
        'defesas': ['aparar', 'esquivar', 'fortitude', 'vontade', 'resistencia'],
        'pericias': ['acrobacias', 'atletismo', 'combate_distancia','combate_corpo', 'enganacao', 'especialidade', 'furtividade',
    'intimidacao', 'intuicao', 'investigacao', 'percepcao', 'persuasao', 'prestidigitacao', 'tecnologia', 'tratamento', 'veiculos',
    'historia', 'sobrevivencia']
    }

    return render(request, 'personagens/ficha_personagem.html', {
        'personagem': personagem,
        'categorias': categorias,
        'poderes_de_item': poderes_de_item
    })


# ------- NPC: criação restrita ao GM da sala -------
@login_required
def criar_npc(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    if sala.game_master != request.user:
        return redirect('listar_salas')

    if request.method == 'POST':
        form = PersonagemNPCForm(request.POST, request.FILES)
        formset = PoderNPCFormSet(request.POST, request.FILES, prefix='poder_set')
        if form.is_valid() and formset.is_valid():
            npc = form.save(commit=False)
            # Dono será o GM para controle; sem vantagens/inventário
            npc.usuario = request.user
            npc.is_npc = True
            npc.save()
            poderes = formset.save(commit=False)
            for poder in poderes:
                poder.personagem = npc
                poder.save()
            formset.save_m2m()
            return redirect('listar_npcs')
    else:
        form = PersonagemNPCForm()
        formset = PoderNPCFormSet(prefix='poder_set')

    pericias = [
        'acrobacias', 'atletismo', 'combate_distancia', 'combate_corpo', 'enganacao',
        'especialidade', 'furtividade', 'intimidacao', 'intuicao', 'investigacao',
        'percepcao', 'persuasao', 'prestidigitacao', 'tecnologia', 'tratamento',
        'veiculos', 'historia', 'sobrevivencia'
    ]
    meio = len(pericias) // 2 + len(pericias) % 2
    context = {
        'form': form,
        'formset': formset,
        'caracteristicas': [
            'forca', 'vigor', 'destreza', 'agilidade', 'luta', 'inteligencia', 'prontidao', 'presenca'
        ],
        'defesas': ['aparar', 'esquivar', 'fortitude', 'vontade', 'resistencia'],
        'pericias_col1': pericias[:meio],
        'pericias_col2': pericias[meio:],
        'sala': sala,
    }
    return render(request, 'personagens/criar_npc.html', context)


@login_required
def listar_npcs(request):
    # Apenas o GM pode ver seus próprios NPCs
    npcs = Personagem.objects.filter(usuario=request.user, is_npc=True).order_by('nome')
    return render(request, 'personagens/listar_npcs.html', {'npcs': npcs})


@login_required
def editar_npc(request, personagem_id):
    npc = get_object_or_404(Personagem, id=personagem_id, usuario=request.user, is_npc=True)
    if request.method == 'POST':
        form = PersonagemNPCForm(request.POST, request.FILES, instance=npc)
        formset = PoderNPCFormSet(request.POST, request.FILES, instance=npc, prefix='poder_set')
        if form.is_valid() and formset.is_valid():
            npc = form.save(commit=False)
            npc.is_npc = True
            npc.usuario = request.user
            npc.save()
            formset.save()
            return redirect('listar_npcs')
    else:
        form = PersonagemNPCForm(instance=npc)
        formset = PoderNPCFormSet(instance=npc, prefix='poder_set')

    pericias = [
        'acrobacias', 'atletismo', 'combate_distancia', 'combate_corpo', 'enganacao',
        'especialidade', 'furtividade', 'intimidacao', 'intuicao', 'investigacao',
        'percepcao', 'persuasao', 'prestidigitacao', 'tecnologia', 'tratamento',
        'veiculos', 'historia', 'sobrevivencia'
    ]
    meio = len(pericias) // 2 + len(pericias) % 2
    context = {
        'form': form,
        'formset': formset,
        'caracteristicas': [
            'forca', 'vigor', 'destreza', 'agilidade', 'luta', 'inteligencia', 'prontidao', 'presenca'
        ],
        'defesas': ['aparar', 'esquivar', 'fortitude', 'vontade', 'resistencia'],
        'pericias_col1': pericias[:meio],
        'pericias_col2': pericias[meio:],
        'npc': npc,
    }
    return render(request, 'personagens/editar_npc.html', context)


@login_required
def excluir_npc(request, personagem_id):
    npc = get_object_or_404(Personagem, id=personagem_id, usuario=request.user, is_npc=True)
    if request.method == 'POST':
        npc.delete()
        return redirect('listar_npcs')
    return render(request, 'personagens/excluir_npc.html', {'npc': npc})



