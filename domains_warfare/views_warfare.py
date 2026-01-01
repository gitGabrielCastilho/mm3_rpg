"""
Views para o sistema de Warfare Combat.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core import signing
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
import json
from typing import List
from personagens.models import PerfilUsuario
from combate.models import Mapa
from .models import Domain, Unit
from .models_warfare import (
    CombateWarfare,
    ParticipanteWarfare,
    StatusUnitWarfare,
    TurnoWarfare,
    MapaWarfare,
    PosicaoUnitWarfare,
)
import random


@login_required
def warfare_criar(request):
    """Página para criar um novo combate warfare."""
    try:
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or not perfil.sala_atual:
            messages.error(request, "Você precisa estar em uma sala para criar um combate warfare.")
            return redirect('listar_salas')
        
        # Apenas GM pode criar combates warfare
        sala = perfil.sala_atual
        if sala.game_master != request.user:
            messages.error(request, "Apenas o GM pode criar combates warfare.")
            return redirect('domain_list')
        
        if request.method == 'POST':
            domain_ids = request.POST.getlist('domains')
            nome_combate = request.POST.get('nome', 'Combate Warfare')
            
            if not domain_ids or len(domain_ids) < 2:
                messages.error(request, "Selecione pelo menos 2 domains para iniciar o combate.")
                return redirect('warfare_criar')
            
            # Criar combate
            combate = CombateWarfare.objects.create(
                sala=perfil.sala_atual,
                nome=nome_combate,
                criador=request.user
            )
            
            # Adicionar domains participantes
            for idx, domain_id in enumerate(domain_ids):
                domain = get_object_or_404(Domain, pk=domain_id, sala=perfil.sala_atual)
                ParticipanteWarfare.objects.create(
                    combate=combate,
                    domain=domain,
                    ordem_iniciativa=idx
                )
                
                # Criar status para todas as unidades do domain
                for unit in domain.units.all():
                    # HP = Size da unidade (d4=4, d6=6, d8=8, d10=10, d12=12)
                    hp_max = _get_hp_from_size(unit.size)
                    StatusUnitWarfare.objects.create(
                        combate=combate,
                        unit=unit,
                        hp_atual=hp_max,
                        hp_maximo=hp_max
                    )
            
            messages.success(request, f"Combate '{combate.nome}' iniciado com sucesso!")
            return redirect('warfare_detalhes', pk=combate.pk)
        
        # GET: Listar domains disponíveis
        # GM pode ver todos, jogadores veem apenas os seus
        if sala.game_master == request.user:
            domains = Domain.objects.filter(sala=perfil.sala_atual).order_by('nome')
        else:
            domains = Domain.objects.filter(
                sala=perfil.sala_atual
            ).filter(
                Q(criador=request.user) | Q(jogadores_acesso=request.user)
            ).distinct().order_by('nome')
        
        context = {
            'domains': domains,
        }
        return render(request, 'domains_warfare/warfare_criar.html', context)
        
    except Exception as e:
        messages.error(request, f"Erro ao criar combate: {str(e)}")
        return redirect('domain_list')


def _get_hp_from_size(size):
    """Converte o Size da unidade em HP."""
    if not size:
        return 6  # Default 1d6
    
    nome_size = size.get_nome_display().lower() if hasattr(size, 'get_nome_display') else str(size).lower()
    
    if '1d4' in nome_size or 'd4' in nome_size:
        return 4
    elif '1d6' in nome_size or 'd6' in nome_size:
        return 6
    elif '1d8' in nome_size or 'd8' in nome_size:
        return 8
    elif '1d10' in nome_size or 'd10' in nome_size:
        return 10
    elif '1d12' in nome_size or 'd12' in nome_size:
        return 12
    else:
        return 6  # Default


@login_required
def warfare_detalhes(request, pk):
    """Página de detalhes/sala de combate warfare."""
    try:
        combate = get_object_or_404(CombateWarfare, pk=pk)
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or perfil.sala_atual != combate.sala:
            messages.error(request, "Você não tem acesso a este combate.")
            return redirect('domain_list')
        
        # Verificar se o usuário tem acesso (GM ou participa de algum domain)
        user_domains = Domain.objects.filter(
            Q(criador=request.user) | Q(jogadores_acesso=request.user),
            participacoes_warfare__combate=combate
        ).distinct()
        
        if combate.sala.game_master != request.user and not user_domains.exists():
            messages.error(request, "Você não participa deste combate.")
            return redirect('domain_list')
        
        # Listar participantes (domains)
        participantes = combate.participantes.select_related('domain').order_by('ordem_iniciativa')
        
        # Listar todas as unidades em combate com status
        units_status = []
        for participante in participantes:
            for unit in participante.domain.units.all():
                # Buscar ou criar status se não existir
                status, created = StatusUnitWarfare.objects.get_or_create(
                    combate=combate,
                    unit=unit,
                    defaults={
                        'hp_maximo': _get_hp_from_size(unit.size),
                        'hp_atual': _get_hp_from_size(unit.size)
                    }
                )
                units_status.append({
                    'unit': unit,
                    'domain': participante.domain,
                    'status': status,
                    'atributos': unit.get_atributos_finais(),
                })
        
        # Histórico de turnos
        turnos = combate.turnos_warfare.select_related(
            'unit_atacante', 'unit_alvo'
        ).order_by('-criado_em')[:50]
        
        # Turno ativo
        turno_ativo = combate.get_turno_ativo()
        
        # Mapas (usar todos, não apenas ativos)
        mapas = combate.mapas_warfare.all()
        mapa_ativo = mapas.first()
        posicoes = PosicaoUnitWarfare.objects.filter(mapa__combate=combate).select_related('mapa', 'unit')

        mapas_globais = []
        if combate.sala.game_master == request.user:
            mapas_globais = Mapa.objects.filter(combate__isnull=True, criado_por=request.user).order_by('-id')
        
        context = {
            'combate': combate,
            'participantes': participantes,
            'units_status': units_status,
            'turnos': turnos,
            'turno_ativo': turno_ativo,
            'mapas': mapas,
            'mapa_ativo': mapa_ativo,
            'posicoes': posicoes,
            'is_gm': combate.sala.game_master == request.user,
            'mapas_globais': mapas_globais,
            'ws_token': signing.dumps({'uid': request.user.id}, salt='ws-combate'),
        }
        return render(request, 'domains_warfare/warfare_detalhes.html', context)
        
    except Exception as e:
        messages.error(request, f"Erro ao carregar combate: {str(e)}")
        return redirect('domain_list')


@login_required
def warfare_listar(request):
    """Lista todos os combates warfare da sala."""
    try:
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or not perfil.sala_atual:
            messages.error(request, "Você precisa estar em uma sala.")
            return redirect('listar_salas')
        
        # Listar combates da sala
        sala = perfil.sala_atual
        if sala.game_master == request.user:
            combates = CombateWarfare.objects.filter(sala=perfil.sala_atual).order_by('-criado_em')
        else:
            # Jogadores veem apenas combates dos quais participam
            user_domains = Domain.objects.filter(
                Q(criador=request.user) | Q(jogadores_acesso=request.user)
            ).distinct()
            
            combates = CombateWarfare.objects.filter(
                sala=perfil.sala_atual,
                domains__in=user_domains
            ).distinct().order_by('-criado_em')
        
        context = {
            'combates': combates,
        }
        return render(request, 'domains_warfare/warfare_listar.html', context)
        
    except Exception as e:
        messages.error(request, f"Erro ao listar combates: {str(e)}")
        return redirect('domain_list')


@login_required
def warfare_finalizar(request, pk):
    """Finaliza um combate warfare."""
    if request.method != 'POST':
        return redirect('warfare_detalhes', pk=pk)
    
    try:
        combate = get_object_or_404(CombateWarfare, pk=pk)
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or perfil.sala_atual != combate.sala:
            messages.error(request, "Você não tem acesso a este combate.")
            return redirect('domain_list')
        
        # Apenas GM pode finalizar
        if combate.sala.game_master != request.user:
            messages.error(request, "Apenas o GM pode finalizar o combate.")
            return redirect('warfare_detalhes', pk=pk)
        
        combate.ativo = False
        combate.save()
        
        messages.success(request, f"Combate '{combate.nome}' finalizado.")
        return redirect('warfare_listar')
        
    except Exception as e:
        messages.error(request, f"Erro ao finalizar combate: {str(e)}")
        return redirect('warfare_detalhes', pk=pk)


@login_required
def warfare_deletar(request, pk):
    """Deleta um combate warfare (apenas GM)."""
    if request.method != 'POST':
        return redirect('warfare_listar')
    
    try:
        combate = get_object_or_404(CombateWarfare, pk=pk)
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or perfil.sala_atual != combate.sala:
            messages.error(request, "Você não tem acesso a este combate.")
            return redirect('domain_list')
        
        # Apenas GM pode deletar
        if combate.sala.game_master != request.user:
            messages.error(request, "Apenas o GM pode deletar o combate.")
            return redirect('warfare_listar')
        
        nome_combate = combate.nome
        combate.delete()
        
        messages.success(request, f"Combate '{nome_combate}' deletado com sucesso.")
        return redirect('warfare_listar')
        
    except Exception as e:
        messages.error(request, f"Erro ao deletar combate: {str(e)}")
        return redirect('warfare_listar')


@login_required
def warfare_adicionar_mapa(request, pk):
    """Adiciona um mapa ao combate warfare."""
    try:
        combate = get_object_or_404(CombateWarfare, pk=pk)
        perfil = PerfilUsuario.objects.filter(user=request.user).first()

        if not perfil or perfil.sala_atual != combate.sala:
            messages.error(request, "Você não tem acesso a este combate.")
            return redirect('domain_list')

        # Apenas GM pode adicionar mapas
        if combate.sala.game_master != request.user:
            messages.error(request, "Apenas o GM pode adicionar mapas.")
            return redirect('warfare_detalhes', pk=pk)

        # POST: clonar mapa global existente
        if request.method == 'POST':
            mapa_id = request.POST.get('mapa_existente') or request.POST.get('mapa_id')
            if not mapa_id:
                messages.error(request, "Selecione um mapa existente para usar.")
                return redirect('warfare_detalhes', pk=pk)

            mapa_base = get_object_or_404(
                Mapa,
                id=mapa_id,
                combate__isnull=True,
                criado_por=request.user,
            )

            mapa = MapaWarfare.objects.create(
                combate=combate,
                nome=mapa_base.nome,
                imagem=mapa_base.imagem,
            )
            for status in combate.status_units.all():
                PosicaoUnitWarfare.objects.get_or_create(
                    mapa=mapa,
                    unit=status.unit,
                    defaults={'x': 50, 'y': 50},
                )
            messages.success(request, f"Mapa '{mapa.nome}' adicionado com sucesso!")
            return redirect('warfare_detalhes', pk=pk)

        # GET: redireciona para a página de detalhes (criação ocorre via mapa global)
        return redirect('warfare_detalhes', pk=pk)

    except Exception as e:
        messages.error(request, f"Erro ao adicionar mapa: {str(e)}")
        return redirect('warfare_detalhes', pk=pk)


@login_required
def warfare_remover_mapa(request, pk, mapa_id):
    """Remove um mapa do combate warfare (apenas GM)."""
    if request.method != 'POST':
        return redirect('warfare_detalhes', pk=pk)

    try:
        combate = get_object_or_404(CombateWarfare, pk=pk)
        perfil = PerfilUsuario.objects.filter(user=request.user).first()

        if not perfil or perfil.sala_atual != combate.sala:
            messages.error(request, "Você não tem acesso a este combate.")
            return redirect('domain_list')

        if combate.sala.game_master != request.user:
            messages.error(request, "Apenas o GM pode remover mapas.")
            return redirect('warfare_detalhes', pk=pk)

        mapa = get_object_or_404(MapaWarfare, pk=mapa_id, combate=combate)
        nome = mapa.nome
        mapa.delete()

        messages.success(request, f"Mapa '{nome}' removido com sucesso.")
        return redirect('warfare_detalhes', pk=pk)

    except Exception as e:
        messages.error(request, f"Erro ao remover mapa: {str(e)}")
        return redirect('warfare_detalhes', pk=pk)


@login_required
def warfare_atualizar_posicao_token(request, pk, posicao_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'method_not_allowed'}, status=405)

    posicao = get_object_or_404(PosicaoUnitWarfare, id=posicao_id, mapa__combate_id=pk)
    combate = posicao.mapa.combate

    # Permissão: GM da sala ou jogador que controla o domain da unidade
    domain = posicao.unit.domain
    is_gm = combate.sala.game_master == request.user
    is_domain_owner = domain.criador_id == request.user.id
    has_access = domain.jogadores_acesso.filter(id=request.user.id).exists()
    if not (is_gm or is_domain_owner or has_access):
        return JsonResponse({'error': 'forbidden'}, status=403)

    try:
        data = json.loads(request.body or '{}')
    except Exception:
        data = {}

    try:
        posicao.x = float(data.get('x', posicao.x))
        posicao.y = float(data.get('y', posicao.y))
        size = data.get('size')
        if isinstance(size, (int, float)):
            posicao.token_size = max(10, min(200, int(size)))
        posicao.save()

        # Broadcast para todos conectados
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'warfare_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({
                    'evento': 'token_move',
                    'posicao_id': posicao.id,
                    'mapa_id': posicao.mapa_id,
                    'x': posicao.x,
                    'y': posicao.y,
                })
            }
        )
        if isinstance(size, (int, float)):
            async_to_sync(channel_layer.group_send)(
                f'warfare_{combate.id}',
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
        return JsonResponse({'error': 'server_error'}, status=500)

    return JsonResponse({'status': 'ok'})


@login_required
def warfare_resolver_ataque(request, pk):
    if request.method != 'POST':
        return redirect('warfare_detalhes', pk=pk)

    combate = get_object_or_404(CombateWarfare, pk=pk)
    perfil = PerfilUsuario.objects.filter(user=request.user).first()

    if not perfil or perfil.sala_atual != combate.sala:
        messages.error(request, "Você não tem acesso a este combate.")
        return redirect('domain_list')

    if not combate.ativo:
        messages.error(request, "Combate encerrado: não é possível atacar.")
        return redirect('warfare_detalhes', pk=pk)

    atacante_id = request.POST.get('atacante_id')
    alvo_id = request.POST.get('alvo_id')

    if not atacante_id or not alvo_id or atacante_id == alvo_id:
        messages.error(request, "Selecione atacante e alvo distintos.")
        return redirect('warfare_detalhes', pk=pk)

    atacante = get_object_or_404(
        Unit,
        pk=atacante_id,
        domain__participacoes_warfare__combate=combate,
    )
    alvo = get_object_or_404(
        Unit,
        pk=alvo_id,
        domain__participacoes_warfare__combate=combate,
    )

    is_gm = combate.sala.game_master_id == request.user.id
    controla_atacante = (
        is_gm
        or atacante.domain.criador_id == request.user.id
        or atacante.domain.jogadores_acesso.filter(id=request.user.id).exists()
    )
    if not controla_atacante:
        messages.error(request, "Você não pode agir com esta unidade.")
        return redirect('warfare_detalhes', pk=pk)

    status_atacante, _ = StatusUnitWarfare.objects.get_or_create(
        combate=combate,
        unit=atacante,
        defaults={
            'hp_maximo': _get_hp_from_size(atacante.size),
            'hp_atual': _get_hp_from_size(atacante.size),
        }
    )
    status_alvo, _ = StatusUnitWarfare.objects.get_or_create(
        combate=combate,
        unit=alvo,
        defaults={
            'hp_maximo': _get_hp_from_size(alvo.size),
            'hp_atual': _get_hp_from_size(alvo.size),
        }
    )

    if status_atacante.incapacitado:
        messages.error(request, "A unidade atacante está incapacitada.")
        return redirect('warfare_detalhes', pk=pk)
    if status_alvo.incapacitado:
        messages.error(request, "O alvo já está incapacitado.")
        return redirect('warfare_detalhes', pk=pk)

    atributos_atacante = atacante.get_atributos_finais()
    atributos_alvo = alvo.get_atributos_finais()

    roll_ataque_d20 = random.randint(1, 20)
    ataque_total = roll_ataque_d20 + atributos_atacante.get('ataque', 0)
    sucesso_ataque = ataque_total >= atributos_alvo.get('defesa', 0)

    roll_poder_total = None
    sucesso_poder = False
    dano_total = 0

    if sucesso_ataque:
        roll_poder_d20 = random.randint(1, 20)
        roll_poder_total = roll_poder_d20 + atributos_atacante.get('poder', 0)
        sucesso_poder = roll_poder_total >= atributos_alvo.get('resistencia', 0)
        if sucesso_poder:
            dano_total += 1

    half_threshold = status_alvo.hp_maximo / 2
    moral_dc = 10
    roll_moral_total = None
    falha_moral = False
    moral_logs: List[str] = []
    hp_antes = status_alvo.hp_atual

    def roda_moral(label: str):
        nonlocal dano_total, roll_moral_total, falha_moral
        roll = random.randint(1, 20) + atributos_alvo.get('moral', 0)
        roll_moral_total = roll
        if roll < moral_dc:
            falha_moral = True
            dano_total += 1
            moral_logs.append(f"{label}: falhou ({roll} < {moral_dc})")
        else:
            moral_logs.append(f"{label}: sucesso ({roll} ≥ {moral_dc})")

    if status_alvo.hp_atual <= half_threshold:
        roda_moral('Moral (atacado ≤50%)')

    hp_proj = status_alvo.hp_atual - dano_total
    if status_alvo.hp_atual > half_threshold and hp_proj <= half_threshold:
        roda_moral('Moral (ficou ≤50%)')

    if dano_total > 0:
        status_alvo.aplicar_dano(dano_total)
    else:
        if status_alvo.hp_atual <= half_threshold and not status_alvo.diminished:
            status_alvo.diminished = True
            status_alvo.save(update_fields=['diminished', 'atualizado_em'])

    hp_depois = status_alvo.hp_atual

    descricao_partes = [
        f"Ataque d20 ({roll_ataque_d20}) + ATQ {atributos_atacante.get('ataque', 0)} = {ataque_total} vs DEF {atributos_alvo.get('defesa', 0)}",
        "acertou" if sucesso_ataque else "errou",
    ]

    if sucesso_ataque:
        if roll_poder_total is not None:
            descricao_partes.append(
                f"Poder: {roll_poder_total} vs RES {atributos_alvo.get('resistencia', 0)}"
            )
            descricao_partes.append("causou dano" if sucesso_poder else "poder resistido")
    if moral_logs:
        descricao_partes.extend(moral_logs)
    descricao_partes.append(f"Dano total: {dano_total}")
    descricao_partes.append(f"HP alvo: {hp_antes} → {hp_depois}")
    descricao = " | ".join(descricao_partes)

    ordem = combate.turnos_warfare.count() + 1
    turno = TurnoWarfare.objects.create(
        combate=combate,
        unit_atacante=atacante,
        unit_alvo=alvo,
        ordem=ordem,
        ativo=False,
        tipo_acao='ataque',
        roll_ataque=ataque_total,
        roll_poder=roll_poder_total,
        roll_moral=roll_moral_total,
        sucesso_ataque=sucesso_ataque,
        sucesso_poder=sucesso_poder,
        falha_moral=falha_moral,
        dano_causado=dano_total,
        descricao=descricao,
    )

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'warfare_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({
                    'evento': 'ataque',
                    'turno': {
                        'id': turno.id,
                        'hora': turno.criado_em.strftime('%H:%M'),
                        'atacante_nome': atacante.nome,
                        'atacante_domain': atacante.domain.nome,
                        'alvo_nome': alvo.nome,
                        'alvo_domain': alvo.domain.nome,
                        'sucesso_ataque': sucesso_ataque,
                        'sucesso_poder': sucesso_poder,
                        'roll_ataque': ataque_total,
                        'roll_poder': roll_poder_total,
                        'roll_moral': roll_moral_total,
                        'dano': dano_total,
                        'defesa': atributos_alvo.get('defesa', 0),
                        'resistencia': atributos_alvo.get('resistencia', 0),
                        'descricao': descricao,
                    },
                    'alvo_status': {
                        'unit_id': alvo.id,
                        'hp_atual': status_alvo.hp_atual,
                        'hp_max': status_alvo.hp_maximo,
                        'diminished': status_alvo.diminished,
                        'incapacitado': status_alvo.incapacitado,
                    }
                })
            }
        )
    except Exception:
        pass

    messages.success(
        request,
        f"{atacante.nome} atacou {alvo.nome}: {'acertou' if sucesso_ataque else 'errou'}; dano {dano_total}."
    )
    return redirect('warfare_detalhes', pk=pk)


@login_required
def warfare_ajustar_hp_unit(request, pk, unit_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'method_not_allowed'}, status=405)

    combate = get_object_or_404(CombateWarfare, pk=pk)
    perfil = PerfilUsuario.objects.filter(user=request.user).first()

    if not perfil or perfil.sala_atual != combate.sala:
        return JsonResponse({'error': 'forbidden'}, status=403)

    # Permissão: GM ou controlador do domain
    unit = get_object_or_404(Unit, pk=unit_id, domain__participacoes_warfare__combate=combate)
    is_gm = combate.sala.game_master_id == request.user.id
    controla = (
        is_gm
        or unit.domain.criador_id == request.user.id
        or unit.domain.jogadores_acesso.filter(id=request.user.id).exists()
    )
    if not controla:
        return JsonResponse({'error': 'forbidden'}, status=403)

    status, _ = StatusUnitWarfare.objects.get_or_create(
        combate=combate,
        unit=unit,
        defaults={
            'hp_maximo': _get_hp_from_size(unit.size),
            'hp_atual': _get_hp_from_size(unit.size),
        }
    )

    try:
        data = json.loads(request.body or '{}') if request.body else {}
    except Exception:
        data = {}

    action = data.get('action') or ''
    delta = int(data.get('delta', 1) or 1)

    if action == 'reset':
        status.hp_atual = status.hp_maximo
        status.diminished = False
        status.incapacitado = False
        status.save(update_fields=['hp_atual', 'diminished', 'incapacitado', 'atualizado_em'])
    elif action == 'dano':
        delta = abs(delta)
        status.aplicar_dano(delta)
    elif action == 'curar':
        delta = abs(delta)
        status.curar(delta)
    else:
        return JsonResponse({'error': 'invalid_action'}, status=400)

    status_data = {
        'unit_id': unit.id,
        'hp_atual': status.hp_atual,
        'hp_max': status.hp_maximo,
        'diminished': status.diminished,
        'incapacitado': status.incapacitado,
    }

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'warfare_{combate.id}',
            {
                'type': 'combate_message',
                'message': json.dumps({
                    'evento': 'status_update',
                    'status': status_data,
                })
            }
        )
    except Exception:
        pass

    return JsonResponse({'status': 'ok', 'unit_status': status_data})

