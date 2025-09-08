from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import (
    CadastroForm, PersonagemForm, PoderForm, InventarioForm,
    PersonagemNPCForm, PoderNPCFormSet
)
from .models import Personagem, Poder, Inventario
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.http import QueryDict
from django.forms import inlineformset_factory
from salas.models import Sala
from django.contrib import messages
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


PoderFormSet = inlineformset_factory(
    Personagem,
    Poder,
    form=PoderForm,
    extra=1,
    can_delete=True
)

def home(request):
    # Nova home: lista de salas
    return redirect('listar_salas')

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
    # Exige estar em uma sala
    sala_atual = None
    try:
        sala_atual = request.user.perfilusuario.sala_atual
    except Exception:
        sala_atual = None
    if not sala_atual:
        return redirect('listar_salas')
    if request.method == 'POST':
        form = PersonagemForm(request.POST, request.FILES)
        inventario_form = InventarioForm(request.POST)
        formset = PoderFormSet(request.POST, request.FILES, prefix='poder_set')
        if form.is_valid() and inventario_form.is_valid() and formset.is_valid():
            personagem = form.save(commit=False)
            personagem.usuario = request.user
            personagem.sala = sala_atual
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
    # Lista só personagens do usuário na sala atual
    sala_atual = None
    try:
        sala_atual = request.user.perfilusuario.sala_atual
    except Exception:
        sala_atual = None
    if not sala_atual:
        return redirect('listar_salas')
    personagens = Personagem.objects.filter(usuario=request.user, is_npc=False, sala=sala_atual)
    return render(request, 'personagens/listar_personagens.html', {'personagens': personagens, 'sala': sala_atual})


@login_required
def importar_personagem_lista(request):
    """Lista personagens do usuário em outras salas para importar (copiar) para a sala atual."""
    sala_atual = getattr(getattr(request.user, 'perfilusuario', None), 'sala_atual', None)
    if not sala_atual:
        return redirect('listar_salas')
    personagens = Personagem.objects.filter(usuario=request.user, is_npc=False).exclude(sala=sala_atual)
    return render(request, 'personagens/importar_personagem.html', {
        'personagens_outras_salas': personagens,
        'sala': sala_atual,
    })


def _clonar_personagem(orig: Personagem, sala_destino: Sala, dono):
    """Clona o personagem (e poderes/inventário/vantagens) para a sala_destino, mantendo o mesmo dono."""
    # Clona campos simples
    campos_simples = {
        'is_npc': orig.is_npc,
        'especialidade_casting_ability': orig.especialidade_casting_ability,
        'nome': orig.nome,
        'nivel_poder': orig.nivel_poder,
        'foto': orig.foto,
        # Características
        'forca': orig.forca,
        'vigor': orig.vigor,
        'destreza': orig.destreza,
        'agilidade': orig.agilidade,
        'luta': orig.luta,
        'inteligencia': orig.inteligencia,
        'prontidao': orig.prontidao,
        'presenca': orig.presenca,
        # Defesas
        'aparar': orig.aparar,
        'esquivar': orig.esquivar,
        'fortitude': orig.fortitude,
        'vontade': orig.vontade,
        'resistencia': orig.resistencia,
        'penalidade_resistencia': orig.penalidade_resistencia,
        'condicao': orig.condicao,
        # Perícias
        'acrobacias': orig.acrobacias,
        'atletismo': orig.atletismo,
        'combate_distancia': orig.combate_distancia,
        'combate_corpo': orig.combate_corpo,
        'enganacao': orig.enganacao,
        'especialidade': orig.especialidade,
        'furtividade': orig.furtividade,
        'intimidacao': orig.intimidacao,
        'intuicao': orig.intuicao,
        'investigacao': orig.investigacao,
        'percepcao': orig.percepcao,
        'persuasao': orig.persuasao,
        'prestidigitacao': orig.prestidigitacao,
        'tecnologia': orig.tecnologia,
        'tratamento': orig.tratamento,
        'veiculos': orig.veiculos,
        'historia': orig.historia,
        'sobrevivencia': orig.sobrevivencia,
    }
    novo = Personagem(**campos_simples)
    novo.usuario = dono
    novo.sala = sala_destino
    novo.is_npc = False  # Segurança: importação apenas de jogadores
    novo.full_clean(exclude=['usuario', 'sala'])
    novo.save()

    # Vantagens (M2M)
    novo.vantagens.set(orig.vantagens.all())

    # Inventário
    inv_orig = getattr(orig, 'inventario', None)
    inv_novo = Inventario.objects.create(personagem=novo)
    if inv_orig:
        inv_novo.ouro = inv_orig.ouro
        inv_novo.dragon_shard = inv_orig.dragon_shard
        inv_novo.save()
        inv_novo.itens.set(inv_orig.itens.all())

    # Poderes
    poderes_orig = list(orig.poderes.all())
    novos_poderes = []
    for p in poderes_orig:
        novos_poderes.append(Poder(
            personagem=novo,
            casting_ability=p.casting_ability,
            nome=p.nome,
            tipo=p.tipo,
            modo=p.modo,
            duracao=p.duracao,
            nivel_efeito=p.nivel_efeito,
            bonus_ataque=p.bonus_ataque,
            defesa_ativa=p.defesa_ativa,
            defesa_passiva=p.defesa_passiva,
            de_item=p.de_item,
            item_origem=p.item_origem,
            de_vantagem=p.de_vantagem,
            vantagem_origem=p.vantagem_origem,
        ))
    Poder.objects.bulk_create(novos_poderes)
    # Replica encadeamentos se existirem (campo pode não existir em versões antigas)
    try:
        mapa_old_new = {old.id: new for old, new in zip(poderes_orig, novos_poderes)}
        for old in poderes_orig:
            ligados_ids = list(getattr(old, 'ligados').values_list('id', flat=True)) if hasattr(old, 'ligados') else []
            if not ligados_ids:
                continue
            new = mapa_old_new.get(old.id)
            if not new:
                continue
            novos_ligados = [mapa_old_new[oid] for oid in ligados_ids if oid in mapa_old_new]
            if novos_ligados:
                new.ligados.set(novos_ligados)
    except Exception:
        pass
    return novo


@login_required
@transaction.atomic
def importar_personagem(request, personagem_id):
    """Copia um personagem do usuário de outra sala para a sala atual."""
    if request.method != 'POST':
        return redirect('importar_personagem_lista')
    sala_atual = getattr(getattr(request.user, 'perfilusuario', None), 'sala_atual', None)
    if not sala_atual:
        return redirect('listar_salas')
    orig = get_object_or_404(Personagem, id=personagem_id, usuario=request.user, is_npc=False)
    if orig.sala_id == sala_atual.id:
        messages.info(request, 'Este personagem já está na sala atual.')
        return redirect('importar_personagem_lista')
    novo = _clonar_personagem(orig, sala_atual, request.user)
    messages.success(request, f'Personagem "{novo.nome}" importado para a sala {sala_atual.nome}.')
    return redirect('listar_personagens')


@login_required
@transaction.atomic
def clonar_personagem_para_jogador(request, personagem_id):
    """Permite ao GM clonar um Personagem dele para um Jogador da sala atual."""
    personagem = get_object_or_404(Personagem, id=personagem_id, usuario=request.user)
    # Verifica sala atual e permissão de GM
    sala_atual = getattr(getattr(request.user, 'perfilusuario', None), 'sala_atual', None)
    if not sala_atual or personagem.sala_id != sala_atual.id or sala_atual.game_master_id != request.user.id:
        return redirect('listar_salas')

    jogadores_qs = sala_atual.jogadores.all().order_by('username')
    if request.method == 'POST':
        jogador_id = request.POST.get('jogador_id')
        nome_novo = (request.POST.get('nome') or '').strip()
        try:
            jogador = jogadores_qs.get(id=jogador_id)
        except Exception:
            messages.error(request, 'Selecione um jogador válido da sala.')
            return render(request, 'personagens/clonar_personagem.html', {
                'personagem': personagem,
                'sala': sala_atual,
                'jogadores': jogadores_qs,
                'nome_sugerido': personagem.nome,
            })
        try:
            novo = _clonar_personagem(personagem, sala_atual, jogador)
        except ValidationError as ve:
            messages.error(request, f'Não foi possível clonar: {"; ".join(sum(ve.message_dict.values(), [])) if hasattr(ve, "message_dict") else ", ".join(ve.messages)}')
            return render(request, 'personagens/clonar_personagem.html', {
                'personagem': personagem,
                'sala': sala_atual,
                'jogadores': jogadores_qs,
                'nome_sugerido': personagem.nome,
            })
        # Renomeia se informado
        if nome_novo and nome_novo != novo.nome:
            novo.nome = nome_novo
            novo.save(update_fields=['nome'])
        messages.success(request, f'Personagem "{personagem.nome}" clonado para {jogador.username} como "{novo.nome}".')
        return redirect('listar_personagens')

    return render(request, 'personagens/clonar_personagem.html', {
        'personagem': personagem,
        'sala': sala_atual,
        'jogadores': jogadores_qs,
        'nome_sugerido': personagem.nome,
    })


@login_required
def editar_personagem(request, personagem_id):
    personagem = get_object_or_404(Personagem, id=personagem_id, usuario=request.user)
    # Exige estar na sala do personagem
    sala_atual = None
    try:
        sala_atual = request.user.perfilusuario.sala_atual
    except Exception:
        sala_atual = None
    if not sala_atual or personagem.sala_id != sala_atual.id:
        return redirect('listar_salas')
    inventario, created = Inventario.objects.get_or_create(personagem=personagem)
    if request.method == 'POST':
        # Garante que ids dos poderes existentes estejam presentes no POST (workaround de template/JS)
        data = request.POST.copy() if not isinstance(request.POST, QueryDict) else request.POST.copy()
        try:
            initial_forms = int(data.get('poder_set-INITIAL_FORMS', '0'))
        except Exception:
            initial_forms = 0
        # Usa ordem determinística por pk
        existing_pks = list(personagem.poderes.order_by('pk').values_list('pk', flat=True))
        for i in range(min(initial_forms, len(existing_pks))):
            key = f'poder_set-{i}-id'
            if not data.get(key):
                data[key] = str(existing_pks[i])

        form = PersonagemForm(data, request.FILES, instance=personagem)
        inventario_form = InventarioForm(data, instance=inventario)
        formset = PoderFormSet(data, request.FILES, instance=personagem, prefix='poder_set')
        if form.is_valid() and inventario_form.is_valid() and formset.is_valid():
            personagem = form.save(commit=False)
            personagem.sala = sala_atual
            personagem.save()

            # Inventário: preservar itens selecionados no formulário E itens de poderes
            inv = inventario_form.save(commit=False)
            inv.personagem = personagem
            inv.save()
            # Limpa e remonta o conjunto de itens
            inv.itens.clear()
            itens_selecionados = list(inventario_form.cleaned_data.get('itens') or [])
            if itens_selecionados:
                inv.itens.add(*itens_selecionados)

            poderes = formset.save(commit=False)

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
                    inv.itens.add(poder.item_origem)

            # Processa exclusões do formset
            for obj in formset.deleted_objects:
                obj.delete()

            # Salva todas as vantagens (sem duplicidade)
            personagem.vantagens.set(vantagens_ids)

            # InlineFormSet não tem M2M, mas chamamos para consistência
            formset.save_m2m()
            return redirect('listar_personagens')
        else:
            # Surface concise error indicators via messages
            from django.forms.utils import ErrorDict
            def _count_errors(f):
                if hasattr(f, 'errors') and isinstance(f.errors, ErrorDict):
                    return sum(len(v) for v in f.errors.values()) + len(getattr(f, 'non_field_errors', lambda: [])())
                return 0
            total_err = _count_errors(form) + _count_errors(inventario_form)
            # formset errors: per-form + non-form
            fs_non = len(getattr(formset, 'non_form_errors', lambda: [])())
            fs_forms = sum(_count_errors(f) for f in formset.forms)
            total_err += fs_non + fs_forms
            # Collect detailed errors for logging and optional short preview
            details = []
            for e in form.non_field_errors():
                details.append(f"form: {e}")
            for name, errs in form.errors.items():
                for e in errs:
                    details.append(f"form.{name}: {e}")
            for e in inventario_form.non_field_errors():
                details.append(f"inventario: {e}")
            for name, errs in inventario_form.errors.items():
                for e in errs:
                    details.append(f"inventario.{name}: {e}")
            for e in formset.non_form_errors():
                details.append(f"formset: {e}")
            for idx, f in enumerate(formset.forms):
                for e in f.non_field_errors():
                    details.append(f"poder[{idx}]: {e}")
                for name, errs in f.errors.items():
                    for e in errs:
                        details.append(f"poder[{idx}].{name}: {e}")
            if details:
                logger.warning("[editar_personagem] Falha de validação (%d):\n%s", total_err, "\n".join(details))
            # Debug: log IDs enviados pelo cliente para cada form do formset
            try:
                # Log management form values
                for k in [
                    'poder_set-TOTAL_FORMS',
                    'poder_set-INITIAL_FORMS',
                    'poder_set-MIN_NUM_FORMS',
                    'poder_set-MAX_NUM_FORMS',
                ]:
                    if k in request.POST:
                        logger.warning("[editar_personagem] POST %s=%s", k, request.POST.get(k))
                for f in formset.forms:
                    pid = request.POST.get(f"{f.prefix}-id")
                    pid_list = request.POST.getlist(f"{f.prefix}-id")
                    logger.warning("[editar_personagem] POST %s-id=%s", f.prefix, pid)
                    if pid_list and (len(pid_list) > 1 or (pid_list and pid_list[0] != pid)):
                        logger.warning("[editar_personagem] POST %s-id getlist=%s", f.prefix, pid_list)
                # Dump all poder_set-* fields for debugging names/values
                keys = sorted([k for k in request.POST.keys() if k.startswith('poder_set-')])
                for k in keys:
                    # Don't spam with large textareas; log only short values
                    v = request.POST.getlist(k)
                    vs = v if len(v) > 1 else (v[0] if v else '')
                    logger.warning("[editar_personagem] POST %s => %s", k, vs)
            except Exception:
                pass
            if total_err:
                preview = "; ".join(details[:3]) if details else ""
                if preview:
                    messages.error(request, f'Erros ao salvar: {total_err}. Ex.: {preview}')
                else:
                    messages.error(request, f'Erros ao salvar: {total_err}. Verifique os destaques no formulário abaixo.')
    else:
        # GET: prepara formulários preenchidos
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
    # Permite excluir somente dentro da sala do personagem
    sala_atual = None
    try:
        sala_atual = request.user.perfilusuario.sala_atual
    except Exception:
        sala_atual = None
    if not sala_atual or personagem.sala_id != sala_atual.id:
        return redirect('listar_salas')
    if request.method == 'POST':
        personagem.delete()
        return redirect('listar_personagens')
    return render(request, 'personagens/excluir_personagem.html', {'personagem': personagem})

@login_required
def visualizar_personagem(request, personagem_id):
    personagem = get_object_or_404(Personagem, id=personagem_id, usuario=request.user)
    sala_atual = None
    try:
        sala_atual = request.user.perfilusuario.sala_atual
    except Exception:
        sala_atual = None
    if not sala_atual or personagem.sala_id != sala_atual.id:
        return redirect('listar_salas')
    return render(request, 'personagens/visualizar_personagem.html', {'personagem': personagem})

@login_required
def ficha_personagem(request, personagem_id):
    personagem = get_object_or_404(Personagem, pk=personagem_id)
    sala_atual = None
    try:
        sala_atual = request.user.perfilusuario.sala_atual
    except Exception:
        sala_atual = None
    # Permissões: dono do personagem na sala atual OU GM da sala do personagem estando na sala
    is_dono = personagem.usuario_id == request.user.id
    is_gm_da_sala = sala_atual and personagem.sala_id == sala_atual.id and sala_atual.game_master_id == request.user.id
    if not sala_atual or personagem.sala_id != sala_atual.id or (not is_dono and not is_gm_da_sala):
        return redirect('listar_salas')
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
        'poderes_de_item': poderes_de_item,
        'pode_editar': is_dono,
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
            npc.is_npc = True  # garante bypass de validações do modelo
            npc.usuario = request.user
            npc.sala = sala
            npc.save()
            poderes = formset.save(commit=False)
            for poder in poderes:
                poder.personagem = npc
                poder.save()
            formset.save_m2m()
            return redirect('listar_npcs')
        else:
            # Notifica o usuário sobre erros ao salvar NPC
            from django.forms.utils import ErrorDict
            def _count_errors(f):
                if hasattr(f, 'errors') and isinstance(f.errors, ErrorDict):
                    return sum(len(v) for v in f.errors.values()) + len(getattr(f, 'non_field_errors', lambda: [])())
                return 0
            total_err = _count_errors(form)
            fs_non = len(getattr(formset, 'non_form_errors', lambda: [])())
            fs_forms = sum(_count_errors(f) for f in formset.forms)
            total_err += fs_non + fs_forms
            # Log resumido e mensagem ao usuário
            details = []
            for e in form.non_field_errors():
                details.append(f"form: {e}")
            for name, errs in form.errors.items():
                for e in errs:
                    details.append(f"form.{name}: {e}")
            for e in formset.non_form_errors():
                details.append(f"formset: {e}")
            for idx, f in enumerate(formset.forms):
                for name, errs in f.errors.items():
                    for e in errs:
                        details.append(f"poder[{idx}].{name}: {e}")
            if details:
                logger.warning("[criar_npc] Falha de validação (%d):\n%s", total_err, "\n".join(details))
            preview = "; ".join(details[:3]) if details else ""
            if preview:
                messages.error(request, f'Erros ao salvar NPC: {total_err}. Ex.: {preview}')
            else:
                messages.error(request, f'Erros ao salvar NPC: {total_err}. Verifique os destaques no formulário.')
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
    # Apenas o GM pode ver seus próprios NPCs da sala atual
    sala_atual = None
    try:
        sala_atual = request.user.perfilusuario.sala_atual
    except Exception:
        sala_atual = None
    if not sala_atual:
        return redirect('listar_salas')
    npcs = Personagem.objects.filter(usuario=request.user, is_npc=True, sala=sala_atual).order_by('nome')
    return render(request, 'personagens/listar_npcs.html', {'npcs': npcs, 'sala': sala_atual})


@login_required
def editar_npc(request, personagem_id):
    npc = get_object_or_404(Personagem, id=personagem_id, usuario=request.user, is_npc=True)
    sala_atual = None
    try:
        sala_atual = request.user.perfilusuario.sala_atual
    except Exception:
        sala_atual = None
    if not sala_atual or npc.sala_id != sala_atual.id:
        return redirect('listar_salas')
    if request.method == 'POST':
        # Preenche ids dos poderes existentes se ausentes no POST
        data = request.POST.copy()
        try:
            initial_forms = int(data.get('poder_set-INITIAL_FORMS', '0'))
        except Exception:
            initial_forms = 0
        existing_pks = list(npc.poderes.order_by('pk').values_list('pk', flat=True))
        for i in range(min(initial_forms, len(existing_pks))):
            key = f'poder_set-{i}-id'
            if not data.get(key):
                data[key] = str(existing_pks[i])

        form = PersonagemNPCForm(data, request.FILES, instance=npc)
        formset = PoderNPCFormSet(data, request.FILES, instance=npc, prefix='poder_set')
        if form.is_valid() and formset.is_valid():
            npc = form.save(commit=False)
            npc.is_npc = True  # garante bypass de validações do modelo
            npc.usuario = request.user
            npc.sala = sala_atual
            npc.save()
            formset.save()
            return redirect('listar_npcs')
        else:
            from django.forms.utils import ErrorDict
            def _count_errors(f):
                if hasattr(f, 'errors') and isinstance(f.errors, ErrorDict):
                    return sum(len(v) for v in f.errors.values()) + len(getattr(f, 'non_field_errors', lambda: [])())
                return 0
            total_err = _count_errors(form)
            fs_non = len(getattr(formset, 'non_form_errors', lambda: [])())
            fs_forms = sum(_count_errors(f) for f in formset.forms)
            total_err += fs_non + fs_forms
            details = []
            for e in form.non_field_errors():
                details.append(f"form: {e}")
            for name, errs in form.errors.items():
                for e in errs:
                    details.append(f"form.{name}: {e}")
            for e in formset.non_form_errors():
                details.append(f"formset: {e}")
            for idx, f in enumerate(formset.forms):
                for name, errs in f.errors.items():
                    for e in errs:
                        details.append(f"poder[{idx}].{name}: {e}")
            if details:
                logger.warning("[editar_npc] Falha de validação (%d):\n%s", total_err, "\n".join(details))
            # Log básico dos ids postados
            try:
                if 'poder_set-INITIAL_FORMS' in request.POST:
                    logger.warning("[editar_npc] POST poder_set-INITIAL_FORMS=%s", request.POST.get('poder_set-INITIAL_FORMS'))
                for f in formset.forms:
                    pid = request.POST.get(f"{f.prefix}-id")
                    logger.warning("[editar_npc] POST %s-id=%s", f.prefix, pid)
            except Exception:
                pass
            preview = "; ".join(details[:3]) if details else ""
            if preview:
                messages.error(request, f'Erros ao salvar NPC: {total_err}. Ex.: {preview}')
            else:
                messages.error(request, f'Erros ao salvar NPC: {total_err}. Verifique os destaques no formulário.')
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
    sala_atual = None
    try:
        sala_atual = request.user.perfilusuario.sala_atual
    except Exception:
        sala_atual = None
    if not sala_atual or npc.sala_id != sala_atual.id:
        return redirect('listar_salas')
    if request.method == 'POST':
        npc.delete()
        return redirect('listar_npcs')
    return render(request, 'personagens/excluir_npc.html', {'npc': npc})



