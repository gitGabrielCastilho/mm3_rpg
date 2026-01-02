from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Combate, Participante

@login_required
def tabela_participantes(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    participantes = (
        Participante.objects.filter(combate=combate)
        .select_related('personagem', 'personagem__usuario')
        .order_by('-iniciativa')
    )

    # Gera nomes exibidos com numeração para participantes duplicados (mesmo personagem)
    counts = {}
    for p in participantes:
        pid = p.personagem_id
        counts[pid] = counts.get(pid, 0) + 1
        if counts[pid] > 1:
            p.display_nome = f"{p.personagem.nome} ({counts[pid]})"
        else:
            p.display_nome = p.personagem.nome
    user = request.user
    return render(request, 'combate/_tabela_participantes.html', {
        'participantes': participantes,
        'combate': combate,
        'user': user,
    })

@login_required
def status_card_json(request, combate_id):
    """
    Retorna apenas o HTML do card de status dos participantes como JSON.
    Usado por AJAX para atualizar status leve sem recarregar toda a página.
    """
    combate = get_object_or_404(Combate, id=combate_id)
    
    # Verificação de permissão
    sala = combate.sala
    if sala.game_master != request.user and request.user not in sala.jogadores.all():
        return JsonResponse({'error': 'forbidden'}, status=403)
    
    participantes = (
        Participante.objects.filter(combate=combate)
        .select_related('personagem', 'personagem__usuario')
        .order_by('-iniciativa')
    )
    
    # Renderiza o template parcial
    html = render(request, 'combate/_tabela_participantes.html', {
        'participantes': participantes,
        'combate': combate,
        'user': request.user,
    }).content.decode('utf-8')
    
    return JsonResponse({'html': html})
