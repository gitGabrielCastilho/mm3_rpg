from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Domain
from .forms import DomainForm
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
                    perfil.sala_atual.mestre == request.user
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

