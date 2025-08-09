from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from .models import Combate

@login_required
def tabela_participantes(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    participantes = combate.participantes.select_related('personagem', 'personagem__usuario').all()
    user = request.user
    return render(request, 'combate/_tabela_participantes.html', {
        'participantes': participantes,
        'combate': combate,
        'user': user,
    })
