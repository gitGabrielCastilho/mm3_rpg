from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
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
