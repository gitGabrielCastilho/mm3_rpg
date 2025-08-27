from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Sala

@login_required
def participantes_sidebar(request, sala_id):
    sala = Sala.objects.get(id=sala_id)
    return render(request, 'salas/_sidebar_participantes.html', {'sala': sala, 'user': request.user})
