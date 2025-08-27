from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.cache import cache
from .models import Sala

@login_required
def participantes_sidebar(request, sala_id):
    sala = Sala.objects.get(id=sala_id)
    # Presence baseada em cache com TTL (setada pelo consumer via heartbeat)
    online_ids = []
    for u in sala.participantes.all():
        key = f"presence:sala:{sala_id}:user:{u.id}"
        if cache.get(key, 0):
            online_ids.append(u.id)
    # Otimismo: se este cliente está pedindo o sidebar, considere-o online
    if request.user.is_authenticated and request.user in sala.participantes.all():
        if request.user.id not in online_ids:
            online_ids.append(request.user.id)
    return render(
        request,
        'salas/_sidebar_participantes.html',
        {
            'sala': sala,
            'user': request.user,
            'online_ids': online_ids,
        },
    )
