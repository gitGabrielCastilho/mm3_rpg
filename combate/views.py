
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from .models import Combate, Turno, Participante
from personagens.models import Personagem, Poder
from django.utils import timezone
import random
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Mapa, PosicaoPersonagem
from .forms import MapaForm
from salas.models import Sala
import json
import logging

# Logger
logger = logging.getLogger(__name__)

try:  # Optional import for nicer error handling when using Cloudinary storage
    from cloudinary.exceptions import Error as CloudinaryError  # type: ignore
except Exception:  # pragma: no cover
    class CloudinaryError(Exception):  # fallback
        pass

# Heurística: cliente espera JSON quando é AJAX/fetch
def _expects_json(request) -> bool:
    if request.headers.get('x-requested-with', '').lower() == 'xmlhttprequest':
        return True
    accept = request.headers.get('accept', '')
    return 'application/json' in accept.lower()

"""Endpoints e views do combate."""

# AJAX: retorna poderes de um personagem (com verificação de permissão)
@login_required
def poderes_personagem_ajax(request):
    personagem_id = request.GET.get('personagem_id')
    if not personagem_id:
        return HttpResponseBadRequest('personagem_id obrigatório')
    try:
        personagem = Personagem.objects.get(id=personagem_id)
    except Personagem.DoesNotExist:
        return JsonResponse({'poderes': []})

    # Restringe o acesso: somente o dono do personagem ou GM podem ver os poderes
    is_gm = bool(getattr(getattr(request.user, 'perfilusuario', None), 'tipo', '') == 'game_master')
    if not is_gm and personagem.usuario_id != request.user.id:
        # Não revelar poderes de outros personagens para jogadores
        return JsonResponse({'poderes': []})

    poderes = list(Poder.objects.filter(personagem=personagem).values('id', 'nome', 'tipo'))
    return JsonResponse({'poderes': poderes})

def criar_combate(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id, game_master=request.user)
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or not request.user.salas_gm.exists():
        return redirect('home')
    if request.method == 'POST':
        personagem_ids = request.POST.getlist('personagens')
        personagens = Personagem.objects.filter(id__in=personagem_ids)

        combate = Combate.objects.create(sala=sala, ativo=True)

        ordem = []
        for personagem in personagens:
            iniciativa = random.randint(1, 20) + personagem.prontidao
            p = Participante.objects.create(personagem=personagem, combate=combate, iniciativa=iniciativa)
            ordem.append((p, iniciativa))

        # Notifica todos os participantes sobre o novo combate
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'combate_{combate.id}',
                {
                    'type': 'combate_message',
                    'message': json.dumps({'evento': 'novo_combate', 'descricao': f'Combate criado na sala {sala.nome}.'})
                }
            )
        except Exception:
            logger.warning("Falha ao enviar evento 'novo_combate' via Channels (ignorado)", exc_info=True)
        if _expects_json(request):
            return JsonResponse({'status': 'ok', 'evento': 'novo_combate', 'combate_id': combate.id, 'sala_id': sala.id})
        return redirect('detalhes_combate', combate_id=combate.id)

    personagens = Personagem.objects.all()
    return render(request, 'combate/criar_combate.html', {'personagens': personagens})


def detalhes_combate(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    participantes = (
        Participante.objects.filter(combate=combate)
        .select_related('personagem', 'personagem__usuario')
        .order_by('-iniciativa')
    )
    turnos = Turno.objects.filter(combate=combate).order_by('criado_em')  # ou por ordem
    turno_ativo = turnos.filter(ativo=True).first()
    mapas_globais = Mapa.objects.filter(combate__isnull=True, criado_por=request.user).order_by('-id')
    mapa = combate.mapas.first()
    posicoes = PosicaoPersonagem.objects.filter(mapa=mapa) if mapa else []

    # Não pré-carrega poderes do turno_ativo para evitar alternância no formulário.
    # O frontend busca via AJAX conforme o participante selecionado em "Ações de".
    poderes_disponiveis = []

    defesas_disponiveis = ["vontade", "fortitude", "resistencia", "aparar", "esquivar"]

    pericias = [
        'acrobacias', 'atletismo', 'combate_distancia', 'combate_corpo', 'enganacao',
        'especialidade', 'furtividade', 'intimidacao', 'intuicao', 'investigacao',
        'percepcao', 'persuasao', 'prestidigitacao', 'tecnologia', 'tratamento',
        'veiculos', 'historia', 'sobrevivencia'
    ]
    caracteristicas = [
        'forca', 'vigor', 'destreza', 'agilidade', 'luta', 'inteligencia', 'prontidao', 'presenca'
    ]

    # Gera nomes exibidos com numeração para participantes duplicados
    counts = {}
    for p in participantes:
        pid = p.personagem_id
        counts[pid] = counts.get(pid, 0) + 1
        if counts[pid] > 1:
            p.display_nome = f"{p.personagem.nome} ({counts[pid]})"
        else:
            p.display_nome = p.personagem.nome

    personagens_no_combate_ids = list(participantes.values_list('personagem_id', flat=True))
    if hasattr(request.user, 'perfilusuario') and request.user.perfilusuario.sala_atual and request.user.perfilusuario.sala_atual.game_master == request.user:
        # GM: personagens dos participantes da sala (exclui já adicionados) e NPCs próprios (sem exclusão p/ permitir múltiplos)
        sala = request.user.perfilusuario.sala_atual
        personagens_disponiveis = Personagem.objects.filter(usuario__in=sala.participantes.all(), is_npc=False).exclude(id__in=personagens_no_combate_ids)
        npcs_disponiveis = Personagem.objects.filter(usuario=request.user, is_npc=True).order_by('nome')
    else:
        personagens_disponiveis = Personagem.objects.filter(usuario=request.user, is_npc=False).exclude(id__in=personagens_no_combate_ids)
        npcs_disponiveis = Personagem.objects.none()
    
    context = {
        'combate': combate,
        'participantes': participantes,
        'turnos': turnos,
        'turno_ativo': turno_ativo,
        'poderes_disponiveis': poderes_disponiveis,  
        'defesas': defesas_disponiveis,
        'personagens_disponiveis': personagens_disponiveis,
    'npcs_disponiveis': npcs_disponiveis,
        'pericias': pericias,
        'caracteristicas': caracteristicas,
        'mapas_globais': mapas_globais,
        'mapa': mapa,
        'posicoes': posicoes,
    }

    return render(request, 'combate/detalhes_combate.html', context)
@csrf_exempt
@login_required
def atualizar_posicao_token(request, token_id):
    if request.method == "POST":
        posicao = get_object_or_404(PosicaoPersonagem, id=token_id)
        data = json.loads(request.body)
        posicao.x = int(data.get("x", posicao.x))
        posicao.y = int(data.get("y", posicao.y))
        posicao.save()
        # Notifica todos os participantes apenas sobre a movimentação do token (sem forçar refresh do mapa)
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'combate_{posicao.participante.combate.id}',
                {
                    'type': 'combate_message',
                    'message': json.dumps({
                        'evento': 'token_move',
                        'posicao_id': posicao.id,
                        'mapa_id': posicao.mapa.id if posicao.mapa_id else None,
                        'x': posicao.x,
                        'y': posicao.y,
                        'nome': posicao.participante.personagem.nome,
                    })
                }
            )
        except Exception:
            # Em dev, ignore falha de broadcast para não quebrar o movimento do token
            pass
        return JsonResponse({"status": "ok"})

@require_POST
def passar_turno(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    turnos = Turno.objects.filter(combate=combate).order_by('ordem')

    ativo = turnos.filter(ativo=True).first()

    if ativo:
        ativo.ativo = False
        ativo.save()

        proximo = turnos.filter(ordem__gt=ativo.ordem).first()
        if not proximo:
            proximo = turnos.first()

        proximo.ativo = True
        proximo.save()

    # Notifica todos os participantes sobre o avanço de turno
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'avancar_turno', 'descricao': 'Turno avançado.'})
            }
        )
    except Exception:
        logger.warning("Falha ao enviar evento 'avancar_turno' via Channels (ignorado)", exc_info=True)
    if _expects_json(request):
        return JsonResponse({'status': 'ok', 'evento': 'avancar_turno', 'combate_id': combate.id})
    return redirect('detalhes_combate', combate_id=combate.id)


@login_required
def listar_combates(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    # Verifica se o usuário está na sala (GM ou jogador)
    if sala.game_master != request.user and request.user not in sala.jogadores.all():
        return redirect('home')
    if sala.game_master == request.user:
        combates = Combate.objects.filter(sala=sala).order_by('-criado_em')
    else:
        personagens_usuario = Personagem.objects.filter(usuario=request.user)
        combates = Combate.objects.filter(sala=sala, participante__personagem__in=personagens_usuario).distinct().order_by('-criado_em')
    return render(request, 'combate/listar_combates.html', {'combates': combates, 'sala': sala})

@require_POST
def iniciar_turno(request, combate_id):
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or not request.user.salas_gm.exists():
        return redirect('home')
    combate = get_object_or_404(Combate, id=combate_id)
    participantes = Participante.objects.filter(combate=combate).order_by('-iniciativa')
    if not participantes.exists():
        messages.error(request, "Nenhum participante encontrado para iniciar o turno.")
        return redirect('detalhes_combate', combate_id=combate.id)

    primeiro_participante = participantes.first()
    Turno.objects.create(
        combate=combate,
        personagem=primeiro_participante.personagem,
        ordem=0,
        ativo=True
    )
    messages.success(request, f"Turno iniciado para {primeiro_participante.personagem.nome}.")
    # Notifica todos os participantes sobre o início do turno
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'iniciar_turno', 'descricao': f'Turno iniciado para {primeiro_participante.personagem.nome}.'})
            }
        )
    except Exception:
        logger.warning("Falha ao enviar evento 'iniciar_turno' via Channels (ignorado)", exc_info=True)
    if _expects_json(request):
        return JsonResponse({
            'status': 'ok',
            'evento': 'iniciar_turno',
            'combate_id': combate.id,
            'turno': {
                'personagem_id': primeiro_participante.personagem.id,
                'ordem': 0,
                'ativo': True,
            }
        })
    return redirect('detalhes_combate', combate_id=combate.id)


@require_POST
def avancar_turno(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    turnos = Turno.objects.filter(combate=combate).order_by('ordem')
    turno_ativo = turnos.filter(ativo=True).first()
    if turno_ativo:
        turno_ativo.ativo = False
        turno_ativo.save()
        participantes = Participante.objects.filter(combate=combate).order_by('-iniciativa')
        participante_ids = list(participantes.values_list('id', flat=True))
        personagem_ids = list(participantes.values_list('personagem_id', flat=True))
        if turno_ativo.personagem_id in personagem_ids:
            idx = personagem_ids.index(turno_ativo.personagem_id)
            proximo_idx = (idx + 1) % len(personagem_ids)
        else:
            proximo_idx = 0  
        personagem_proximo = participantes[proximo_idx].personagem
        Turno.objects.create(
            combate=combate,
            personagem=personagem_proximo,
            ordem=turno_ativo.ordem + 1,
            ativo=True
        )
        # Notifica todos os participantes sobre o avanço do turno
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'avancar_turno', 'descricao': f'Turno avançado para {personagem_proximo.nome}.'})
            }
        )
    if _expects_json(request):
        resp = {'status': 'ok', 'evento': 'avancar_turno', 'combate_id': combate.id}
        try:
            resp['turno'] = {
                'personagem_id': personagem_proximo.id,
                'ordem': turno_ativo.ordem + 1 if turno_ativo else 0,
                'ativo': True,
            }
        except Exception:
            pass
        return JsonResponse(resp)
    return redirect('detalhes_combate', combate_id=combate.id)


@require_POST
def finalizar_combate(request, combate_id):
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or not request.user.salas_gm.exists():
        return redirect('home')
    combate = get_object_or_404(Combate, id=combate_id)
    # Apenas o GM da sala deste combate pode finalizar
    if combate.sala.game_master != request.user:
        return redirect('home')
    combate.ativo = False
    combate.save()
    Turno.objects.filter(combate=combate, ativo=True).update(ativo=False)
    # Notifica todos os participantes sobre o fim do combate
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'finalizar_combate', 'descricao': 'Combate finalizado.'})
            }
        )
    except Exception:
        logger.warning("Falha ao enviar evento 'finalizar_combate' via Channels (ignorado)", exc_info=True)
    messages.success(request, "Combate finalizado.")
    if _expects_json(request):
        return JsonResponse({'status': 'ok', 'evento': 'finalizar_combate', 'combate_id': combate.id, 'sala_id': combate.sala.id})
    return redirect('listar_combates', sala_id=combate.sala.id)


@require_POST
def limpar_historico(request, combate_id):
    """GM-only: remove all Turno records for a combate, effectively clearing the attack log."""
    combate = get_object_or_404(Combate, id=combate_id)
    # Apenas o GM da sala pode limpar o histórico
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or combate.sala.game_master != request.user:
        return redirect('home')
    # Apaga todos os turnos deste combate
    Turno.objects.filter(combate=combate).delete()
    # Notifica clientes para atualizarem o histórico (tolerante a falhas)
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'limpar_historico', 'descricao': 'Histórico limpo pelo GM.'})
            }
        )
    except Exception:
        logger.warning("Falha ao enviar evento 'limpar_historico' via Channels (ignorado)", exc_info=True)
    if _expects_json(request):
        return JsonResponse({'status': 'ok', 'evento': 'limpar_historico', 'combate_id': combate.id})
    return redirect('detalhes_combate', combate_id=combate.id)


@login_required
def deletar_combate(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    sala_id = combate.sala.id
    # Apenas o GM da sala pode deletar um combate
    if combate.sala.game_master != request.user:
        return redirect('listar_combates', sala_id)
    if request.method == 'POST':
        combate.delete()
        if _expects_json(request):
            return JsonResponse({'status': 'ok', 'deleted': True, 'sala_id': sala_id})
        return redirect('listar_combates', sala_id)
    return render(request, 'combate/deletar_combate.html', {'combate': combate})









@login_required

@login_required
def adicionar_mapa_global(request):
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or not request.user.salas_gm.exists():
        return redirect('home')
    if request.method == 'POST':
        form = MapaForm(request.POST, request.FILES)
        if form.is_valid():
            mapa = form.save(commit=False)
            mapa.criado_por = request.user
            mapa.save()
            return redirect('listar_mapas')
    else:
        form = MapaForm()
    return render(request, 'combate/adicionar_mapa.html', {'form': form})

@login_required
def remover_mapa_global(request, mapa_id):
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or not request.user.salas_gm.exists():
        return redirect('home')
    mapa = get_object_or_404(Mapa, id=mapa_id, combate__isnull=True, criado_por=request.user)
    mapa.delete()
    return redirect('listar_mapas')

@login_required
def listar_mapas(request):
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or not request.user.salas_gm.exists():
        return redirect('home')
    mapas = Mapa.objects.filter(combate__isnull=True, criado_por=request.user).order_by('-id')
    return render(request, 'combate/listar_mapas.html', {'mapas': mapas})

@csrf_exempt
@login_required
def realizar_ataque(request, combate_id):
    if request.method != 'POST':
        return redirect('detalhes_combate', combate_id=combate_id)

    turno_ativo = Turno.objects.filter(combate_id=combate_id, ativo=True).first()
    resultados = []

    # Helper para registrar no turno ativo
    def append_to_turno(texto: str):
        nonlocal turno_ativo
        if not texto:
            return
        if turno_ativo:
            if turno_ativo.descricao:
                turno_ativo.descricao += "<br>" + texto
            else:
                turno_ativo.descricao = texto
            turno_ativo.save()
        else:
            messages.warning(request, "Ação realizada, mas não há turno ativo. Inicie um turno para registrar no histórico.")

    # Resolve atacante a partir de Participante.id (preferido) ou do turno ativo
    participante_atacante = None
    atacante = None
    personagem_acao_id = request.POST.get('personagem_acao')
    if personagem_acao_id:
        try:
            participante_atacante = Participante.objects.select_related('personagem').get(
                combate_id=combate_id, id=personagem_acao_id
            )
            atacante = participante_atacante.personagem
        except Participante.DoesNotExist:
            pass
    if not atacante and turno_ativo:
        atacante = turno_ativo.personagem
        participante_atacante = Participante.objects.filter(
            combate_id=combate_id, personagem=atacante
        ).order_by('-iniciativa').first()

    if not atacante or not participante_atacante:
        return redirect('detalhes_combate', combate_id=combate_id)

    # Segurança: somente o GM da sala ou o dono do personagem pode agir por ele
    combate = get_object_or_404(Combate, id=combate_id)
    is_gm = combate.sala.game_master == request.user
    if not is_gm and participante_atacante.personagem.usuario_id != request.user.id:
        if _expects_json(request):
            return JsonResponse({'status': 'error', 'error': 'Sem permissão para agir por este personagem.'}, status=403)
        return redirect('detalhes_combate', combate_id=combate_id)

    PERICIA_CARACTERISTICA = {
        'acrobacias': 'agilidade',
        'atletismo': 'forca',
        'combate_distancia': 'destreza',
        'combate_corpo': 'luta',
        'enganacao': 'presenca',
        'especialidade': 'casting_ability',
        'furtividade': 'agilidade',
        'intimidacao': 'presenca',
        'intuicao': 'prontidao',
        'investigacao': 'inteligencia',
        'percepcao': 'prontidao',
        'persuasao': 'presenca',
        'prestidigitacao': 'destreza',
        'tecnologia': 'inteligencia',
        'tratamento': 'inteligencia',
        'veiculos': 'destreza',
        'historia': 'inteligencia',
        'sobrevivencia': 'prontidao',
    }

    # Ramificações simples: perícia, característica e d20
    if request.POST.get('rolar_pericia'):
        pericia_escolhida = request.POST.get('pericia')
        if pericia_escolhida:
            valor_pericia = getattr(atacante, pericia_escolhida, None)
            buff = participante_atacante.bonus_temporario
            debuff = participante_atacante.penalidade_temporaria
            caracteristica_base = PERICIA_CARACTERISTICA.get(pericia_escolhida)
            if pericia_escolhida == 'especialidade':
                valor_caracteristica = getattr(atacante, getattr(atacante, 'especialidade_casting_ability', ''), 0)
                base_name = getattr(atacante, 'especialidade_casting_ability', 'especialidade')
            else:
                valor_caracteristica = getattr(atacante, caracteristica_base, 0)
                base_name = caracteristica_base
            if valor_pericia is not None:
                rolagem_base = random.randint(1, 20)
                total = rolagem_base + valor_pericia + valor_caracteristica + buff - debuff
                resultados.append(
                    f"{atacante.nome} rolou {pericia_escolhida.capitalize()}: {rolagem_base} + {valor_pericia} (perícia) + {valor_caracteristica} ({str(base_name).replace('_', ' ').capitalize()})"
                    f"{' + ' + str(buff) if buff else ''}"
                    f"{' - ' + str(debuff) if debuff else ''}"
                    f" = <b>{total}</b>"
                )
                participante_atacante.bonus_temporario = 0
                participante_atacante.penalidade_temporaria = 0
                participante_atacante.save()
            else:
                resultados.append(f"{atacante.nome} não possui a perícia {pericia_escolhida}.")
        else:
            resultados.append("Nenhuma perícia selecionada.")

        nova_descricao = "<br>".join(resultados)
        append_to_turno(nova_descricao)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate_id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'rolagem', 'descricao': nova_descricao})
            }
        )
        if _expects_json(request):
            return JsonResponse({'status': 'ok', 'evento': 'rolagem', 'descricao': nova_descricao})
        return redirect('detalhes_combate', combate_id=combate_id)

    if request.POST.get('rolar_caracteristica'):
        caracteristica_escolhida = request.POST.get('caracteristica')
        if caracteristica_escolhida:
            valor_caracteristica = getattr(atacante, caracteristica_escolhida, None)
            buff = participante_atacante.bonus_temporario
            debuff = participante_atacante.penalidade_temporaria
            if valor_caracteristica is not None:
                rolagem_base = random.randint(1, 20)
                total = rolagem_base + valor_caracteristica + buff - debuff
                resultados.append(
                    f"{atacante.nome} rolou {caracteristica_escolhida.capitalize()}: {rolagem_base} + {valor_caracteristica}"
                    f"{' + ' + str(buff) if buff else ''}"
                    f"{' - ' + str(debuff) if debuff else ''}"
                    f" = <b>{total}</b>"
                )
                participante_atacante.bonus_temporario = 0
                participante_atacante.penalidade_temporaria = 0
                participante_atacante.save()
            else:
                resultados.append(f"{atacante.nome} não possui a característica {caracteristica_escolhida}.")
        else:
            resultados.append("Nenhuma característica selecionada.")

        nova_descricao = "<br>".join(resultados)
        append_to_turno(nova_descricao)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate_id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'rolagem', 'descricao': nova_descricao})
            }
        )
        if _expects_json(request):
            return JsonResponse({'status': 'ok', 'evento': 'rolagem', 'descricao': nova_descricao})
        return redirect('detalhes_combate', combate_id=combate_id)

    if request.POST.get('rolar_d20'):
        rolagem_base = random.randint(1, 20)
        resultados.append(f"{atacante.nome} rolou um d20: <b>{rolagem_base}</b>")
        nova_descricao = "<br>".join(resultados)
        append_to_turno(nova_descricao)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate_id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'rolagem', 'descricao': nova_descricao})
            }
        )
        if _expects_json(request):
            return JsonResponse({'status': 'ok', 'evento': 'rolagem', 'descricao': nova_descricao})
        return redirect('detalhes_combate', combate_id=combate_id)

    # Poder com alvos (Participante IDs)
    alvo_ids = request.POST.getlist('alvo_id')
    poder_id = request.POST.get('poder_id')
    if poder_id:
        # Garante que o poder pertence ao atacante
        poder = get_object_or_404(Poder, id=poder_id, personagem=atacante)
        # Novo tipo: Descritivo — apenas gera rolagem/descrição, sem exigir alvos e sem efeitos
        if getattr(poder, 'tipo', '') == 'descritivo':
            # Apenas d20 + nível do poder descritivo (sem buffs/debuffs, sem alvo)
            rolagem_base = random.randint(1, 20)
            total = rolagem_base + int(getattr(poder, 'nivel_efeito', 0) or 0)
            resultados.append(
                f"{atacante.nome} usou {poder.nome} (Descritivo): {rolagem_base} + {poder.nivel_efeito} = <b>{total}</b>"
            )

            nova_descricao = "<br>".join(resultados)
            append_to_turno(nova_descricao)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'combate_{combate_id}',
                {
                    'type': 'combate_message',
                    'message': json.dumps({'evento': 'rolagem', 'descricao': nova_descricao})
                }
            )
            if _expects_json(request):
                return JsonResponse({'status': 'ok', 'evento': 'rolagem', 'descricao': nova_descricao})
            return redirect('detalhes_combate', combate_id=combate_id)

        # Demais tipos exigem alvos
        if not alvo_ids:
            # Sem alvos e não-descritivo: ignora esta ação
            return redirect('detalhes_combate', combate_id=combate_id)
        for alvo_id in alvo_ids:
            participante_alvo = get_object_or_404(Participante, id=alvo_id, combate_id=combate_id)
            alvo = participante_alvo.personagem

            # CURA
            if poder.tipo == 'cura':
                rolagem = random.randint(1, 20) + getattr(atacante, getattr(poder, 'casting_ability', ''), 0)
                cd = 10 - poder.nivel_efeito
                if rolagem >= cd:
                    if participante_alvo.dano >= participante_alvo.aflicao and participante_alvo.dano > 0:
                        participante_alvo.dano -= 1
                        resultado = f"{atacante.nome} curou {alvo.nome} (Rolagem {rolagem} vs CD {cd}): sucesso! Dano reduzido em 1."
                    elif participante_alvo.aflicao > participante_alvo.dano and participante_alvo.aflicao > 0:
                        participante_alvo.aflicao -= 1
                        resultado = f"{atacante.nome} curou {alvo.nome} (Rolagem {rolagem} vs CD {cd}): sucesso! Aflição reduzida em 1."
                    else:
                        resultado = f"{atacante.nome} curou {alvo.nome} (Rolagem {rolagem} vs CD {cd}): sucesso! Nada para curar."
                    participante_alvo.save()
                else:
                    resultado = f"{atacante.nome} tentou curar {alvo.nome} (Rolagem {rolagem} vs CD {cd}): falhou."

            # BUFF
            elif poder.tipo == 'buff':
                participante_alvo.bonus_temporario += poder.nivel_efeito
                participante_alvo.save()
                resultado = f"{alvo.nome} recebe um bônus de +{poder.nivel_efeito} na próxima rolagem."

            # DEBUFF
            elif poder.tipo == 'debuff':
                participante_alvo.penalidade_temporaria += poder.nivel_efeito
                participante_alvo.save()
                resultado = f"{alvo.nome} recebe uma penalidade de -{poder.nivel_efeito} na próxima rolagem."

            # ÁREA
            elif getattr(poder, 'modo', '') == 'area':
                esquiva = getattr(alvo, 'esquivar', 0)
                rolagem_esquiva_base = random.randint(1, 20)
                rolagem_esquiva = rolagem_esquiva_base + esquiva
                if poder.tipo == 'dano':
                    cd = poder.nivel_efeito + 15
                    cd_sucesso = (15 + poder.nivel_efeito) // 2
                else:
                    cd = poder.nivel_efeito + 10
                    cd_sucesso = (10 + poder.nivel_efeito) // 2
                if rolagem_esquiva < cd:
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    buff = participante_alvo.bonus_temporario
                    debuff = participante_alvo.penalidade_temporaria
                    rolagem_defesa_base = random.randint(1, 20)
                    rolagem_defesa = rolagem_defesa_base + defesa_valor + buff - debuff
                    participante_alvo.bonus_temporario = 0
                    participante_alvo.penalidade_temporaria = 0
                    participante_alvo.save()

                    defesa_msg = (
                        f"{rolagem_defesa_base} + {defesa_valor}"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f" = {rolagem_defesa}"
                    )

                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = (
                                f"{alvo.nome} falhou na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva}: {defesa_msg} <b>Sofreu 1 de dano!</b>"
                            )
                        else:
                            resultado = (
                                f"{alvo.nome} falhou na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva}: {defesa_msg} (sem dano)"
                            )
                    else:
                        if rolagem_defesa < cd:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = (
                                f"{alvo.nome} falhou na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva}: {defesa_msg} <b>Sofreu 1 de aflição!</b>"
                            )
                        else:
                            resultado = (
                                f"{alvo.nome} falhou na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva}: {defesa_msg} (sem aflição)"
                            )
                else:
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    buff = participante_alvo.bonus_temporario
                    debuff = participante_alvo.penalidade_temporaria
                    rolagem_defesa_base = random.randint(1, 20)
                    rolagem_defesa = rolagem_defesa_base + defesa_valor + buff - debuff
                    participante_alvo.bonus_temporario = 0
                    participante_alvo.penalidade_temporaria = 0
                    participante_alvo.save()

                    defesa_msg = (
                        f"{rolagem_defesa_base} + {defesa_valor}"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f" = {rolagem_defesa}"
                    )

                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd_sucesso:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = (
                                f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {defesa_msg} <b>Sofreu 1 de dano!</b>"
                            )
                        else:
                            resultado = (
                                f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {defesa_msg} (sem dano)"
                            )
                    else:
                        if rolagem_defesa < cd_sucesso:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = (
                                f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {defesa_msg} <b>Sofreu 1 de aflição!</b>"
                            )
                        else:
                            resultado = (
                                f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {defesa_msg} (sem aflição)"
                            )

            # PERCEPÇÃO
            elif getattr(poder, 'modo', '') == 'percepcao':
                if poder.tipo == 'dano':
                    cd = poder.nivel_efeito + 15
                else:
                    cd = poder.nivel_efeito + 10
                defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                buff = participante_alvo.bonus_temporario
                debuff = participante_alvo.penalidade_temporaria
                rolagem_defesa_base = random.randint(1, 20)
                rolagem_defesa = rolagem_defesa_base + defesa_valor + buff - debuff
                participante_alvo.bonus_temporario = 0
                participante_alvo.penalidade_temporaria = 0
                participante_alvo.save()

                defesa_msg = (
                    f"{rolagem_defesa_base} + {defesa_valor}"
                    f"{' + ' + str(buff) if buff else ''}"
                    f"{' - ' + str(debuff) if debuff else ''}"
                    f" = {rolagem_defesa}"
                )

                if poder.tipo == 'dano':
                    if rolagem_defesa < cd:
                        participante_alvo.dano += 1
                        participante_alvo.save()
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de dano!</b>"
                    else:
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem dano)"
                else:
                    if rolagem_defesa < cd:
                        participante_alvo.aflicao += 1
                        participante_alvo.save()
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de aflição!</b>"
                    else:
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem aflição)"

            # MELEE
            elif getattr(poder, 'modo', '') == 'melee':
                buff_atacante = participante_atacante.bonus_temporario
                debuff_atacante = participante_atacante.penalidade_temporaria
                ataque_base = random.randint(1, 20)
                ataque = ataque_base + poder.bonus_ataque + buff_atacante - debuff_atacante
                aparar = getattr(alvo, 'aparar', 0)
                participante_atacante.bonus_temporario = 0
                participante_atacante.penalidade_temporaria = 0
                participante_atacante.save()
                cd = (15 + poder.nivel_efeito) if poder.tipo == 'dano' else (10 + poder.nivel_efeito)
                if ataque > 10 + aparar:
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    buff = participante_alvo.bonus_temporario
                    debuff = participante_alvo.penalidade_temporaria
                    rolagem_defesa_base = random.randint(1, 20)
                    rolagem_defesa = rolagem_defesa_base + defesa_valor + buff - debuff
                    participante_alvo.bonus_temporario = 0
                    participante_alvo.penalidade_temporaria = 0
                    participante_alvo.save()

                    defesa_msg = (
                        f"{rolagem_defesa_base} + {defesa_valor}"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f" = {rolagem_defesa}"
                    )

                    ataque_msg = (
                        f"{ataque_base} + {poder.bonus_ataque}"
                        f"{' + ' + str(buff_atacante) if buff_atacante else ''}"
                        f"{' - ' + str(debuff_atacante) if debuff_atacante else ''}"
                        f" = {ataque}"
                    )

                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+aparar}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de dano!</b>"
                            )
                        else:
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+aparar}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem dano)"
                            )
                    else:
                        if rolagem_defesa < cd:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+aparar}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de aflição!</b>"
                            )
                        else:
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+aparar}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem aflição)"
                            )
                else:
                    ataque_msg = (
                        f"{ataque_base} + {poder.bonus_ataque}"
                        f"{' + ' + str(buff_atacante) if buff_atacante else ''}"
                        f"{' - ' + str(debuff_atacante) if debuff_atacante else ''}"
                        f" = {ataque}"
                    )
                    resultado = f"{atacante.nome} errou {alvo.nome} (ataque {ataque_msg} vs {10+aparar})"

            # RANGED
            elif getattr(poder, 'modo', '') == 'ranged':
                buff_atacante = participante_atacante.bonus_temporario
                debuff_atacante = participante_atacante.penalidade_temporaria
                ataque_base = random.randint(1, 20)
                ataque = ataque_base + poder.bonus_ataque + buff_atacante - debuff_atacante
                esquiva = getattr(alvo, 'esquivar', 0)
                participante_atacante.bonus_temporario = 0
                participante_atacante.penalidade_temporaria = 0
                participante_atacante.save()
                cd = (15 + poder.nivel_efeito) if poder.tipo == 'dano' else (10 + poder.nivel_efeito)
                if ataque > 10 + esquiva:
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    buff = participante_alvo.bonus_temporario
                    debuff = participante_alvo.penalidade_temporaria
                    rolagem_defesa_base = random.randint(1, 20)
                    rolagem_defesa = rolagem_defesa_base + defesa_valor + buff - debuff
                    participante_alvo.bonus_temporario = 0
                    participante_alvo.penalidade_temporaria = 0
                    participante_alvo.save()

                    defesa_msg = (
                        f"{rolagem_defesa_base} + {defesa_valor}"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f" = {rolagem_defesa}"
                    )

                    ataque_msg = (
                        f"{ataque_base} + {poder.bonus_ataque}"
                        f"{' + ' + str(buff_atacante) if buff_atacante else ''}"
                        f"{' - ' + str(debuff_atacante) if debuff_atacante else ''}"
                        f" = {ataque}"
                    )

                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+esquiva}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de dano!</b>"
                            )
                        else:
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+esquiva}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem dano)"
                            )
                    else:
                        if rolagem_defesa < cd:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+esquiva}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de aflição!</b>"
                            )
                        else:
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+esquiva}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem aflição)"
                            )
                else:
                    ataque_msg = (
                        f"{ataque_base} + {poder.bonus_ataque}"
                        f"{' + ' + str(buff_atacante) if buff_atacante else ''}"
                        f"{' - ' + str(debuff_atacante) if debuff_atacante else ''}"
                        f" = {ataque}"
                    )
                    resultado = f"{atacante.nome} errou {alvo.nome} (ataque {ataque_msg} vs {10+esquiva})"

            else:
                resultado = f"Ação inválida para o poder selecionado."

            resultados.append(resultado)

        nova_descricao = "<br>".join(resultados)
        append_to_turno(nova_descricao)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate_id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'rolagem', 'descricao': nova_descricao})
            }
        )
        if _expects_json(request):
            return JsonResponse({'status': 'ok', 'evento': 'rolagem', 'descricao': nova_descricao})
        return redirect('detalhes_combate', combate_id=combate_id)

    # Nenhuma ação válida enviada
    return redirect('detalhes_combate', combate_id=combate_id)

def adicionar_participante(request, combate_id):
    if not hasattr(request.user, 'perfilusuario') or not request.user.perfilusuario.sala_atual:
        return redirect('home')
    combate = get_object_or_404(Combate, id=combate_id)
    personagem_id = request.POST.get('personagem_id')
    sala = combate.sala
    if sala.game_master == request.user:
        personagem = get_object_or_404(Personagem, id=personagem_id, usuario__in=sala.participantes.all())
    else:
        personagem = get_object_or_404(Personagem, id=personagem_id, usuario=request.user)
    iniciativa = random.randint(1, 20) + personagem.prontidao
    participante = Participante.objects.create(personagem=personagem, combate=combate, iniciativa=iniciativa)
    mapa = combate.mapas.first()
    if mapa:
        PosicaoPersonagem.objects.create(mapa=mapa, participante=participante, x=10, y=10)
    # Notifica todos os participantes sobre a adição
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({
                    'evento': 'adicionar_participante',
                    'descricao': f'{personagem.nome} entrou no combate.',
                    'participante': {
                        'id': participante.id,
                        'personagem_id': personagem.id,
                        'nome': personagem.nome,
                        'usuario_id': personagem.usuario_id,
                        'is_npc': bool(getattr(personagem, 'is_npc', False)),
                    }
                })
            }
        )
    except Exception:
        logger.warning("Falha ao enviar evento 'adicionar_participante' via Channels (ignorado)", exc_info=True)
    if _expects_json(request):
        return JsonResponse({
            'status': 'ok',
            'evento': 'adicionar_participante',
            'combate_id': combate.id,
            'participante': {
                'id': participante.id,
                'personagem_id': personagem.id,
                'nome': personagem.nome,
                'iniciativa': iniciativa,
            }
        })
    return redirect('detalhes_combate', combate_id=combate_id)

def remover_participante(request, combate_id, participante_id):
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or not request.user.salas_gm.exists():
        return redirect('home')
    participante = get_object_or_404(Participante, id=participante_id, combate_id=combate_id)
    nome = participante.personagem.nome
    participante.delete()
    # Notifica todos os participantes sobre a remoção
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate_id}',
            {
                'type': 'combate_message',
                'message': json.dumps({
                    'evento': 'remover_participante',
                    'descricao': f'{nome} foi removido do combate.',
                    'participante_id': participante_id
                })
            }
        )
    except Exception:
        logger.warning("Falha ao enviar evento 'remover_participante' via Channels (ignorado)", exc_info=True)
    if _expects_json(request):
        return JsonResponse({'status': 'ok', 'evento': 'remover_participante', 'combate_id': combate_id, 'participante_id': participante_id, 'nome': nome})
    return redirect('detalhes_combate', combate_id=combate_id)

def adicionar_mapa(request, combate_id):
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or not request.user.salas_gm.exists():
        return redirect('home')
    combate = get_object_or_404(Combate, id=combate_id)
    mapas_globais = Mapa.objects.filter(combate__isnull=True, criado_por=request.user).order_by('-id')
    form = MapaForm()
    if request.method == 'POST':
        # Se o usuário clicou em "Usar Mapa Selecionado"
        if request.POST.get('usar_existente'):
            mapa_id = request.POST.get('mapa_existente')
            if mapa_id:
                mapa = get_object_or_404(Mapa, id=mapa_id, criado_por=request.user, combate__isnull=True)
                mapa.combate = combate
                try:
                    mapa.save()
                except Exception as e:
                    logger.exception("Erro ao vincular mapa existente ao combate")
                    msg = f"Erro ao vincular mapa: {e}"
                    if _expects_json(request):
                        return JsonResponse({"status": "error", "error": msg}, status=400)
                    from django.contrib import messages
                    messages.error(request, msg)
                    return render(request, 'combate/adicionar_mapa.html', {
                        'form': form,
                        'combate': combate,
                        'mapas_globais': mapas_globais,
                    }, status=400)
                # CRIA OS TOKENS PARA TODOS OS PARTICIPANTES JÁ EXISTENTES
                participantes = Participante.objects.filter(combate=combate)
                for participante in participantes:
                    if not PosicaoPersonagem.objects.filter(mapa=mapa, participante=participante).exists():
                        PosicaoPersonagem.objects.create(mapa=mapa, participante=participante, x=10, y=10)
                # Notifica todos os participantes sobre o novo mapa (tolerante a falhas)
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'combate_{combate.id}',
                        {
                            'type': 'combate_message',
                            'message': json.dumps({'evento': 'adicionar_mapa', 'descricao': f'Mapa {mapa.nome} adicionado ao combate.'})
                        }
                    )
                except Exception:
                    logger.warning("Falha ao enviar evento 'adicionar_mapa' pelo Channels", exc_info=True)
                if _expects_json(request):
                    return JsonResponse({'status': 'ok', 'evento': 'adicionar_mapa', 'combate_id': combate.id, 'mapa': {'id': mapa.id, 'nome': mapa.nome, 'url': mapa.imagem.url if getattr(mapa, 'imagem', None) else ''}})
                return redirect('detalhes_combate', combate_id=combate_id)
        else:
            # Se o usuário enviou um novo mapa
            form = MapaForm(request.POST, request.FILES)
            if form.is_valid():
                mapa = form.save(commit=False)
                mapa.combate = combate
                mapa.criado_por = request.user
                try:
                    mapa.save()
                except CloudinaryError as ce:
                    logger.exception("Falha ao enviar imagem do mapa para Cloudinary")
                    msg = f"Erro ao enviar imagem: {ce}"
                    if _expects_json(request):
                        return JsonResponse({"status": "error", "error": msg}, status=400)
                    from django.contrib import messages
                    messages.error(request, msg)
                    return render(request, 'combate/adicionar_mapa.html', {
                        'form': form,
                        'combate': combate,
                        'mapas_globais': mapas_globais,
                    }, status=400)
                except Exception as e:
                    logger.exception("Erro inesperado ao salvar Mapa")
                    msg = f"Erro inesperado ao salvar o mapa: {e}"
                    if _expects_json(request):
                        return JsonResponse({"status": "error", "error": msg}, status=500)
                    from django.contrib import messages
                    messages.error(request, msg)
                    return render(request, 'combate/adicionar_mapa.html', {
                        'form': form,
                        'combate': combate,
                        'mapas_globais': mapas_globais,
                    }, status=500)
                # CRIA OS TOKENS PARA TODOS OS PARTICIPANTES JÁ EXISTENTES
                participantes = Participante.objects.filter(combate=combate)
                for participante in participantes:
                    if not PosicaoPersonagem.objects.filter(mapa=mapa, participante=participante).exists():
                        PosicaoPersonagem.objects.create(mapa=mapa, participante=participante, x=10, y=10)
                # Notifica todos os participantes sobre o novo mapa (tolerante a falhas)
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'combate_{combate.id}',
                        {
                            'type': 'combate_message',
                            'message': json.dumps({'evento': 'adicionar_mapa', 'descricao': f'Mapa {mapa.nome} adicionado ao combate.'})
                        }
                    )
                except Exception:
                    logger.warning("Falha ao enviar evento 'adicionar_mapa' pelo Channels", exc_info=True)
                if _expects_json(request):
                    return JsonResponse({'status': 'ok', 'evento': 'adicionar_mapa', 'combate_id': combate.id, 'mapa': {'id': mapa.id, 'nome': mapa.nome, 'url': mapa.imagem.url if getattr(mapa, 'imagem', None) else ''}})
                return redirect('detalhes_combate', combate_id=combate_id)
    return render(request, 'combate/adicionar_mapa.html', {
        'form': form,
        'combate': combate,
        'mapas_globais': mapas_globais,
    })

def remover_mapa(request, combate_id, mapa_id):
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or not request.user.salas_gm.exists():
        return redirect('home')
    mapa = get_object_or_404(Mapa, id=mapa_id, combate_id=combate_id)
    nome = mapa.nome
    mapa.combate = None  # Apenas desvincula do combate
    mapa.save()
    # Notifica todos os participantes sobre a remoção do mapa (tolerante a falhas)
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate_id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'remover_mapa', 'descricao': f'Mapa {nome} removido do combate.'})
            }
        )
    except Exception:
        logger.warning("Falha ao enviar evento 'remover_mapa' pelo Channels", exc_info=True)
    if _expects_json(request):
        return JsonResponse({'status': 'ok', 'evento': 'remover_mapa', 'combate_id': combate_id, 'mapa_id': mapa_id, 'nome': nome})
    return redirect('detalhes_combate', combate_id=combate_id)

def adicionar_npc_participante(request, combate_id):
    # Apenas GM com sala atual pode adicionar NPC
    if not hasattr(request.user, 'perfilusuario') or not request.user.perfilusuario.sala_atual or request.user.perfilusuario.tipo != 'game_master':
        return redirect('home')
    combate = get_object_or_404(Combate, id=combate_id)
    sala = combate.sala
    if sala.game_master != request.user:
        return redirect('home')
    npc_id = request.POST.get('npc_id')
    npc = get_object_or_404(Personagem, id=npc_id, usuario=request.user, is_npc=True)
    iniciativa = random.randint(1, 20) + npc.prontidao
    participante = Participante.objects.create(personagem=npc, combate=combate, iniciativa=iniciativa)
    mapa = combate.mapas.first()
    if mapa:
        PosicaoPersonagem.objects.create(mapa=mapa, participante=participante, x=10, y=10)
    # Notifica todos
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({
                    'evento': 'adicionar_participante',
                    'descricao': f'{npc.nome} (NPC) entrou no combate.',
                    'participante': {
                        'id': participante.id,
                        'personagem_id': npc.id,
                        'nome': npc.nome,
                        'usuario_id': npc.usuario_id,
                        'is_npc': True,
                    }
                })
            }
        )
    except Exception:
        logger.warning("Falha ao enviar evento 'adicionar_participante' (NPC) via Channels (ignorado)", exc_info=True)
    if _expects_json(request):
        return JsonResponse({
            'status': 'ok',
            'evento': 'adicionar_participante',
            'combate_id': combate.id,
            'participante': {
                'id': participante.id,
                'personagem_id': npc.id,
                'nome': npc.nome,
                'iniciativa': iniciativa,
                'is_npc': True,
            }
        })
    return redirect('detalhes_combate', combate_id=combate_id)