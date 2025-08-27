from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.cache import cache
from .models import Sala

@login_required
def participantes_sidebar(request, sala_id):
    sala = Sala.objects.get(id=sala_id)
    # Monta conjunto de usuários conectados via cache de presença
    conectados = set()
    for participante in sala.participantes.all():
        key = f"presence:sala:{sala_id}:user:{participante.id}"
        if (cache.get(key) or 0) > 0:
            conectados.add(participante.id)
    # Inclui GM na checagem caso não esteja na relação participantes
    if sala.game_master_id:
        gm_key = f"presence:sala:{sala_id}:user:{sala.game_master_id}"
        if (cache.get(gm_key) or 0) > 0:
            conectados.add(sala.game_master_id)
    return render(request, 'salas/_sidebar_participantes.html', {
        'sala': sala,
        'user': request.user,
        'conectados': conectados,
    })
