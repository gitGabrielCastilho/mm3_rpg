from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import CadastroForm, PersonagemForm, PoderForm, InventarioForm
from .models import Personagem, Poder, Inventario
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory


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
            for poder in poderes:
                poder.personagem = personagem
                poder.save()
                # Adiciona item ao inventário se for poder de item
                if getattr(poder, 'de_item', False) and getattr(poder, 'item_origem', None):
                    inventario.itens.add(poder.item_origem)
            formset.save_m2m()
            return redirect('listar_personagens')
    else:
        form = PersonagemForm()
        inventario_form = InventarioForm()
        formset = PoderFormSet(prefix='poder_set')

    context = {
        'form': form,
        'inventario_form': inventario_form,
        'formset': formset,
        'caracteristicas': [
            'forca', 'vigor', 'destreza', 'agilidade', 'luta', 'inteligencia', 'prontidao', 'presenca'
        ],
        'defesas': ['aparar', 'esquivar', 'fortitude', 'vontade', 'resistencia'],
        'pericias': [
            'acrobacias', 'atletismo', 'combate_distancia', 'combate_corpo', 'enganacao',
            'especialidade', 'furtividade', 'intimidacao', 'intuicao', 'investigacao',
            'percepcao', 'persuasao', 'prestidigitacao', 'tecnologia', 'tratamento',
            'veiculos', 'historia', 'sobrevivencia'
        ]
    }
    return render(request, 'personagens/criar_personagem.html', context)


@login_required
def listar_personagens(request):
    personagens = Personagem.objects.filter(usuario=request.user)
    return render(request, 'personagens/listar_personagens.html', {'personagens': personagens})


@login_required
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
            for poder in poderes:
                poder.personagem = personagem
                poder.save()
                # Adiciona item ao inventário se for poder de item
                if getattr(poder, 'de_item', False) and getattr(poder, 'item_origem', None):
                    inventario.itens.add(poder.item_origem)
            formset.save_m2m()
            return redirect('listar_personagens')
    else:
        form = PersonagemForm(instance=personagem)
        inventario_form = InventarioForm(instance=inventario)
        formset = PoderFormSet(instance=personagem, prefix='poder_set')

    context = {
        'form': form,
        'inventario_form': inventario_form,
        'formset': formset,
        'caracteristicas': [
            'forca', 'vigor', 'destreza', 'agilidade', 'luta', 'inteligencia', 'prontidao', 'presenca'
        ],
        'defesas': ['aparar', 'esquivar', 'fortitude', 'vontade', 'resistencia'],
        'pericias': [
            'acrobacias', 'atletismo', 'combate_distancia', 'combate_corpo', 'enganacao',
            'especialidade', 'furtividade', 'intimidacao', 'intuicao', 'investigacao',
            'percepcao', 'persuasao', 'prestidigitacao', 'tecnologia', 'tratamento',
            'veiculos', 'historia', 'sobrevivencia'
        ]
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



