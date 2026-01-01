"""
Views para o sistema de Warfare Combat.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from personagens.models import PerfilUsuario
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
        
        # Mapas
        mapas = combate.mapas_warfare.filter(ativo=True)
        mapa_ativo = mapas.first()
        posicoes = []
        if mapa_ativo:
            posicoes = mapa_ativo.posicoes_units.select_related('unit')
        
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
        from .forms import MapaWargameForm
        
        combate = get_object_or_404(CombateWarfare, pk=pk)
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or perfil.sala_atual != combate.sala:
            messages.error(request, "Você não tem acesso a este combate.")
            return redirect('domain_list')
        
        # Apenas GM pode adicionar mapas
        if combate.sala.game_master != request.user:
            messages.error(request, "Apenas o GM pode adicionar mapas.")
            return redirect('warfare_detalhes', pk=pk)
        
        form = MapaWargameForm()
        
        if request.method == 'POST':
            form = MapaWargameForm(request.POST, request.FILES)
            if form.is_valid():
                mapa = form.save(commit=False)
                mapa.combate = combate
                mapa.save()
                
                # Criar posições para todas as unidades
                for status in combate.status_units.all():
                    PosicaoUnitWarfare.objects.get_or_create(
                        mapa=mapa,
                        unit=status.unit,
                        defaults={'x': 50, 'y': 50}
                    )
                
                messages.success(request, f"Mapa '{mapa.nome}' adicionado com sucesso!")
                return redirect('warfare_detalhes', pk=pk)
        
        context = {
            'combate': combate,
            'form': form,
        }
        return render(request, 'combate/adicionar_mapa.html', context)
        
    except Exception as e:
        messages.error(request, f"Erro ao adicionar mapa: {str(e)}")
        return redirect('warfare_detalhes', pk=pk)

