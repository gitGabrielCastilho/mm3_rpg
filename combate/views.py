from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from .models import Combate, Turno, Participante
from personagens.models import Personagem, Poder
from django.utils import timezone
import random
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Mapa, PosicaoPersonagem, EfeitoConcentracao
from django.db.models import Q, F
from .forms import MapaForm, AtaqueForm
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

# --- Helpers para Aprimorar ---
def _atributo_efetivo(personagem: Personagem, participante: Participante, atributo: str, combate_id: int) -> int:
    """Retorna o valor do atributo considerando efeitos Aprimorar ativos para este alvo no combate.
    Regra: soma todos os nivel_efeito de poderes do tipo 'aprimorar' com casting_ability == atributo e ativos
    sobre este participante. Pode ultrapassar limites.
    """
    base = getattr(personagem, atributo, 0)
    try:
        efeitos = (
            EfeitoConcentracao.objects
            .filter(combate_id=combate_id, alvo_participante=participante, ativo=True, poder__tipo='aprimorar', poder__casting_ability=atributo)
            .select_related('poder')
        )
        bonus = sum(getattr(e.poder, 'nivel_efeito', 0) or 0 for e in efeitos)
        return base + int(bonus)
    except Exception:
        return base

# --- Helpers de defesa: inclui característica associada (aparar+luta, esquivar+agilidade, fortitude+vigor, resistencia+vigor, vontade+prontidao)
_DEFESA_ASSOC_MAP = {
    'aparar': 'luta',
    'esquivar': 'agilidade',
    'fortitude': 'vigor',
    'resistencia': 'vigor',
    'vontade': 'prontidao',
}

def _defesa_efetiva(personagem: Personagem, participante: Participante, defesa: str, combate_id: int) -> int:
    """Retorna o valor da defesa somando a característica associada.
    Ex.: Resistência = resistencia + vigor; Aparar = aparar + luta; Esquivar = esquivar + agilidade; etc.
    Ambos componentes consideram Aprimorar/Reduzir ativos.
    """
    val_def = _atributo_efetivo(personagem, participante, defesa, combate_id)
    assoc = _DEFESA_ASSOC_MAP.get(defesa)
    if assoc:
        val_def += _atributo_efetivo(personagem, participante, assoc, combate_id)
    return val_def

# AJAX: retorna poderes de um personagem (com verificação de permissão)
@login_required
def poderes_personagem_ajax(request):
    personagem_id = request.GET.get('personagem_id')
    # Seja tolerante com chamadas incompletas: devolve vazio em vez de 400
    if not personagem_id:
        return JsonResponse({'poderes': []})
    try:
        pid = int(personagem_id)
    except (TypeError, ValueError):
        return JsonResponse({'poderes': []})
    try:
        personagem = Personagem.objects.get(id=pid)
    except Personagem.DoesNotExist:
        return JsonResponse({'poderes': []})

    # Restringe o acesso: somente o dono do personagem ou GM podem ver os poderes
    is_gm = bool(getattr(getattr(request.user, 'perfilusuario', None), 'tipo', '') == 'game_master')
    if not is_gm and personagem.usuario_id != request.user.id:
        # Não revelar poderes de outros personagens para jogadores
        return JsonResponse({'poderes': []})

    # Agrupa poderes por nome para evitar duplicatas quando estão encadeados (ligados)
    # Regra: com a nova validação, somente poderes com MESMO nome podem estar ligados.
    poderes_qs = Poder.objects.filter(personagem=personagem).prefetch_related('ligados')
    grupos = {}
    for poder in poderes_qs:
        nome = poder.nome
        entry = grupos.get(nome)
        if not entry:
            grupos[nome] = {
                'id': poder.id,  # representante
                'nome': nome,
                'tipo': poder.tipo,
                'duracao': poder.duracao,
                'ids_equivalentes': set([poder.id])
            }
        else:
            # Se já existe um representante, só agrega o id
            entry['ids_equivalentes'].add(poder.id)
        # Também adiciona ids dos ligados (mesmo nome pela validação)
        for ligado in poder.ligados.all():
            grupos[nome]['ids_equivalentes'].add(ligado.id)
    poderes = []
    for g in grupos.values():
        poderes.append({
            'id': g['id'],
            'nome': g['nome'],
            'tipo': g['tipo'],
            'duracao': g['duracao'],
            'equivalentes': list(sorted(g['ids_equivalentes']))
        })
    poderes.sort(key=lambda x: x['nome'].lower())
    return JsonResponse({'poderes': poderes})

# JSON enxuto: lista de participantes (id, personagem_id, nome/display_nome) para sincronização leve sem recarregar formulário.
@login_required
def participantes_json(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    # Permissão: somente GM da sala ou jogadores da sala
    sala = combate.sala
    if sala.game_master != request.user and request.user not in sala.jogadores.all():
        return JsonResponse({'error': 'forbidden'}, status=403)
    participantes = (
        Participante.objects.filter(combate=combate)
        .select_related('personagem')
        .order_by('-iniciativa')
    )
    # Gera display_nome (mesma lógica de duplicados usada em detalhes_combate)
    counts = {}
    data = []
    for p in participantes:
        pid = p.personagem_id
        counts[pid] = counts.get(pid, 0) + 1
        if counts[pid] > 1:
            display_nome = f"{p.personagem.nome} ({counts[pid]})"
        else:
            display_nome = p.personagem.nome
        data.append({
            'id': p.id,
            'personagem_id': p.personagem_id,
            'nome': display_nome,
        })
    return JsonResponse({'participantes': data})

@login_required
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

    # Limita a lista de personagens: jogadores da sala (não-NPC) e NPCs do GM
    try:
        personagens = Personagem.objects.filter(
            Q(usuario__in=sala.participantes.all(), is_npc=False) | Q(usuario=sala.game_master, is_npc=True)
        ).distinct().order_by('nome')
    except Exception:
        personagens = Personagem.objects.none()
    return render(request, 'combate/criar_combate.html', {'personagens': personagens})


@login_required
def detalhes_combate(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    # Permissão: GM da sala ou jogadores pertencentes à sala
    sala = combate.sala
    if sala.game_master != request.user and request.user not in sala.jogadores.all():
        return redirect('home')
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
        'veiculos', 'historia', 'sobrevivencia', 'arcana', 'religiao'
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
    
    # Form de ataque com escopo de sala
    try:
        ataque_form = AtaqueForm(sala=sala)
        try:
            allowed_personagem_ids = list(ataque_form.fields['atacante'].queryset.values_list('id', flat=True))
        except Exception:
            allowed_personagem_ids = []
    except Exception:
        ataque_form = None
        allowed_personagem_ids = []

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
        'ataque_form': ataque_form,
        'allowed_personagem_ids': allowed_personagem_ids,
    }

    return render(request, 'combate/detalhes_combate.html', context)
@login_required
def atualizar_posicao_token(request, token_id):
    if request.method == "POST":
        posicao = get_object_or_404(PosicaoPersonagem, id=token_id)
        # Permissão: somente GM da sala ou dono do personagem
        combate = posicao.participante.combate
        if not (combate.sala.game_master == request.user or posicao.participante.personagem.usuario_id == request.user.id):
            return JsonResponse({'error': 'forbidden'}, status=403)
        data = json.loads(request.body)
        posicao.x = int(data.get("x", posicao.x))
        posicao.y = int(data.get("y", posicao.y))
        size = data.get("size")
        if isinstance(size, (int, float)):
            try:
                posicao.token_size = max(10, min(200, int(size)))
            except Exception:
                pass
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
            # Se tamanho foi atualizado, envie um evento específico
            if isinstance(size, (int, float)):
                async_to_sync(channel_layer.group_send)(
                    f'combate_{posicao.participante.combate.id}',
                    {
                        'type': 'combate_message',
                        'message': json.dumps({
                            'evento': 'token_resize',
                            'posicao_id': posicao.id,
                            'size': posicao.token_size,
                        })
                    }
                )
        except Exception:
            # Em dev, ignore falha de broadcast para não quebrar o movimento do token
            pass
        return JsonResponse({"status": "ok"})

@login_required
@require_POST
def passar_turno(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    if combate.sala.game_master != request.user:
        if _expects_json(request):
            return JsonResponse({'error': 'forbidden'}, status=403)
        return redirect('detalhes_combate', combate_id=combate.id)
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

@login_required
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
    novo_turno = Turno.objects.create(
        combate=combate,
        personagem=primeiro_participante.personagem,
        ordem=0,
        ativo=True
    )
    # Tique de Concentração/Sustentado: no início do turno do conjurador, efeitos ativos reaplicam
    try:
        # Resumo de efeitos ativos (Sustentado e Concentração) no início do turno
        mensagens_tick = []
        ativos_qs = (
            EfeitoConcentracao.objects
            .filter(combate=combate, aplicador=primeiro_participante.personagem, ativo=True)
            .select_related('alvo_participante', 'alvo_participante__personagem', 'poder')
        )
        sust_ativos = [
            f"• <b>{ef.poder.nome}</b> em {ef.alvo_participante.personagem.nome}"
            for ef in ativos_qs if getattr(ef.poder, 'duracao', '') == 'sustentado'
        ]
        conc_ativos = [
            f"• <b>{ef.poder.nome}</b> em {ef.alvo_participante.personagem.nome}"
            for ef in ativos_qs if getattr(ef.poder, 'duracao', '') == 'concentracao'
        ]
        if sust_ativos:
            mensagens_tick.append("[Sustentado] Ativos no início do turno:")
            mensagens_tick.extend(sust_ativos)
        if conc_ativos:
            mensagens_tick.append("[Concentração] Ativos no início do turno:")
            mensagens_tick.extend(conc_ativos)
        efeitos = ativos_qs
        for ef in efeitos:
            poder = ef.poder
            alvo_part = ef.alvo_participante
            alvo = alvo_part.personagem
            tick_label = '[Concentração]' if getattr(poder, 'duracao', 'concentracao') == 'concentracao' else ('[Sustentado]' if getattr(poder, 'duracao', '') == 'sustentado' else '[Concentração]')
            # Tipos ofensivos: aplicar teste de defesa similar ao turno inicial
            if poder.tipo in ('dano', 'aflicao'):
                # CD usa nível efetivo; para dano melee com checkbox somar_forca_no_nivel, soma Força efetiva do aplicador (com Aprimorar/Reduzir)
                try:
                    if poder.tipo == 'dano' and getattr(poder, 'modo', '') == 'melee' and getattr(poder, 'somar_forca_no_nivel', False):
                        aplicador = ef.poder.personagem
                        aplicador_part = Participante.objects.filter(combate=combate, personagem=aplicador).first()
                        forca_eff = _atributo_efetivo(aplicador, aplicador_part, 'forca', combate.id) if aplicador_part else int(getattr(aplicador, 'forca', 0) or 0)
                        n_eff = abs(int(getattr(poder, 'nivel_efeito', 0) or 0)) + abs(int(forca_eff))
                    else:
                        n_eff = int(getattr(poder, 'nivel_efeito', 0) or 0)
                except Exception:
                    n_eff = int(getattr(poder, 'nivel_efeito', 0) or 0)
                cd = (15 + n_eff) if poder.tipo == 'dano' else (10 + n_eff)
                defesa_attr = getattr(poder, 'defesa_passiva', 'resistencia') or 'resistencia'
                defesa_valor = _defesa_efetiva(alvo, alvo_part, defesa_attr, combate.id)
                # Bônus específico (Aprimorar instantâneo) para próxima rolagem daquela defesa
                attr_bonus_map = alvo_part.proximo_bonus_por_atributo or {}
                attr_next_bonus = int(attr_bonus_map.get(defesa_attr, 0))
                buff = alvo_part.bonus_temporario
                debuff = alvo_part.penalidade_temporaria
                rolagem_base = random.randint(1, 20)
                total_def = rolagem_base + defesa_valor + attr_next_bonus + buff - debuff
                # Consome buff/debuff do alvo sem sobrescrever outros campos atualizados por F()
                Participante.objects.filter(pk=alvo_part.pk).update(bonus_temporario=0, penalidade_temporaria=0)
                # Consome bônus específico por atributo (defesa)
                if attr_next_bonus:
                    try:
                        del attr_bonus_map[defesa_attr]
                    except Exception:
                        attr_bonus_map[defesa_attr] = 0
                    alvo_part.proximo_bonus_por_atributo = attr_bonus_map
                    alvo_part.save()
                attr_piece = (f" + {attr_next_bonus}" if attr_next_bonus > 0 else (f" - {abs(attr_next_bonus)}" if attr_next_bonus < 0 else ""))
                defesa_msg = (
                    f"{rolagem_base} + {defesa_valor}"
                    f"{' + ' + str(buff) if buff else ''}"
                    f"{' - ' + str(debuff) if debuff else ''}"
                    f"{attr_piece} = {total_def}"
                )
                if total_def < cd:
                    if poder.tipo == 'dano':
                        Participante.objects.filter(pk=alvo_part.pk).update(dano=F('dano') + 1)
                        mensagens_tick.append(
                            f"{tick_label} {poder.nome} afeta {alvo.nome}: teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — <b>Sofreu 1 de dano!</b>"
                        )
                    else:
                        Participante.objects.filter(pk=alvo_part.pk).update(aflicao=F('aflicao') + 1)
                        mensagens_tick.append(
                            f"{tick_label} {poder.nome} afeta {alvo.nome}: teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — <b>Sofreu 1 de aflição!</b>"
                        )
                    # Teste de Vigor CD 15: apenas se o alvo mantém efeitos próprios (como conjurador)
                    if EfeitoConcentracao.objects.filter(combate=combate, ativo=True, aplicador=alvo).exists():
                        vigor = _atributo_efetivo(alvo, alvo_part, 'vigor', combate.id)
                        # Consome bônus específico (Aprimorar instantâneo) em Vigor, se houver
                        vigor_map = alvo_part.proximo_bonus_por_atributo or {}
                        vigor_next = int(vigor_map.get('vigor', 0))
                        rolagem_vigor = random.randint(1, 20)
                        total_vigor = rolagem_vigor + vigor + vigor_next
                        if vigor_next:
                            try:
                                del vigor_map['vigor']
                            except Exception:
                                vigor_map['vigor'] = 0
                            alvo_part.proximo_bonus_por_atributo = vigor_map
                            alvo_part.save()
                        if total_vigor < 15:
                            encerrados = EfeitoConcentracao.objects.filter(
                                combate=combate, ativo=True, aplicador=alvo
                            )
                            if encerrados.exists():
                                encerrados.update(ativo=False)
                                nomes = ", ".join(set(e.poder.nome for e in encerrados))
                                mensagens_tick.append(
                                    f"[Concentração] {alvo.nome} falhou Vigor ({rolagem_vigor} + {vigor} = {total_vigor}) vs CD 15 — efeitos encerrados: {nomes}."
                                )
                        else:
                            mensagens_tick.append(
                                f"[Concentração] {alvo.nome} manteve a concentração (Vigor {rolagem_vigor} + {vigor} = {total_vigor} vs 15)."
                            )
                else:
                    mensagens_tick.append(
                        f"{tick_label} {poder.nome} em {alvo.nome}: teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — sem efeito."
                    )
            # Cura: repete a rolagem de cura do conjurador para o mesmo alvo
            elif poder.tipo == 'cura':
                # Novo: Cura usa d20 + Nível de Efeito (não mais Habilidade de Conjuração)
                rolagem = random.randint(1, 20) + int(getattr(poder, 'nivel_efeito', 0) or 0)
                cd = 10 - poder.nivel_efeito
                if rolagem >= cd:
                    if alvo_part.dano >= alvo_part.aflicao and alvo_part.dano > 0:
                        Participante.objects.filter(pk=alvo_part.pk).update(dano=F('dano') - 1)
                        mensagens_tick.append(
                            f"{tick_label} {poder.nome} cura {alvo.nome} (Rolagem {rolagem} vs CD {cd}): Dano reduzido em 1."
                        )
                    elif alvo_part.aflicao > alvo_part.dano and alvo_part.aflicao > 0:
                        Participante.objects.filter(pk=alvo_part.pk).update(aflicao=F('aflicao') - 1)
                        mensagens_tick.append(
                            f"{tick_label} {poder.nome} cura {alvo.nome} (Rolagem {rolagem} vs CD {cd}): Aflição reduzida em 1."
                        )
                    else:
                        mensagens_tick.append(
                            f"{tick_label} {poder.nome} cura {alvo.nome} (Rolagem {rolagem} vs CD {cd}): nada para curar."
                        )
                else:
                    mensagens_tick.append(
                        f"{tick_label} {poder.nome} tentou curar {alvo.nome} (Rolagem {rolagem} vs CD {cd}): falhou."
                    )
            # Buff/Debuff (unificado): reaplica o modificador temporário
            elif poder.tipo == 'buff':
                alvo_part.bonus_temporario += poder.nivel_efeito
                alvo_part.save()
                sign_val = f"+{poder.nivel_efeito}" if int(getattr(poder, 'nivel_efeito', 0) or 0) >= 0 else f"{poder.nivel_efeito}"
                mensagens_tick.append(
                    f"{tick_label} {poder.nome} aplica novamente {sign_val} a {alvo.nome} na próxima rolagem."
                )
            elif poder.tipo == 'aprimorar':
                # Para Reduzir (valor negativo): alvo faz teste a cada tique; se passar, efeito termina; se falhar, mantém
                val = int(getattr(poder, 'nivel_efeito', 0) or 0)
                if val < 0:
                    defesa_attr = getattr(poder, 'defesa_passiva', 'vontade') or 'vontade'
                    buff = alvo_part.bonus_temporario
                    debuff = alvo_part.penalidade_temporaria
                    attr_map = alvo_part.proximo_bonus_por_atributo or {}
                    a_next = int(attr_map.get(defesa_attr, 0))
                    base = random.randint(1, 20)
                    defesa_valor = _atributo_efetivo(alvo, alvo_part, defesa_attr, combate.id)
                    total = base + defesa_valor + a_next + buff - debuff
                    # Consome bônus gerais e específico da defesa
                    Participante.objects.filter(pk=alvo_part.pk).update(bonus_temporario=0, penalidade_temporaria=0)
                    if a_next:
                        try:
                            del attr_map[defesa_attr]
                        except Exception:
                            attr_map[defesa_attr] = 0
                        alvo_part.proximo_bonus_por_atributo = attr_map
                        alvo_part.save()
                    cd = 10 + abs(val)
                    a_piece = (f" + {a_next}" if a_next > 0 else (f" - {abs(a_next)}" if a_next < 0 else ""))
                    defesa_msg = (
                        f"{base} + {defesa_valor}"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f"{a_piece} = {total}"
                    )
                    if total >= cd:
                        # Sucesso: termina o efeito
                        ef.ativo = False
                        ef.save()
                        mensagens_tick.append(
                            f"{tick_label} {alvo.nome} resistiu a {poder.nome}: teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — <b>Efeito encerrado</b>."
                        )
                    else:
                        mensagens_tick.append(
                            f"{tick_label} {poder.nome} mantém {alvo.nome}: falhou {defesa_attr} ({defesa_msg}) contra CD {cd}."
                        )
                else:
                    # Aprimorar positivo: apenas mantém e informa
                    sign_val = f"+{val}" if val >= 0 else f"{val}"
                    mensagens_tick.append(
                        f"{tick_label} {poder.nome} mantém {alvo.nome} com {sign_val} em {poder.casting_ability.capitalize()}."
                    )
        if mensagens_tick:
            texto = "<br>".join(mensagens_tick)
            novo_turno.descricao = (novo_turno.descricao + "<br>" if novo_turno.descricao else "") + texto
            novo_turno.save()
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'combate_{combate.id}',
                    {
                        'type': 'combate_message',
                        'message': json.dumps({'evento': 'concentracao_tick', 'descricao': texto})
                    }
                )
            except Exception:
                logger.warning("Falha ao enviar evento 'concentracao_tick' via Channels (ignorado)", exc_info=True)
    except Exception:
        logger.warning("Falha ao processar tique de concentração no início do turno", exc_info=True)
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


@login_required
@require_POST
def avancar_turno(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    if combate.sala.game_master != request.user:
        if _expects_json(request):
            return JsonResponse({'error': 'forbidden'}, status=403)
        return redirect('detalhes_combate', combate_id=combate.id)
    turnos = Turno.objects.filter(combate=combate).order_by('ordem')
    turno_ativo = turnos.filter(ativo=True).first()
    if turno_ativo:
        turno_ativo.ativo = False
        turno_ativo.save()
        participantes = list(Participante.objects.filter(combate=combate).order_by('-iniciativa'))
        
        # CORREÇÃO SIMPLES: ao invés de usar o problemático index() com personagem_id,
        # vamos manter um contador rotativo para personagens duplicados
        
        # Encontra todos os participantes com o mesmo personagem_id do turno atual
        participantes_mesmo_personagem = [p for p in participantes if p.personagem_id == turno_ativo.personagem_id]
        
        if len(participantes_mesmo_personagem) == 1:
            # Personagem único: usa a lógica simples original
            for i, p in enumerate(participantes):
                if p.personagem_id == turno_ativo.personagem_id:
                    proximo_idx = (i + 1) % len(participantes)
                    break
        else:
            # Múltiplos participantes com mesmo personagem_id: usa rotação baseada no número de turnos
            # Conta quantos turnos este personagem_id já teve
            total_turnos_personagem = Turno.objects.filter(
                combate=combate, 
                personagem_id=turno_ativo.personagem_id
            ).count()
            
            # O índice dentro do grupo de duplicados é baseado no número de turnos (rotação)
            indice_no_grupo = (total_turnos_personagem - 1) % len(participantes_mesmo_personagem)
            participante_atual = participantes_mesmo_personagem[indice_no_grupo]
            
            # Encontra o índice deste participante na lista geral
            idx_atual = participantes.index(participante_atual)
            proximo_idx = (idx_atual + 1) % len(participantes)
        
        personagem_proximo = participantes[proximo_idx].personagem
        novo_turno = Turno.objects.create(combate=combate, personagem=personagem_proximo, ordem=turno_ativo.ordem + 1, ativo=True)
        # Processa efeitos de concentração / sustentado
        try:
            ativos = (
                EfeitoConcentracao.objects
                .filter(combate=combate, aplicador=personagem_proximo, ativo=True)
                .select_related('alvo_participante', 'alvo_participante__personagem', 'poder')
            )
            mensagens_tick = []
            sust = [f"• <b>{ef.poder.nome}</b> em {ef.alvo_participante.personagem.nome}" for ef in ativos if getattr(ef.poder, 'duracao', '') == 'sustentado']
            conc = [f"• <b>{ef.poder.nome}</b> em {ef.alvo_participante.personagem.nome}" for ef in ativos if getattr(ef.poder, 'duracao', '') == 'concentracao']
            if sust:
                mensagens_tick.append("[Sustentado] Ativos no início do turno:")
                mensagens_tick.extend(sust)
            if conc:
                mensagens_tick.append("[Concentração] Ativos no início do turno:")
                mensagens_tick.extend(conc)
            for ef in ativos:
                poder = ef.poder
                alvo_part = ef.alvo_participante
                alvo = alvo_part.personagem
                label = '[Concentração]' if getattr(poder, 'duracao', '') == 'concentracao' else ('[Sustentado]' if getattr(poder, 'duracao', '') == 'sustentado' else '')
                if poder.tipo in ('dano', 'aflicao'):
                    try:
                        if poder.tipo == 'dano' and getattr(poder, 'modo', '') == 'melee' and getattr(poder, 'somar_forca_no_nivel', False):
                            aplicador = ef.poder.personagem
                            aplicador_part = Participante.objects.filter(combate=combate, personagem=aplicador).first()
                            forca_eff = _atributo_efetivo(aplicador, aplicador_part, 'forca', combate.id) if aplicador_part else int(getattr(aplicador, 'forca', 0) or 0)
                            n_eff = abs(int(getattr(poder, 'nivel_efeito', 0) or 0)) + abs(int(forca_eff))
                        else:
                            n_eff = int(getattr(poder, 'nivel_efeito', 0) or 0)
                    except Exception:
                        n_eff = int(getattr(poder, 'nivel_efeito', 0) or 0)
                    cd = (15 if poder.tipo == 'dano' else 10) + n_eff
                    defesa_attr = getattr(poder, 'defesa_passiva', 'resistencia') or 'resistencia'
                    base = random.randint(1, 20)
                    val = _atributo_efetivo(alvo, alvo_part, defesa_attr, combate.id)
                    attr_map = alvo_part.proximo_bonus_por_atributo or {}
                    a_next = int(attr_map.get(defesa_attr, 0))
                    buff = alvo_part.bonus_temporario
                    debuff = alvo_part.penalidade_temporaria
                    total = base + val + a_next + buff - debuff
                    Participante.objects.filter(pk=alvo_part.pk).update(bonus_temporario=0, penalidade_temporaria=0)
                    if a_next:
                        try:
                            del attr_map[defesa_attr]
                        except Exception:
                            attr_map[defesa_attr] = 0
                        alvo_part.proximo_bonus_por_atributo = attr_map
                        alvo_part.save()
                    a_piece = (f" + {a_next}" if a_next > 0 else (f" - {abs(a_next)}" if a_next < 0 else ""))
                    msg_def = f"{base} + {val}{' + ' + str(buff) if buff else ''}{' - ' + str(debuff) if debuff else ''}{a_piece} = {total}"
                    if total < cd:
                        field = 'dano' if poder.tipo == 'dano' else 'aflicao'
                        Participante.objects.filter(pk=alvo_part.pk).update(**{field: F(field) + 1})
                        mensagens_tick.append(f"{label} {poder.nome} afeta {alvo.nome}: teste de {defesa_attr} ({msg_def}) contra CD {cd} — <b>{'Dano' if field=='dano' else 'Aflição'} +1</b>.")
                        if EfeitoConcentracao.objects.filter(combate=combate, ativo=True, aplicador=alvo).exists():
                            vigor = _atributo_efetivo(alvo, alvo_part, 'vigor', combate.id)
                            b = random.randint(1, 20)
                            tv = b + vigor
                            if tv < 15:
                                enc = EfeitoConcentracao.objects.filter(combate=combate, ativo=True, aplicador=alvo)
                                if enc.exists():
                                    enc.update(ativo=False)
                                    nomes = ", ".join(set(e.poder.nome for e in enc))
                                    mensagens_tick.append(f"[Concentração] {alvo.nome} falhou Vigor ({b} + {vigor} = {tv}) vs 15 — efeitos encerrados: {nomes}.")
                            else:
                                mensagens_tick.append(f"[Concentração] {alvo.nome} manteve a concentração (Vigor {b} + {vigor} = {tv} vs 15).")
                    else:
                        mensagens_tick.append(f"{label} {poder.nome} em {alvo.nome}: teste de {defesa_attr} ({msg_def}) contra CD {cd} — sem efeito.")
                elif poder.tipo == 'cura':
                    # Novo: Cura usa d20 + Nível de Efeito
                    roll = random.randint(1, 20) + int(getattr(poder, 'nivel_efeito', 0) or 0)
                    cd = 10 - poder.nivel_efeito
                    if roll >= cd:
                        if alvo_part.dano >= alvo_part.aflicao and alvo_part.dano > 0:
                            Participante.objects.filter(pk=alvo_part.pk).update(dano=F('dano') - 1)
                            mensagens_tick.append(f"{label} {poder.nome} cura {alvo.nome} (Rol {roll} vs {cd}): Dano -1.")
                        elif alvo_part.aflicao > alvo_part.dano and alvo_part.aflicao > 0:
                            Participante.objects.filter(pk=alvo_part.pk).update(aflicao=F('aflicao') - 1)
                            mensagens_tick.append(f"{label} {poder.nome} cura {alvo.nome} (Rol {roll} vs {cd}): Aflição -1.")
                        else:
                            mensagens_tick.append(f"{label} {poder.nome} cura {alvo.nome} (Rol {roll} vs {cd}): nada para curar.")
                    else:
                        mensagens_tick.append(f"{label} {poder.nome} tentou curar {alvo.nome} (Rol {roll} vs {cd}): falhou.")
                elif poder.tipo == 'buff':
                    alvo_part.bonus_temporario += poder.nivel_efeito
                    alvo_part.save()
                    val = int(getattr(poder, 'nivel_efeito', 0) or 0)
                    sign_val = f"+{val}" if val >= 0 else f"{val}"
                    mensagens_tick.append(f"{label} {poder.nome} aplica novamente {sign_val} a {alvo.nome}.")
                elif poder.tipo == 'aprimorar':
                    val = int(getattr(poder, 'nivel_efeito', 0) or 0)
                    if val < 0:
                        defesa_attr = getattr(poder, 'defesa_passiva', 'vontade') or 'vontade'
                        buff = alvo_part.bonus_temporario
                        debuff = alvo_part.penalidade_temporaria
                        attr_map = alvo_part.proximo_bonus_por_atributo or {}
                        a_next = int(attr_map.get(defesa_attr, 0))
                        base = random.randint(1, 20)
                        defesa_valor = _atributo_efetivo(alvo, alvo_part, defesa_attr, combate.id)
                        total = base + defesa_valor + a_next + buff - debuff
                        Participante.objects.filter(pk=alvo_part.pk).update(bonus_temporario=0, penalidade_temporaria=0)
                        if a_next:
                            try:
                                del attr_map[defesa_attr]
                            except Exception:
                                attr_map[defesa_attr] = 0
                            alvo_part.proximo_bonus_por_atributo = attr_map
                            alvo_part.save()
                        cd = 10 + abs(val)
                        a_piece = (f" + {a_next}" if a_next > 0 else (f" - {abs(a_next)}" if a_next < 0 else ""))
                        defesa_msg = (
                            f"{base} + {defesa_valor}"
                            f"{' + ' + str(buff) if buff else ''}"
                            f"{' - ' + str(debuff) if debuff else ''}"
                            f"{a_piece} = {total}"
                        )
                        if total >= cd:
                            # Sucesso: termina o efeito
                            ef.ativo = False
                            ef.save()
                            mensagens_tick.append(f"{label} {alvo.nome} resistiu a {poder.nome}: teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — <b>Efeito encerrado</b>.")
                        else:
                            mensagens_tick.append(f"{label} {poder.nome} mantém {alvo.nome}: falhou {defesa_attr} ({defesa_msg}) contra CD {cd}.")
                    else:
                        sign_val = f"+{val}" if val >= 0 else f"{val}"
                        mensagens_tick.append(f"{label} {poder.nome} mantém {alvo.nome} com {sign_val} em {poder.casting_ability.capitalize()}.")
            if mensagens_tick:
                texto = "<br>".join(mensagens_tick)
                novo_turno.descricao = (novo_turno.descricao + "<br>" if novo_turno.descricao else "") + texto
                novo_turno.save()
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'combate_{combate.id}',
                        {
                            'type': 'combate_message',
                            'message': json.dumps({'evento': 'concentracao_tick', 'descricao': texto})
                        }
                    )
                except Exception:
                    logger.warning("Falha ao enviar evento 'concentracao_tick' via Channels (ignorado)", exc_info=True)
        except Exception:
            logger.warning("Falha no processamento do tique de concentração em avancar_turno", exc_info=True)
        # Evento avancar_turno
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'combate_{combate.id}',
                {
                    'type': 'combate_message',
                    'message': json.dumps({'evento': 'avancar_turno', 'descricao': f'Turno avançado para {personagem_proximo.nome}.'})
                }
            )
        except Exception:
            logger.warning("Falha ao enviar evento 'avancar_turno' via Channels (ignorado)", exc_info=True)
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


@login_required
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
    # Encerra todas as concentrações ativas deste combate
    try:
        EfeitoConcentracao.objects.filter(combate=combate, ativo=True).update(ativo=False)
    except Exception:
        logger.warning("Falha ao encerrar efeitos de concentração ao finalizar combate", exc_info=True)
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


@login_required
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
@require_POST
def encerrar_efeito(request, combate_id, efeito_id):
    """Encerra manualmente um único efeito de concentração/sustentado.
    Permissão: GM da sala do combate OU dono do personagem que é o aplicador do efeito.
    """
    combate = get_object_or_404(Combate, id=combate_id)
    efeito = get_object_or_404(EfeitoConcentracao, id=efeito_id, combate=combate)
    # Permissões
    is_gm = combate.sala.game_master == request.user
    is_owner = getattr(efeito.aplicador, 'usuario_id', None) == request.user.id
    if not (is_gm or is_owner):
        return redirect('detalhes_combate', combate_id=combate.id)
    if efeito.ativo:
        efeito.ativo = False
        efeito.save()
        # Log no turno ativo (se existir)
        turno_ativo = Turno.objects.filter(combate=combate, ativo=True).first()
        texto = f"[Concentração] {efeito.aplicador.nome} encerrou {efeito.poder.nome} em {efeito.alvo_participante.personagem.nome}."
        if turno_ativo:
            turno_ativo.descricao = (turno_ativo.descricao + "<br>" if turno_ativo.descricao else "") + texto
            turno_ativo.save()
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'combate_{combate.id}',
                {
                    'type': 'combate_message',
                    'message': json.dumps({'evento': 'rolagem', 'descricao': texto})
                }
            )
        except Exception:
            logger.warning("Falha ao enviar evento 'rolagem' (encerrar_efeito)", exc_info=True)
    if _expects_json(request):
        return JsonResponse({'status': 'ok', 'evento': 'rolagem'})
    return redirect('detalhes_combate', combate_id=combate.id)


@login_required
@require_POST
def encerrar_meus_efeitos(request, combate_id):
    """Encerra todos os efeitos mantidos pelo personagem selecionado em 'Ações de'."""
    combate = get_object_or_404(Combate, id=combate_id)
    participante_id = request.POST.get('personagem_acao')
    if not participante_id:
        return redirect('detalhes_combate', combate_id=combate.id)
    participante = get_object_or_404(Participante.objects.select_related('personagem'), id=participante_id, combate=combate)
    # Permissões
    is_gm = combate.sala.game_master == request.user
    is_owner = participante.personagem.usuario_id == request.user.id
    if not (is_gm or is_owner):
        return redirect('detalhes_combate', combate_id=combate.id)
    ativos = EfeitoConcentracao.objects.filter(combate=combate, aplicador=participante.personagem, ativo=True)
    nomes = []
    if ativos.exists():
        nomes = list({e.poder.nome for e in ativos})
        ativos.update(ativo=False)
    texto = ("[Concentração] " + participante.personagem.nome +
             (" encerrou todos os seus efeitos ativos: " + ", ".join(nomes) if nomes else " não possuía efeitos ativos para encerrar."))
    # Log
    turno_ativo = Turno.objects.filter(combate=combate, ativo=True).first()
    if turno_ativo:
        turno_ativo.descricao = (turno_ativo.descricao + "<br>" if turno_ativo.descricao else "") + texto
        turno_ativo.save()
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'combate_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({'evento': 'rolagem', 'descricao': texto})
            }
        )
    except Exception:
        logger.warning("Falha ao enviar evento 'rolagem' (encerrar_meus_efeitos)", exc_info=True)
    if _expects_json(request):
        return JsonResponse({'status': 'ok', 'evento': 'rolagem'})
    return redirect('detalhes_combate', combate_id=combate.id)





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

    # Helper para enviar evento via Channels (tolerante a falhas)
    def send_event(evento: str, descricao: str):
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'combate_{combate_id}',
                {
                    'type': 'combate_message',
                    'message': json.dumps({'evento': evento, 'descricao': descricao})
                }
            )
        except Exception:
            logger.warning("Falha ao enviar evento '%s' via Channels (ignorado)", evento, exc_info=True)

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
        'arcana': 'inteligencia',
        'religiao': 'prontidao',
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
                base_name = getattr(atacante, 'especialidade_casting_ability', 'especialidade')
                valor_caracteristica = _atributo_efetivo(atacante, participante_atacante, base_name, combate_id)
            else:
                base_name = caracteristica_base
                valor_caracteristica = _atributo_efetivo(atacante, participante_atacante, caracteristica_base, combate_id)

            # Bônus específico para próxima rolagem desse atributo (Aprimorar instantâneo)
            attr_bonus_map = participante_atacante.proximo_bonus_por_atributo or {}
            attr_next_bonus = int(attr_bonus_map.get(base_name, 0)) if base_name else 0
            if valor_pericia is not None:
                rolagem_base = random.randint(1, 20)
                total = rolagem_base + valor_pericia + valor_caracteristica + attr_next_bonus + buff - debuff
                attr_piece = (f" + {attr_next_bonus}" if attr_next_bonus > 0 else (f" - {abs(attr_next_bonus)}" if attr_next_bonus < 0 else ""))
                resultados.append(
                    f"{atacante.nome} rolou {pericia_escolhida.capitalize()}: {rolagem_base} + {valor_pericia} (perícia) + {valor_caracteristica} ({str(base_name).replace('_', ' ').capitalize()})"
                    f"{' + ' + str(buff) if buff else ''}"
                    f"{' - ' + str(debuff) if debuff else ''}"
                    f"{attr_piece} = <b>{total}</b>"
                )
                participante_atacante.bonus_temporario = 0
                participante_atacante.penalidade_temporaria = 0
                # Consome bônus específico por atributo
                if attr_next_bonus:
                    try:
                        del attr_bonus_map[base_name]
                    except Exception:
                        attr_bonus_map[base_name] = 0
                    participante_atacante.proximo_bonus_por_atributo = attr_bonus_map
                participante_atacante.save()
            else:
                resultados.append(f"{atacante.nome} não possui a perícia {pericia_escolhida}.")
        else:
            resultados.append("Nenhuma perícia selecionada.")

        nova_descricao = "<br>".join(resultados)
        append_to_turno(nova_descricao)
        send_event('rolagem', nova_descricao)
        if _expects_json(request):
            return JsonResponse({'status': 'ok', 'evento': 'rolagem', 'descricao': nova_descricao})
        return redirect('detalhes_combate', combate_id=combate_id)

    if request.POST.get('rolar_caracteristica'):
        caracteristica_escolhida = request.POST.get('caracteristica')
        if caracteristica_escolhida:
            valor_caracteristica = _atributo_efetivo(atacante, participante_atacante, caracteristica_escolhida, combate_id)
            # Bonus específico para próxima rolagem daquele atributo
            attr_bonus_map = participante_atacante.proximo_bonus_por_atributo or {}
            attr_next_bonus = int(attr_bonus_map.get(caracteristica_escolhida, 0))
            buff = participante_atacante.bonus_temporario
            debuff = participante_atacante.penalidade_temporaria
            if valor_caracteristica is not None:
                rolagem_base = random.randint(1, 20)
                total = rolagem_base + valor_caracteristica + attr_next_bonus + buff - debuff
                attr_piece = (f" + {attr_next_bonus}" if attr_next_bonus > 0 else (f" - {abs(attr_next_bonus)}" if attr_next_bonus < 0 else ""))
                resultados.append(
                    f"{atacante.nome} rolou {caracteristica_escolhida.capitalize()}: {rolagem_base} + {valor_caracteristica}"
                    f"{' + ' + str(buff) if buff else ''}"
                    f"{' - ' + str(debuff) if debuff else ''}"
                    f"{attr_piece} = <b>{total}</b>"
                )
                participante_atacante.bonus_temporario = 0
                participante_atacante.penalidade_temporaria = 0
                # Consome bônus específico por atributo
                if attr_next_bonus:
                    try:
                        del attr_bonus_map[caracteristica_escolhida]
                    except Exception:
                        attr_bonus_map[caracteristica_escolhida] = 0
                    participante_atacante.proximo_bonus_por_atributo = attr_bonus_map
                participante_atacante.save()
            else:
                resultados.append(f"{atacante.nome} não possui a característica {caracteristica_escolhida}.")
        else:
            resultados.append("Nenhuma característica selecionada.")

        nova_descricao = "<br>".join(resultados)
        append_to_turno(nova_descricao)
        send_event('rolagem', nova_descricao)
        if _expects_json(request):
            return JsonResponse({'status': 'ok', 'evento': 'rolagem', 'descricao': nova_descricao})
        return redirect('detalhes_combate', combate_id=combate_id)

    if request.POST.get('rolar_d20'):
        rolagem_base = random.randint(1, 20)
        resultados.append(f"{atacante.nome} rolou um d20: <b>{rolagem_base}</b>")
        nova_descricao = "<br>".join(resultados)
        append_to_turno(nova_descricao)
        send_event('rolagem', nova_descricao)
        if _expects_json(request):
            return JsonResponse({'status': 'ok', 'evento': 'rolagem', 'descricao': nova_descricao})
        return redirect('detalhes_combate', combate_id=combate_id)

    # Poder com (opcionais) alvos
    alvo_ids = request.POST.getlist('alvo_id')
    poder_id = request.POST.get('poder_id')
    if poder_id:
        poder = get_object_or_404(Poder, id=poder_id, personagem=atacante)

        def manter_concentracao_apos_sofrer(alvo_part):
            efeitos_mantidos = EfeitoConcentracao.objects.filter(
                combate_id=combate_id, ativo=True, aplicador=alvo_part.personagem
            )
            if not efeitos_mantidos.exists():
                return
            vigor = _atributo_efetivo(alvo_part.personagem, alvo_part, 'vigor', combate_id)
            rolagem = random.randint(1, 20)
            total = rolagem + vigor
            if total < 15:
                nomes = ", ".join(set(e.poder.nome for e in efeitos_mantidos))
                efeitos_mantidos.update(ativo=False)
                resultados.append(
                    f"[Concentração] {alvo_part.personagem.nome} falhou Vigor ({rolagem} + {vigor} = {total}) vs CD 15 — efeitos encerrados: {nomes}."
                )
            else:
                resultados.append(
                    f"[Concentração] {alvo_part.personagem.nome} manteve a concentração (Vigor {rolagem} + {vigor} = {total} vs 15)."
                )

        # Monta sequência encadeada (somente 1 nível)
        try:
            ligados = list(poder.ligados.all())
        except Exception:
            ligados = []
        poderes_sequence = [poder] + ligados
        # Shared attack state per target for this chain of linked effects
        _shared_attack_state = {}

        def _get_shared_attack_state_for_target(target_id: int):
            """Compute or retrieve a shared attack roll for this target across linked melee/ranged effects.
            Uses one d20 and the highest bonus per kind (melee/ranged). Consumes attacker temp mods once.
            """
            st = _shared_attack_state.get(target_id)
            if st is not None:
                return st
            # Determine if there are melee/ranged powers in this chain
            has_melee = any(getattr(p, 'modo', '') == 'melee' for p in poderes_sequence)
            has_ranged = any(getattr(p, 'modo', '') == 'ranged' for p in poderes_sequence)
            if not (has_melee or has_ranged):
                st = {}
                _shared_attack_state[target_id] = st
                return st
            d20 = random.randint(1, 20)
            try:
                max_melee = max([int(getattr(p, 'bonus_ataque', 0) or 0) for p in poderes_sequence if getattr(p, 'modo', '') == 'melee'] or [0])
                max_ranged = max([int(getattr(p, 'bonus_ataque', 0) or 0) for p in poderes_sequence if getattr(p, 'modo', '') == 'ranged'] or [0])
            except Exception:
                max_melee = 0
                max_ranged = 0
            # Base do atacante: Luta (melee) e Destreza (ranged)
            try:
                base_melee = _atributo_efetivo(atacante, participante_atacante, 'luta', combate_id) if has_melee else 0
            except Exception:
                base_melee = 0
            try:
                base_ranged = _atributo_efetivo(atacante, participante_atacante, 'destreza', combate_id) if has_ranged else 0
            except Exception:
                base_ranged = 0
            buff_att = participante_atacante.bonus_temporario
            debuff_att = participante_atacante.penalidade_temporaria
            # We'll need alvo to know defenses; resolve lazily at use-site
            st = {
                'd20': d20,
                'base_melee': base_melee,
                'base_ranged': base_ranged,
                'max_melee': max_melee,
                'max_ranged': max_ranged,
                'buff_att': buff_att,
                'debuff_att': debuff_att,
                'atk_total_melee': None,
                'atk_total_ranged': None,
                'hit_melee': None,
                'hit_ranged': None,
                'atk_msg_melee': None,
                'atk_msg_ranged': None,
                'logged_melee': False,
                'logged_ranged': False,
            }
            # Consume attacker temporary mods once when creating the state
            participante_atacante.bonus_temporario = 0
            participante_atacante.penalidade_temporaria = 0
            participante_atacante.save()
            _shared_attack_state[target_id] = st
            return st

        for idx, poder_atual in enumerate(poderes_sequence):
            duracao_raw = getattr(poder_atual, 'duracao', 'instantaneo')
            duracao_label = 'Concentração' if duracao_raw == 'concentracao' else ('Sustentado' if duracao_raw == 'sustentado' else 'Instantâneo')

            # Se concentração: encerrar instância anterior deste poder individualmente
            if duracao_raw == 'concentracao':
                anteriores = EfeitoConcentracao.objects.filter(
                    combate_id=combate_id, aplicador=atacante, poder=poder_atual, ativo=True
                )
                if anteriores.exists():
                    anteriores.update(ativo=False)
                    resultados.append(f"[Concentração] {atacante.nome} reutilizou {poder_atual.nome}: instância anterior encerrada.")

            cabecalho = (
                f"{atacante.nome} usou {poder_atual.nome} — Duração: {duracao_label}" if idx == 0
                else f"[Encadeado] {atacante.nome} aplica {poder_atual.nome}"
            )
            resultados.append(cabecalho)

            # Descritivo não exige alvo
            if getattr(poder_atual, 'tipo', '') == 'descritivo':
                rolagem_base = random.randint(1, 20)
                total = rolagem_base + int(getattr(poder_atual, 'nivel_efeito', 0) or 0)
                resultados.append(
                    f"{poder_atual.nome} (Descritivo): {rolagem_base} + {poder_atual.nivel_efeito} = <b>{total}</b>"
                )
                continue

            # Demais tipos precisam de alvos; se ausentes no poder principal aborta tudo, se em encadeados apenas pula
            if not alvo_ids:
                if idx == 0:  # principal sem alvo não-descritivo -> ignora ação
                    return redirect('detalhes_combate', combate_id=combate_id)
                else:
                    continue

            for alvo_id in alvo_ids:
                participante_alvo = get_object_or_404(Participante, id=alvo_id, combate_id=combate_id)
                alvo = participante_alvo.personagem

                tipo = getattr(poder_atual, 'tipo', '')
                modo = getattr(poder_atual, 'modo', '')
                resultado = None

                if tipo == 'cura':
                    # Novo: Cura usa d20 + Nível de Efeito
                    rolagem = random.randint(1, 20) + int(getattr(poder_atual, 'nivel_efeito', 0) or 0)
                    cd = 10 - poder_atual.nivel_efeito
                    if rolagem >= cd:
                        if participante_alvo.dano >= participante_alvo.aflicao and participante_alvo.dano > 0:
                            participante_alvo.dano -= 1
                            resultado = f"{atacante.nome} curou {alvo.nome} ({poder_atual.nome}) Dano -1 (Rol {rolagem} vs {cd})."
                        elif participante_alvo.aflicao > participante_alvo.dano and participante_alvo.aflicao > 0:
                            participante_alvo.aflicao -= 1
                            resultado = f"{atacante.nome} curou {alvo.nome} ({poder_atual.nome}) Aflição -1 (Rol {rolagem} vs {cd})."
                        else:
                            resultado = f"{atacante.nome} curou {alvo.nome} ({poder_atual.nome}) (Rol {rolagem} vs {cd}) nada para curar."
                        participante_alvo.save()
                        if duracao_raw in ('concentracao', 'sustentado'):
                            EfeitoConcentracao.objects.create(
                                combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                            )
                    else:
                        resultado = f"{atacante.nome} tentou curar {alvo.nome} ({poder_atual.nome}) (Rol {rolagem} vs {cd}) falhou."

                elif tipo == 'buff':
                    participante_alvo.bonus_temporario += poder_atual.nivel_efeito
                    participante_alvo.save()
                    val = int(getattr(poder_atual, 'nivel_efeito', 0) or 0)
                    sign_val = f"+{val}" if val >= 0 else f"{val}"
                    resultado = f"{alvo.nome} recebe {sign_val} (Buff/Debuff {poder_atual.nome})."
                    if duracao_raw in ('concentracao', 'sustentado'):
                        EfeitoConcentracao.objects.create(
                            combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                            poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                        )

                elif tipo == 'aprimorar':
                    # Aprimorar/Reduzir: quando negativo (redução), exige teste do alvo para aplicar.
                    # Se for melee/ranged, é necessário acertar o ataque antes do teste.
                    val = int(getattr(poder_atual, 'nivel_efeito', 0) or 0)
                    if val < 0 and modo in ('melee', 'ranged'):
                        # Shared attack resolution for linked melee/ranged
                        st = _get_shared_attack_state_for_target(alvo_id)
                        # Compute outcome for this kind lazily
                        is_melee = (modo == 'melee')
                        if is_melee and st.get('hit_melee') is None:
                            aparar = getattr(alvo, 'aparar', 0)
                            atk_total = st['d20'] + st['base_melee'] + st['max_melee'] + st['buff_att'] - st['debuff_att']
                            st['atk_total_melee'] = atk_total
                            st['hit_melee'] = atk_total > 10 + aparar
                            st['atk_msg_melee'] = (
                                f"{st['d20']} + {st['base_melee']} + {st['max_melee']}"
                                f"{' + ' + str(st['buff_att']) if st['buff_att'] else ''}"
                                f"{' - ' + str(st['debuff_att']) if st['debuff_att'] else ''} = {atk_total}"
                            )
                            st['aparar'] = aparar
                        if (not is_melee) and st.get('hit_ranged') is None:
                            esquivar = getattr(alvo, 'esquivar', 0)
                            atk_total = st['d20'] + st['base_ranged'] + st['max_ranged'] + st['buff_att'] - st['debuff_att']
                            st['atk_total_ranged'] = atk_total
                            st['hit_ranged'] = atk_total > 10 + esquivar
                            st['atk_msg_ranged'] = (
                                f"{st['d20']} + {st['base_ranged']} + {st['max_ranged']}"
                                f"{' + ' + str(st['buff_att']) if st['buff_att'] else ''}"
                                f"{' - ' + str(st['debuff_att']) if st['debuff_att'] else ''} = {atk_total}"
                            )
                            st['esquivar'] = esquivar
                        hit_now = st['hit_melee'] if is_melee else st['hit_ranged']
                        atk_msg = st['atk_msg_melee'] if is_melee else st['atk_msg_ranged']
                        defesa_mov_val = 10 + (st['aparar'] if is_melee else st['esquivar'])
                        if not hit_now:
                            # If we've already logged a miss for this kind in this chain, skip duplicates
                            logged_flag = 'logged_melee' if is_melee else 'logged_ranged'
                            if st.get(logged_flag):
                                # Skip producing another attack test/log for encadeado
                                continue
                            st[logged_flag] = True
                            resultado = f"{atacante.nome} errou {alvo.nome} (atk {atk_msg} vs {defesa_mov_val}) ({poder_atual.nome})"
                        else:
                            # 2) Teste do alvo na defesa passiva
                            defesa_attr = getattr(poder_atual, 'defesa_passiva', 'vontade') or 'vontade'
                            buff = participante_alvo.bonus_temporario
                            debuff = participante_alvo.penalidade_temporaria
                            attr_map = participante_alvo.proximo_bonus_por_atributo or {}
                            a_next = int(attr_map.get(defesa_attr, 0))
                            base = random.randint(1, 20)
                            defesa_val = _atributo_efetivo(alvo, participante_alvo, defesa_attr, combate.id)
                            total = base + defesa_val + a_next + buff - debuff
                            # Consome bônus gerais e específico por defesa
                            participante_alvo.bonus_temporario = 0
                            participante_alvo.penalidade_temporaria = 0
                            if a_next:
                                try:
                                    del attr_map[defesa_attr]
                                except Exception:
                                    attr_map[defesa_attr] = 0
                                participante_alvo.proximo_bonus_por_atributo = attr_map
                            participante_alvo.save()
                            cd = 10 + abs(val)
                            a_piece = (f" + {a_next}" if a_next > 0 else (f" - {abs(a_next)}" if a_next < 0 else ""))
                            defesa_msg = (
                                f"{base} + {defesa_val}"
                                f"{' + ' + str(buff) if buff else ''}"
                                f"{' - ' + str(debuff) if debuff else ''}"
                                f"{a_piece} = {total}"
                            )
                            ataque_msg = atk_msg
                            if total < cd:
                                # Falhou o teste: aplica Reduzir
                                if duracao_raw in ('concentracao', 'sustentado'):
                                    EfeitoConcentracao.objects.create(
                                        combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                        poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                    )
                                    resultado = (
                                        f"{atacante.nome} acertou {alvo.nome} (atk {ataque_msg} vs {defesa_mov_val}); "
                                        f"teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — "
                                        f"<b>Reduzido {val}</b> em {poder_atual.casting_ability.capitalize()} ({duracao_label})."
                                    )
                                else:
                                    # Instantâneo: aplica como penalidade específica na próxima rolagem daquele atributo
                                    attr_map2 = participante_alvo.proximo_bonus_por_atributo or {}
                                    key = getattr(poder_atual, 'casting_ability', None)
                                    if key:
                                        attr_map2[key] = int(attr_map2.get(key, 0)) + val
                                        participante_alvo.proximo_bonus_por_atributo = attr_map2
                                    participante_alvo.save()
                                    resultado = (
                                        f"{atacante.nome} acertou {alvo.nome} (atk {ataque_msg} vs {defesa_mov_val}); "
                                        f"teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — "
                                        f"<b>Reduzido {val}</b> na próxima rolagem de {getattr(poder_atual, 'casting_ability', '').capitalize()}."
                                    )
                            else:
                                resultado = (
                                    f"{atacante.nome} acertou {alvo.nome} (atk {ataque_msg} vs {defesa_mov_val}); "
                                    f"teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — sem efeito."
                                )
                    elif val < 0:
                        # Modos não-ofensivos/percepção ou área
                        if modo == 'area':
                            # Esquiva primeiro, com sucesso parcial reduzindo a CD do teste de defesa
                            esquiva = _defesa_efetiva(alvo, participante_alvo, 'esquivar', combate.id)
                            esq_map = participante_alvo.proximo_bonus_por_atributo or {}
                            esq_next = int(esq_map.get('esquivar', 0))
                            rolagem_esq_base = random.randint(1, 20)
                            rolagem_esq = rolagem_esq_base + esquiva + esq_next
                            # Consome bônus específico de Esquivar
                            if esq_next:
                                try:
                                    del esq_map['esquivar']
                                except Exception:
                                    esq_map['esquivar'] = 0
                                participante_alvo.proximo_bonus_por_atributo = esq_map
                                participante_alvo.save()
                            cd_area = 10 + abs(val)
                            cd_sucesso = cd_area // 2
                            defesa_attr = getattr(poder_atual, 'defesa_passiva', 'vontade') or 'vontade'
                            esq_piece = (f" + {esq_next}" if esq_next > 0 else (f" - {abs(esq_next)}" if esq_next < 0 else ""))
                            # Preparar rol do teste de defesa (consome buffs/penalidades e bônus específico da defesa)
                            def _teste_defesa(cd_uso: int):
                                buff = participante_alvo.bonus_temporario
                                debuff = participante_alvo.penalidade_temporaria
                                attr_map = participante_alvo.proximo_bonus_por_atributo or {}
                                a_next = int(attr_map.get(defesa_attr, 0))
                                base = random.randint(1, 20)
                                defesa_val = _defesa_efetiva(alvo, participante_alvo, defesa_attr, combate.id)
                                total = base + defesa_val + a_next + buff - debuff
                                participante_alvo.bonus_temporario = 0
                                participante_alvo.penalidade_temporaria = 0
                                if a_next:
                                    try:
                                        del attr_map[defesa_attr]
                                    except Exception:
                                        attr_map[defesa_attr] = 0
                                    participante_alvo.proximo_bonus_por_atributo = attr_map
                                participante_alvo.save()
                                a_piece = (f" + {a_next}" if a_next > 0 else (f" - {abs(a_next)}" if a_next < 0 else ""))
                                defesa_msg = (
                                    f"{base} + {defesa_val}"
                                    f"{' + ' + str(buff) if buff else ''}"
                                    f"{' - ' + str(debuff) if debuff else ''}"
                                    f"{a_piece} = {total}"
                                )
                                return total, defesa_msg, cd_uso

                            if rolagem_esq < cd_area:
                                # Falha na esquiva: usa CD cheia
                                total, defesa_msg, cd_uso = _teste_defesa(cd_area)
                                if total < cd_uso:
                                    if duracao_raw in ('concentracao', 'sustentado'):
                                        EfeitoConcentracao.objects.create(
                                            combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                            poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                        )
                                        resultado = (
                                            f"{alvo.nome} falhou esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd_area}); "
                                            f"teste de {defesa_attr} ({defesa_msg}) contra CD {cd_uso} — <b>Reduzido {val}</b> em {poder_atual.casting_ability.capitalize()} ({duracao_label})."
                                        )
                                    else:
                                        attr_map2 = participante_alvo.proximo_bonus_por_atributo or {}
                                        key = getattr(poder_atual, 'casting_ability', None)
                                        if key:
                                            attr_map2[key] = int(attr_map2.get(key, 0)) + val
                                            participante_alvo.proximo_bonus_por_atributo = attr_map2
                                        participante_alvo.save()
                                        resultado = (
                                            f"{alvo.nome} falhou esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd_area}); "
                                            f"teste de {defesa_attr} ({defesa_msg}) contra CD {cd_uso} — <b>Reduzido {val}</b> na próxima rolagem de {getattr(poder_atual, 'casting_ability', '').capitalize()}."
                                        )
                                else:
                                    resultado = (
                                        f"{alvo.nome} falhou esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd_area}); "
                                        f"teste de {defesa_attr} ({defesa_msg}) contra CD {cd_uso} — sem efeito."
                                    )
                            else:
                                # Sucesso parcial na esquiva: CD reduzida
                                total, defesa_msg, cd_uso = _teste_defesa(cd_sucesso)
                                if total < cd_uso:
                                    if duracao_raw in ('concentracao', 'sustentado'):
                                        EfeitoConcentracao.objects.create(
                                            combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                            poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                        )
                                        resultado = (
                                            f"{alvo.nome} sucesso parcial esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd_area}); "
                                            f"teste de {defesa_attr} ({defesa_msg}) contra CD {cd_uso} — <b>Reduzido {val}</b> em {poder_atual.casting_ability.capitalize()} ({duracao_label})."
                                        )
                                    else:
                                        attr_map2 = participante_alvo.proximo_bonus_por_atributo or {}
                                        key = getattr(poder_atual, 'casting_ability', None)
                                        if key:
                                            attr_map2[key] = int(attr_map2.get(key, 0)) + val
                                            participante_alvo.proximo_bonus_por_atributo = attr_map2
                                        participante_alvo.save()
                                        resultado = (
                                            f"{alvo.nome} sucesso parcial esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd_area}); "
                                            f"teste de {defesa_attr} ({defesa_msg}) contra CD {cd_uso} — <b>Reduzido {val}</b> na próxima rolagem de {getattr(poder_atual, 'casting_ability', '').capitalize()}."
                                        )
                                else:
                                    resultado = (
                                        f"{alvo.nome} sucesso parcial esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd_area}); "
                                        f"teste de {defesa_attr} ({defesa_msg}) contra CD {cd_uso} — sem efeito."
                                    )
                        else:
                            # Percepção (ou outros): teste direto na defesa passiva
                            defesa_attr = getattr(poder_atual, 'defesa_passiva', 'vontade') or 'vontade'
                            buff = participante_alvo.bonus_temporario
                            debuff = participante_alvo.penalidade_temporaria
                            attr_map = participante_alvo.proximo_bonus_por_atributo or {}
                            a_next = int(attr_map.get(defesa_attr, 0))
                            base = random.randint(1, 20)
                            defesa_val = _atributo_efetivo(alvo, participante_alvo, defesa_attr, combate.id)
                            total = base + defesa_val + a_next + buff - debuff
                            participante_alvo.bonus_temporario = 0
                            participante_alvo.penalidade_temporaria = 0
                            if a_next:
                                try:
                                    del attr_map[defesa_attr]
                                except Exception:
                                    attr_map[defesa_attr] = 0
                                participante_alvo.proximo_bonus_por_atributo = attr_map
                            participante_alvo.save()
                            cd = 10 + abs(val)
                            a_piece = (f" + {a_next}" if a_next > 0 else (f" - {abs(a_next)}" if a_next < 0 else ""))
                            defesa_msg = (
                                f"{base} + {defesa_val}"
                                f"{' + ' + str(buff) if buff else ''}"
                                f"{' - ' + str(debuff) if debuff else ''}"
                                f"{a_piece} = {total}"
                            )
                            if total < cd:
                                if duracao_raw in ('concentracao', 'sustentado'):
                                    EfeitoConcentracao.objects.create(
                                        combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                        poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                    )
                                    resultado = (
                                        f"{alvo.nome} falhou o teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — "
                                        f"<b>Reduzido {val}</b> em {poder_atual.casting_ability.capitalize()} ({duracao_label})."
                                    )
                                else:
                                    attr_map2 = participante_alvo.proximo_bonus_por_atributo or {}
                                    key = getattr(poder_atual, 'casting_ability', None)
                                    if key:
                                        attr_map2[key] = int(attr_map2.get(key, 0)) + val
                                        participante_alvo.proximo_bonus_por_atributo = attr_map2
                                    participante_alvo.save()
                                    resultado = (
                                        f"{alvo.nome} falhou o teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — "
                                        f"<b>Reduzido {val}</b> na próxima rolagem de {getattr(poder_atual, 'casting_ability', '').capitalize()}."
                                    )
                            else:
                                resultado = (
                                    f"{alvo.nome} resistiu a {poder_atual.nome}: teste de {defesa_attr} ({defesa_msg}) contra CD {cd} — sem efeito."
                                )
                    else:
                        # Valor positivo segue regra atual (não exige teste)
                        if duracao_raw in ('concentracao', 'sustentado'):
                            EfeitoConcentracao.objects.create(
                                combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                            )
                            sign_val = f"+{val}" if val >= 0 else f"{val}"
                            resultado = f"{alvo.nome} fica Aprimorado: {sign_val} em {poder_atual.casting_ability.capitalize()} ({duracao_label})."
                        else:
                            # Instantâneo positivo: bônus específico para a próxima rolagem
                            attr_map = participante_alvo.proximo_bonus_por_atributo or {}
                            key = getattr(poder_atual, 'casting_ability', None)
                            if key:
                                attr_map[key] = int(attr_map.get(key, 0)) + val
                                participante_alvo.proximo_bonus_por_atributo = attr_map
                            participante_alvo.save()
                            sign_val = f"+{val}" if val >= 0 else f"{val}"
                            resultado = f"{alvo.nome} recebe {sign_val} (Aprimorar instantâneo) na próxima rolagem de {getattr(poder_atual, 'casting_ability', '').capitalize()}."

                else:
                    # Modos ofensivos: area, percepcao, melee, ranged
                    # Auxiliares comuns
                    def resolve_defesa(def_attr, buff, debuff):
                        base = random.randint(1, 20)
                        val = _atributo_efetivo(alvo, participante_alvo, def_attr, combate.id)
                        # Bônus específico (Aprimorar instantâneo) para próxima rolagem daquela defesa
                        attr_map = participante_alvo.proximo_bonus_por_atributo or {}
                        a_next = int(attr_map.get(def_attr, 0))
                        total = base + val + a_next + buff - debuff
                        # Consome bônus específico por defesa
                        if a_next:
                            try:
                                del attr_map[def_attr]
                            except Exception:
                                attr_map[def_attr] = 0
                            participante_alvo.proximo_bonus_por_atributo = attr_map
                            participante_alvo.save()
                        return base, val, a_next, total

                    if modo == 'area':
                        esquiva = _defesa_efetiva(alvo, participante_alvo, 'esquivar', combate.id)
                        # Bônus específico (Aprimorar instantâneo) para próxima rolagem de Esquivar
                        esq_map = participante_alvo.proximo_bonus_por_atributo or {}
                        esq_next = int(esq_map.get('esquivar', 0))
                        rolagem_esq_base = random.randint(1, 20)
                        rolagem_esq = rolagem_esq_base + esquiva + esq_next
                        # Consome bônus específico de Esquivar
                        if esq_next:
                            try:
                                del esq_map['esquivar']
                            except Exception:
                                esq_map['esquivar'] = 0
                            participante_alvo.proximo_bonus_por_atributo = esq_map
                            participante_alvo.save()
                        # CD base usa nível efetivo
                        try:
                            if tipo == 'dano' and getattr(poder_atual, 'modo', '') == 'melee' and getattr(poder_atual, 'somar_forca_no_nivel', False):
                                # Usa Força efetiva do atacante (com Aprimorar/Reduzir)
                                forca_eff = _atributo_efetivo(atacante, participante_atacante, 'forca', combate.id)
                                n_eff = abs(int(getattr(poder_atual, 'nivel_efeito', 0) or 0)) + abs(int(forca_eff))
                            else:
                                n_eff = int(getattr(poder_atual, 'nivel_efeito', 0) or 0)
                        except Exception:
                            n_eff = int(getattr(poder_atual, 'nivel_efeito', 0) or 0)
                        cd = (15 if tipo == 'dano' else 10) + n_eff
                        cd_sucesso = ((15 if tipo == 'dano' else 10) + n_eff) // 2
                        cd_sucesso //= 2
                        defesa_attr = poder_atual.defesa_passiva
                        if rolagem_esq < cd:  # falhou esquiva
                            buff = participante_alvo.bonus_temporario
                            debuff = participante_alvo.penalidade_temporaria
                            d_base = random.randint(1, 20)
                            d_valor = _atributo_efetivo(alvo, participante_alvo, defesa_attr, combate.id)
                            # Bônus específico para próxima rolagem daquela defesa
                            a_map = participante_alvo.proximo_bonus_por_atributo or {}
                            a_next = int(a_map.get(defesa_attr, 0))
                            d_total = d_base + d_valor + a_next + buff - debuff
                            participante_alvo.bonus_temporario = 0
                            participante_alvo.penalidade_temporaria = 0
                            participante_alvo.save()
                            # Consome bônus específico por defesa
                            if a_next:
                                try:
                                    del a_map[defesa_attr]
                                except Exception:
                                    a_map[defesa_attr] = 0
                                participante_alvo.proximo_bonus_por_atributo = a_map
                                participante_alvo.save()
                            a_piece = (f" + {a_next}" if a_next > 0 else (f" - {abs(a_next)}" if a_next < 0 else ""))
                            defesa_msg = (
                                f"{d_base} + {d_valor}"
                                f"{' + ' + str(buff) if buff else ''}"
                                f"{' - ' + str(debuff) if debuff else ''}"
                                f"{a_piece} = {d_total}"
                            )
                            esq_piece = (f" + {esq_next}" if esq_next > 0 else (f" - {abs(esq_next)}" if esq_next < 0 else ""))
                            if tipo == 'dano':
                                if d_total < cd:
                                    participante_alvo.dano += 1
                                    participante_alvo.save()
                                    if duracao_raw in ('concentracao', 'sustentado'):
                                        EfeitoConcentracao.objects.create(
                                            combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                            poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                        )
                                    resultado = f"{alvo.nome} falhou esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd}) {defesa_attr}: {defesa_msg} <b>Dano +1</b> ({poder_atual.nome})"
                                    manter_concentracao_apos_sofrer(participante_alvo)
                                else:
                                    resultado = f"{alvo.nome} falhou esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd}) {defesa_attr}: {defesa_msg} (sem dano) ({poder_atual.nome})"
                            else:
                                if d_total < cd:
                                    participante_alvo.aflicao += 1
                                    participante_alvo.save()
                                    if duracao_raw in ('concentracao', 'sustentado'):
                                        EfeitoConcentracao.objects.create(
                                            combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                            poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                        )
                                    resultado = f"{alvo.nome} falhou esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd}) {defesa_attr}: {defesa_msg} <b>Aflição +1</b> ({poder_atual.nome})"
                                    manter_concentracao_apos_sofrer(participante_alvo)
                                else:
                                    resultado = f"{alvo.nome} falhou esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd}) {defesa_attr}: {defesa_msg} (sem aflição) ({poder_atual.nome})"
                        else:  # sucesso parcial na esquiva
                            buff = participante_alvo.bonus_temporario
                            debuff = participante_alvo.penalidade_temporaria
                            d_base = random.randint(1, 20)
                            d_valor = _atributo_efetivo(alvo, participante_alvo, defesa_attr, combate.id)
                            a_map = participante_alvo.proximo_bonus_por_atributo or {}
                            a_next = int(a_map.get(defesa_attr, 0))
                            d_total = d_base + d_valor + a_next + buff - debuff
                            participante_alvo.bonus_temporario = 0
                            participante_alvo.penalidade_temporaria = 0
                            participante_alvo.save()
                            if a_next:
                                try:
                                    del a_map[defesa_attr]
                                except Exception:
                                    a_map[defesa_attr] = 0
                                participante_alvo.proximo_bonus_por_atributo = a_map
                                participante_alvo.save()
                            a_piece = (f" + {a_next}" if a_next > 0 else (f" - {abs(a_next)}" if a_next < 0 else ""))
                            defesa_msg = (
                                f"{d_base} + {d_valor}"
                                f"{' + ' + str(buff) if buff else ''}"
                                f"{' - ' + str(debuff) if debuff else ''}"
                                f"{a_piece} = {d_total}"
                            )
                            esq_piece = (f" + {esq_next}" if esq_next > 0 else (f" - {abs(esq_next)}" if esq_next < 0 else ""))
                            if tipo == 'dano':
                                if d_total < cd_sucesso:
                                    participante_alvo.dano += 1
                                    participante_alvo.save()
                                    if duracao_raw in ('concentracao', 'sustentado'):
                                        EfeitoConcentracao.objects.create(
                                            combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                            poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                        )
                                    resultado = f"{alvo.nome} sucesso parcial esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd}) {defesa_attr}: {defesa_msg} <b>Dano +1</b> ({poder_atual.nome})"
                                    manter_concentracao_apos_sofrer(participante_alvo)
                                else:
                                    resultado = f"{alvo.nome} sucesso parcial esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd}) {defesa_attr}: {defesa_msg} (sem dano) ({poder_atual.nome})"
                            else:
                                if d_total < cd_sucesso:
                                    participante_alvo.aflicao += 1
                                    participante_alvo.save()
                                    if duracao_raw in ('concentracao', 'sustentado'):
                                        EfeitoConcentracao.objects.create(
                                            combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                            poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                        )
                                    resultado = f"{alvo.nome} sucesso parcial esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd}) {defesa_attr}: {defesa_msg} <b>Aflição +1</b> ({poder_atual.nome})"
                                    manter_concentracao_apos_sofrer(participante_alvo)
                                else:
                                    resultado = f"{alvo.nome} sucesso parcial esquiva ({rolagem_esq_base}+{esquiva}{esq_piece}={rolagem_esq} vs {cd}) {defesa_attr}: {defesa_msg} (sem aflição) ({poder_atual.nome})"

                    elif modo == 'percepcao':
                        try:
                            if tipo == 'dano' and getattr(poder_atual, 'modo', '') == 'melee' and getattr(poder_atual, 'somar_forca_no_nivel', False):
                                forca_eff = _atributo_efetivo(atacante, participante_atacante, 'forca', combate.id)
                                n_eff = abs(int(getattr(poder_atual, 'nivel_efeito', 0) or 0)) + abs(int(forca_eff))
                            else:
                                n_eff = int(getattr(poder_atual, 'nivel_efeito', 0) or 0)
                        except Exception:
                            n_eff = int(getattr(poder_atual, 'nivel_efeito', 0) or 0)
                        cd = (15 if tipo == 'dano' else 10) + n_eff
                        defesa_attr = poder_atual.defesa_passiva
                        buff = participante_alvo.bonus_temporario
                        debuff = participante_alvo.penalidade_temporaria
                        base, val, a_next, total = resolve_defesa(defesa_attr, buff, debuff)
                        participante_alvo.bonus_temporario = 0
                        participante_alvo.penalidade_temporaria = 0
                        participante_alvo.save()
                        a_piece = (f" + {a_next}" if a_next > 0 else (f" - {abs(a_next)}" if a_next < 0 else ""))
                        defesa_msg = (
                            f"{base} + {val}"
                            f"{' + ' + str(buff) if buff else ''}"
                            f"{' - ' + str(debuff) if debuff else ''}"
                            f"{a_piece} = {total}"
                        )
                        if tipo == 'dano':
                            if total < cd:
                                participante_alvo.dano += 1
                                participante_alvo.save()
                                if duracao_raw in ('concentracao', 'sustentado'):
                                    EfeitoConcentracao.objects.create(
                                        combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                        poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                    )
                                resultado = f"{alvo.nome} teste {defesa_attr} ({defesa_msg}) vs CD {cd}: <b>Dano +1</b> ({poder_atual.nome})"
                                manter_concentracao_apos_sofrer(participante_alvo)
                            else:
                                resultado = f"{alvo.nome} teste {defesa_attr} ({defesa_msg}) vs CD {cd}: sem dano ({poder_atual.nome})"
                        else:
                            if total < cd:
                                participante_alvo.aflicao += 1
                                participante_alvo.save()
                                if duracao_raw in ('concentracao', 'sustentado'):
                                    EfeitoConcentracao.objects.create(
                                        combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                        poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                    )
                                resultado = f"{alvo.nome} teste {defesa_attr} ({defesa_msg}) vs CD {cd}: <b>Aflição +1</b> ({poder_atual.nome})"
                                manter_concentracao_apos_sofrer(participante_alvo)
                            else:
                                resultado = f"{alvo.nome} teste {defesa_attr} ({defesa_msg}) vs CD {cd}: sem aflição ({poder_atual.nome})"

                    elif modo in ('melee', 'ranged'):
                        # Shared attack vs aparar/esquivar (reuse for encadeado)
                        st = _get_shared_attack_state_for_target(alvo_id)
                        is_melee = (modo == 'melee')
                        if is_melee and st.get('hit_melee') is None:
                            aparar = getattr(alvo, 'aparar', 0)
                            atk_total = st['d20'] + st['base_melee'] + st['max_melee'] + st['buff_att'] - st['debuff_att']
                            st['atk_total_melee'] = atk_total
                            st['hit_melee'] = atk_total > 10 + aparar
                            st['atk_msg_melee'] = (
                                f"{st['d20']} + {st['base_melee']} + {st['max_melee']}"
                                f"{' + ' + str(st['buff_att']) if st['buff_att'] else ''}"
                                f"{' - ' + str(st['debuff_att']) if st['debuff_att'] else ''} = {atk_total}"
                            )
                            st['aparar'] = aparar
                        if (not is_melee) and st.get('hit_ranged') is None:
                            esquivar = getattr(alvo, 'esquivar', 0)
                            atk_total = st['d20'] + st['base_ranged'] + st['max_ranged'] + st['buff_att'] - st['debuff_att']
                            st['atk_total_ranged'] = atk_total
                            st['hit_ranged'] = atk_total > 10 + esquivar
                            st['atk_msg_ranged'] = (
                                f"{st['d20']} + {st['base_ranged']} + {st['max_ranged']}"
                                f"{' + ' + str(st['buff_att']) if st['buff_att'] else ''}"
                                f"{' - ' + str(st['debuff_att']) if st['debuff_att'] else ''} = {atk_total}"
                            )
                            st['esquivar'] = esquivar
                        hit_now = st['hit_melee'] if is_melee else st['hit_ranged']
                        atk_msg = st['atk_msg_melee'] if is_melee else st['atk_msg_ranged']
                        defesa_mov_val = 10 + (st['aparar'] if is_melee else st['esquivar'])
                        logged_flag = 'logged_melee' if is_melee else 'logged_ranged'
                        if hit_now:
                            defesa_attr = poder_atual.defesa_passiva
                            buff = participante_alvo.bonus_temporario
                            debuff = participante_alvo.penalidade_temporaria
                            d_base, d_val, a_next, d_total = resolve_defesa(defesa_attr, buff, debuff)
                            participante_alvo.bonus_temporario = 0
                            participante_alvo.penalidade_temporaria = 0
                            participante_alvo.save()
                            ataque_msg = atk_msg
                            a_piece = (f" + {a_next}" if a_next > 0 else (f" - {abs(a_next)}" if a_next < 0 else ""))
                            defesa_msg = (
                                f"{d_base} + {d_val}"
                                f"{' + ' + str(buff) if buff else ''}"
                                f"{' - ' + str(debuff) if debuff else ''}"
                                f"{a_piece} = {d_total}"
                            )
                            try:
                                if tipo == 'dano' and getattr(poder_atual, 'modo', '') == 'melee' and getattr(poder_atual, 'somar_forca_no_nivel', False):
                                    forca_eff2 = _atributo_efetivo(atacante, participante_atacante, 'forca', combate.id)
                                    n_eff2 = abs(int(getattr(poder_atual, 'nivel_efeito', 0) or 0)) + abs(int(forca_eff2))
                                else:
                                    n_eff2 = int(getattr(poder_atual, 'nivel_efeito', 0) or 0)
                            except Exception:
                                n_eff2 = int(getattr(poder_atual, 'nivel_efeito', 0) or 0)
                            cd = (15 if tipo == 'dano' else 10) + n_eff2
                            if tipo == 'dano':
                                if d_total < cd:
                                    participante_alvo.dano += 1
                                    participante_alvo.save()
                                    if duracao_raw in ('concentracao', 'sustentado'):
                                        EfeitoConcentracao.objects.create(
                                            combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                            poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                        )
                                    if not st[logged_flag]:
                                        resultado = f"{atacante.nome} acertou {alvo.nome} (atk {ataque_msg} vs {defesa_mov_val}) {defesa_attr} ({defesa_msg}) CD {cd} <b>Dano +1</b> ({poder_atual.nome})"
                                        st[logged_flag] = True
                                    else:
                                        resultado = f"{atacante.nome} acertou {alvo.nome} {defesa_attr} ({defesa_msg}) CD {cd} <b>Dano +1</b> ({poder_atual.nome})"
                                    manter_concentracao_apos_sofrer(participante_alvo)
                                else:
                                    if not st[logged_flag]:
                                        resultado = f"{atacante.nome} acertou {alvo.nome} (atk {ataque_msg} vs {defesa_mov_val}) {defesa_attr} ({defesa_msg}) CD {cd} (sem dano) ({poder_atual.nome})"
                                        st[logged_flag] = True
                                    else:
                                        resultado = f"{atacante.nome} acertou {alvo.nome} {defesa_attr} ({defesa_msg}) CD {cd} (sem dano) ({poder_atual.nome})"
                            else:
                                if d_total < cd:
                                    participante_alvo.aflicao += 1
                                    participante_alvo.save()
                                    if duracao_raw in ('concentracao', 'sustentado'):
                                        EfeitoConcentracao.objects.create(
                                            combate=combate, aplicador=atacante, alvo_participante=participante_alvo,
                                            poder=poder_atual, rodada_inicio=turno_ativo.ordem if turno_ativo else 0
                                        )
                                    if not st[logged_flag]:
                                        resultado = f"{atacante.nome} acertou {alvo.nome} (atk {ataque_msg} vs {defesa_mov_val}) {defesa_attr} ({defesa_msg}) CD {cd} <b>Aflição +1</b> ({poder_atual.nome})"
                                        st[logged_flag] = True
                                    else:
                                        resultado = f"{atacante.nome} acertou {alvo.nome} {defesa_attr} ({defesa_msg}) CD {cd} <b>Aflição +1</b> ({poder_atual.nome})"
                                    manter_concentracao_apos_sofrer(participante_alvo)
                                else:
                                    if not st[logged_flag]:
                                        resultado = f"{atacante.nome} acertou {alvo.nome} (atk {ataque_msg} vs {defesa_mov_val}) {defesa_attr} ({defesa_msg}) CD {cd} (sem aflição) ({poder_atual.nome})"
                                        st[logged_flag] = True
                                    else:
                                        resultado = f"{atacante.nome} acertou {alvo.nome} {defesa_attr} ({defesa_msg}) CD {cd} (sem aflição) ({poder_atual.nome})"
                        else:
                            if st[logged_flag]:
                                # We've already logged the miss for this kind in this chain; skip duplicates
                                continue
                            resultado = f"{atacante.nome} errou {alvo.nome} (atk {atk_msg} vs {defesa_mov_val}) ({poder_atual.nome})"
                            st[logged_flag] = True
                    else:
                        resultado = f"Ação inválida para o poder selecionado ({poder_atual.nome})."

                if resultado:
                    resultados.append(resultado)

        nova_descricao = "<br>".join(resultados)
        append_to_turno(nova_descricao)
        send_event('rolagem', nova_descricao)
        if _expects_json(request):
            return JsonResponse({'status': 'ok', 'evento': 'rolagem', 'descricao': nova_descricao})
        return redirect('detalhes_combate', combate_id=combate_id)

    return redirect('detalhes_combate', combate_id=combate_id)

@login_required
def remover_participante(request, combate_id, participante_id):
    if not hasattr(request.user, 'perfilusuario') or request.user.perfilusuario.tipo != 'game_master' or not request.user.salas_gm.exists():
        return redirect('home')
    participante = get_object_or_404(Participante, id=participante_id, combate_id=combate_id)
    nome = participante.personagem.nome
    # Encerra concentrações ligadas a este participante (como alvo) ou aplicador
    try:
        EfeitoConcentracao.objects.filter(
            Q(alvo_participante=participante) | Q(aplicador=participante.personagem),
            combate_id=combate_id,
            ativo=True
        ).update(ativo=False)
    except Exception:
        logger.warning("Falha ao encerrar efeitos de concentração ao remover participante", exc_info=True)
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

@login_required
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

@login_required
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

@login_required
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

@login_required
def adicionar_participante(request, combate_id):
    """Adiciona um personagem jogador existente (não NPC) ao combate. Recriado após remoção anterior.
    Regras:
      - Usuário deve ser GM da sala OU dono do personagem (autoadicionar).
      - Personagem não pode já estar participando.
    """
    if request.method != 'POST':
        return redirect('detalhes_combate', combate_id=combate_id)
    combate = get_object_or_404(Combate, id=combate_id)
    sala = combate.sala
    personagem_id = request.POST.get('personagem_id')
    personagem = get_object_or_404(Personagem, id=personagem_id, is_npc=False)
    # Permissão: GM da sala ou dono do personagem (e personagem na mesma sala)
    if not (sala.game_master_id == request.user.id or personagem.usuario_id == request.user.id):
        return redirect('detalhes_combate', combate_id=combate_id)
    if personagem.sala_id != sala.id:
        return redirect('detalhes_combate', combate_id=combate_id)
    if Participante.objects.filter(combate=combate, personagem=personagem).exists():
        return redirect('detalhes_combate', combate_id=combate_id)
    iniciativa = random.randint(1, 20) + personagem.prontidao
    participante = Participante.objects.create(personagem=personagem, combate=combate, iniciativa=iniciativa)
    # Cria token inicial em todos os mapas
    for mapa in combate.mapas.all():
        if not PosicaoPersonagem.objects.filter(mapa=mapa, participante=participante).exists():
            PosicaoPersonagem.objects.create(mapa=mapa, participante=participante, x=10, y=10)
    # Notifica canais
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
                        'is_npc': False,
                    }
                })
            }
        )
    except Exception:
        logger.warning("Falha ao enviar evento 'adicionar_participante' (PC) via Channels (ignorado)", exc_info=True)
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
                'is_npc': False,
            }
        })
    return redirect('detalhes_combate', combate_id=combate_id)