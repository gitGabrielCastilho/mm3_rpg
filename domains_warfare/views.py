from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import Domain, Unit, UnitAncestry, UnitType, UnitSize, UnitExperience, UnitEquipment, UnitTrait
from .forms import DomainForm, UnitForm
from salas.models import Sala


@login_required
def domain_list(request):
    """Lista TODOS os domínios disponíveis na sala do usuário."""
    try:
        from personagens.models import PerfilUsuario
        
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or not perfil.sala_atual:
            messages.error(request, "Você precisa estar em uma sala para acessar domínios.")
            return redirect('listar_salas')
        
        # Todos os domínios da sala do usuário
        domains = Domain.objects.filter(sala=perfil.sala_atual).order_by('nome')
        
        # Preparar contexto com permissões para cada domain
        domains_with_perms = []
        for domain in domains:
            domains_with_perms.append({
                'domain': domain,
                'pode_editar': domain.pode_editar(request.user),
                'pode_deletar': domain.pode_deletar(request.user),
            })
        
        context = {
            'domains': domains_with_perms,
        }
        return render(request, 'domains_warfare/domain_list.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao carregar domínios: {str(e)}")
        return redirect('listar_salas')


@login_required
def domain_detail(request, pk):
    """Exibe detalhes de um domínio específico."""
    try:
        domain = get_object_or_404(Domain, pk=pk)
        
        # Verificar se o usuário está na mesma sala
        from personagens.models import PerfilUsuario
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or perfil.sala_atual != domain.sala:
            messages.error(request, "Você não tem acesso a este domínio.")
            return redirect('domain_list')
        
        context = {
            'domain': domain,
            'pode_editar': domain.pode_editar(request.user),
            'pode_deletar': domain.pode_deletar(request.user),
        }
        return render(request, 'domains_warfare/domain_detail.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao carregar domínio: {str(e)}")
        return redirect('domain_list')


@login_required
def domain_create(request):
    """Cria um novo domínio."""
    try:
        from personagens.models import PerfilUsuario
        
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or not perfil.sala_atual:
            messages.error(request, "Você precisa estar em uma sala para criar um domínio.")
            return redirect('listar_salas')
        
        if request.method == 'POST':
            form = DomainForm(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                domain = form.save(commit=False)
                domain.criador = request.user
                domain.sala = perfil.sala_atual  # Define a sala automaticamente
                # Define se foi criado por GM
                domain.criado_por_gm = (
                    request.user.is_staff or 
                    request.user.is_superuser or 
                    perfil.sala_atual.game_master == request.user
                )
                domain.save()
                form.save_m2m()  # Salva relações many-to-many
                messages.success(request, f"Domínio '{domain.nome}' criado com sucesso!")
                return redirect('domain_detail', pk=domain.pk)
        else:
            form = DomainForm(user=request.user)
        
        context = {
            'form': form,
            'action': 'Criar',
        }
        return render(request, 'domains_warfare/domain_form.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao criar domínio: {str(e)}")
        return redirect('domain_list')


@login_required
def domain_edit(request, pk):
    """Edita um domínio existente."""
    try:
        domain = get_object_or_404(Domain, pk=pk)
        
        if not domain.pode_editar(request.user):
            messages.error(request, "Você não tem permissão para editar este domínio.")
            return redirect('domain_detail', pk=pk)
        
        if request.method == 'POST':
            form = DomainForm(request.POST, request.FILES, instance=domain, user=request.user)
            if form.is_valid():
                domain = form.save()
                messages.success(request, f"Domínio '{domain.nome}' atualizado com sucesso!")
                return redirect('domain_detail', pk=domain.pk)
        else:
            form = DomainForm(instance=domain, user=request.user)
        
        context = {
            'form': form,
            'domain': domain,
            'action': 'Editar',
        }
        return render(request, 'domains_warfare/domain_form.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao editar domínio: {str(e)}")
        return redirect('domain_list')


@login_required
def domain_delete(request, pk):
    """Deleta um domínio."""
    try:
        domain = get_object_or_404(Domain, pk=pk)
        
        # Apenas criador ou GM podem deletar
        if not domain.pode_deletar(request.user):
            messages.error(request, "Você não tem permissão para deletar este domínio.")
            return redirect('domain_detail', pk=pk)
        
        if request.method == 'POST':
            nome = domain.nome
            domain.delete()
            messages.success(request, f"Domínio '{nome}' deletado com sucesso!")
            return redirect('domain_list')
        
        context = {
            'domain': domain,
        }
        return render(request, 'domains_warfare/domain_confirm_delete.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao deletar domínio: {str(e)}")
        return redirect('domain_list')


# ============================================================================
# UNIT VIEWS
# ============================================================================

@login_required
def unit_list(request, domain_pk):
    """Lista todas as unidades de um domínio."""
    try:
        domain = get_object_or_404(Domain, pk=domain_pk)
        
        # Verificar acesso ao domínio
        from personagens.models import PerfilUsuario
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or perfil.sala_atual != domain.sala:
            messages.error(request, "Você não tem acesso a este domínio.")
            return redirect('domain_list')
        
        # Listar unidades do domínio
        units = Unit.objects.filter(domain=domain).select_related('ancestry', 'criador').order_by('-criado_em')
        
        # Preparar contexto com permissões
        units_with_perms = []
        for unit in units:
            units_with_perms.append({
                'unit': unit,
                'pode_editar': unit.pode_editar(request.user),
                'pode_deletar': unit.pode_deletar(request.user),
            })
        
        context = {
            'domain': domain,
            'units': units_with_perms,
            'pode_criar': domain.pode_editar(request.user),
        }
        return render(request, 'domains_warfare/unit_list.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao carregar unidades: {str(e)}")
        return redirect('domain_list')


@login_required
def unit_detail(request, domain_pk, pk):
    """Exibe detalhes de uma unidade."""
    try:
        domain = get_object_or_404(Domain, pk=domain_pk)
        unit = get_object_or_404(Unit, pk=pk, domain=domain)
        
        # Verificar acesso
        from personagens.models import PerfilUsuario
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or perfil.sala_atual != domain.sala:
            messages.error(request, "Você não tem acesso a esta unidade.")
            return redirect('domain_list')
        
        # Calcular atributos finais com modificadores
        atributos_finais = unit.get_atributos_finais()
        
        context = {
            'domain': domain,
            'unit': unit,
            'atributos_finais': atributos_finais,
            'pode_editar': unit.pode_editar(request.user),
            'pode_deletar': unit.pode_deletar(request.user),
        }
        return render(request, 'domains_warfare/unit_detail.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao carregar unidade: {str(e)}")
        return redirect('domain_list')


@login_required
def unit_create(request, domain_pk):
    """Cria uma nova unidade em um domínio."""
    try:
        domain = get_object_or_404(Domain, pk=domain_pk)
        
        # Verificar se pode editar o domínio
        if not domain.pode_editar(request.user):
            messages.error(request, "Você não tem permissão para adicionar unidades a este domínio.")
            return redirect('unit_list', domain_pk=domain_pk)
        
        if request.method == 'POST':
            form = UnitForm(request.POST, domain=domain)
            if form.is_valid():
                unit = form.save(commit=False)
                unit.domain = domain
                unit.criador = request.user
                unit.save()
                messages.success(request, f"Unidade '{unit.nome}' criada com sucesso!")
                return redirect('unit_detail', domain_pk=domain_pk, pk=unit.pk)
        else:
            form = UnitForm(domain=domain)
        
        context = {
            'domain': domain,
            'form': form,
            'action': 'Criar',
        }
        return render(request, 'domains_warfare/unit_form.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao criar unidade: {str(e)}")
        return redirect('unit_list', domain_pk=domain_pk)


@login_required
def unit_list_all(request):
    """Lista todas as unidades dos domínios acessíveis ao usuário."""
    try:
        from personagens.models import PerfilUsuario
        
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        if not perfil or not perfil.sala_atual:
            messages.error(request, "Você precisa estar em uma sala para acessar unidades.")
            return redirect('listar_salas')
        
        # Buscar todos os domínios da sala do usuário
        domains = Domain.objects.filter(sala=perfil.sala_atual).order_by('nome')
        
        # Buscar todas as unidades desses domínios
        units = Unit.objects.filter(domain__in=domains).select_related(
            'domain', 'ancestry', 'unit_type', 'size', 'experience', 'equipment', 'criador'
        ).order_by('domain__nome', 'nome')
        
        # Agrupar unidades por domínio
        units_by_domain = {}
        for unit in units:
            if unit.domain.nome not in units_by_domain:
                units_by_domain[unit.domain.nome] = {
                    'domain': unit.domain,
                    'units': [],
                    'pode_adicionar': unit.domain.pode_editar(request.user)
                }
            units_by_domain[unit.domain.nome]['units'].append({
                'unit': unit,
                'pode_editar': unit.pode_editar(request.user),
                'pode_deletar': unit.pode_deletar(request.user),
                'custos': unit.get_custos_finais(),
            })
        
        context = {
            'units_by_domain': units_by_domain,
            'total_units': units.count(),
        }
        return render(request, 'domains_warfare/unit_list_all.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao carregar unidades: {str(e)}")
        return redirect('domain_list')


@login_required
def unit_edit(request, domain_pk, pk):
    """Edita uma unidade existente."""
    try:
        domain = get_object_or_404(Domain, pk=domain_pk)
        unit = get_object_or_404(Unit, pk=pk, domain=domain)
        
        # Verificar permissão
        if not unit.pode_editar(request.user):
            messages.error(request, "Você não tem permissão para editar esta unidade.")
            return redirect('unit_detail', domain_pk=domain_pk, pk=pk)
        
        if request.method == 'POST':
            form = UnitForm(request.POST, instance=unit, domain=domain)
            if form.is_valid():
                unit = form.save()
                messages.success(request, f"Unidade '{unit.nome}' atualizada com sucesso!")
                return redirect('unit_detail', domain_pk=domain_pk, pk=unit.pk)
        else:
            form = UnitForm(instance=unit, domain=domain)
        
        context = {
            'domain': domain,
            'unit': unit,
            'form': form,
            'action': 'Editar',
        }
        return render(request, 'domains_warfare/unit_form.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao editar unidade: {str(e)}")
        return redirect('unit_list', domain_pk=domain_pk)


@login_required
def unit_delete(request, domain_pk, pk):
    """Deleta uma unidade."""
    try:
        domain = get_object_or_404(Domain, pk=domain_pk)
        unit = get_object_or_404(Unit, pk=pk, domain=domain)
        
        # Apenas criador ou GM podem deletar
        if not unit.pode_deletar(request.user):
            messages.error(request, "Você não tem permissão para deletar esta unidade.")
            return redirect('unit_detail', domain_pk=domain_pk, pk=pk)
        
        if request.method == 'POST':
            nome = unit.nome
            unit.delete()
            messages.success(request, f"Unidade '{nome}' deletada com sucesso!")
            return redirect('unit_list', domain_pk=domain_pk)
        
        context = {
            'domain': domain,
            'unit': unit,
        }
        return render(request, 'domains_warfare/unit_confirm_delete.html', context)
    except Exception as e:
        messages.error(request, f"Erro ao deletar unidade: {str(e)}")
        return redirect('unit_list', domain_pk=domain_pk)


@login_required
def calculate_unit_cost(request):
    """
    Endpoint AJAX para calcular o custo de uma unidade em tempo real.
    Retorna o custo total e o upkeep baseado nos atributos fornecidos.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    try:
        # Extrair parâmetros da query string
        ancestry_id = request.GET.get('ancestry')
        unit_type_id = request.GET.get('unit_type')
        size_id = request.GET.get('size')
        experience_id = request.GET.get('experience')
        equipment_id = request.GET.get('equipment')
        trait_ids = request.GET.getlist('traits')
        
        # Atributos base
        ataque = int(request.GET.get('ataque', 1))
        poder = int(request.GET.get('poder', 1))
        defesa = int(request.GET.get('defesa', 1))
        resistencia = int(request.GET.get('resistencia', 1))
        moral = int(request.GET.get('moral', 1))
        
        # Calcular modificadores de cada componente
        mods = {
            'ataque': 0,
            'poder': 0,
            'defesa': 0,
            'resistencia': 0,
            'moral': 0,
        }
        
        # Modificadores de ancestry
        if ancestry_id:
            try:
                ancestry = UnitAncestry.objects.get(id=ancestry_id)
                ancestry_mods = ancestry.get_modificadores()
                for key, value in ancestry_mods.items():
                    mods[key] += value
            except UnitAncestry.DoesNotExist:
                pass
        
        # Modificadores de experience
        if experience_id:
            try:
                experience = UnitExperience.objects.get(id=experience_id)
                experience_mods = experience.get_modificadores()
                for key, value in experience_mods.items():
                    mods[key] += value
            except UnitExperience.DoesNotExist:
                pass
        
        # Modificadores de equipment
        if equipment_id:
            try:
                equipment = UnitEquipment.objects.get(id=equipment_id)
                equipment_mods = equipment.get_modificadores()
                for key, value in equipment_mods.items():
                    mods[key] += value
            except UnitEquipment.DoesNotExist:
                pass
        
        # Modificadores de unit type
        type_multiplier = 1.0
        if unit_type_id:
            try:
                unit_type = UnitType.objects.get(id=unit_type_id)
                type_mods = unit_type.get_modificadores()
                for key, value in type_mods.items():
                    mods[key] += value
                type_multiplier = float(unit_type.multiplicador_custo)
            except UnitType.DoesNotExist:
                pass
        
        # Size multiplier
        size_multiplier = 1.0
        if size_id:
            try:
                size = UnitSize.objects.get(id=size_id)
                size_multiplier = float(size.multiplicador_custo)
            except UnitSize.DoesNotExist:
                pass
        
        # Calcular atributos finais
        final_ataque = max(1, ataque + mods['ataque'])
        final_poder = max(1, poder + mods['poder'])
        final_defesa = max(1, defesa + mods['defesa'])
        final_resistencia = max(1, resistencia + mods['resistencia'])
        final_moral = moral + mods['moral']
        
        # Calcular bônus (diferença do base 1)
        bonus_ataque = max(0, final_ataque - 1)
        bonus_poder = max(0, final_poder - 1)
        bonus_defesa = max(0, final_defesa - 1)
        bonus_resistencia = max(0, final_resistencia - 1)
        bonus_moral = max(0, final_moral - 1)
        
        # Somar bônus (morale conta dobrado)
        total_bonus = (bonus_ataque + bonus_poder + bonus_defesa + 
                      bonus_resistencia + (2 * bonus_moral))
        
        # Aplicar multiplicadores
        custo_base = total_bonus * type_multiplier * size_multiplier * 10
        
        # Adicionar custo dos traits
        trait_cost = 0
        if trait_ids:
            traits = UnitTrait.objects.filter(id__in=trait_ids)
            trait_cost = sum(trait.custo for trait in traits)
        
        # Custo total
        custo_total = int(custo_base) + trait_cost + 30
        upkeep = int(custo_total * 0.1)
        
        return JsonResponse({
            'success': True,
            'custo_ouro': custo_total,
            'upkeep': upkeep,
            'final_attributes': {
                'ataque': final_ataque,
                'poder': final_poder,
                'defesa': final_defesa,
                'resistencia': final_resistencia,
                'moral': final_moral,
            },
            'modifiers': mods,
        })
        
    except ValueError as e:
        return JsonResponse({'error': f'Valor inválido: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erro ao calcular custo: {str(e)}'}, status=500)
