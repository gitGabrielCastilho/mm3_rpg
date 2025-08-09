from django.http import HttpResponse
# View para detalhes da sala
from django.contrib.auth.decorators import login_required
@login_required
def detalhes_sala(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    return render(request, 'salas/detalhes_sala.html', {'sala': sala})
from django.shortcuts import render, redirect, get_object_or_404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import Sala
from django.db.models import Q
from django import forms
from personagens.models import PerfilUsuario

class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ['nome']

@login_required
def criar_sala(request):
    if request.method == 'POST':
        form = SalaForm(request.POST)
        if form.is_valid():
            sala = form.save(commit=False)
            sala.game_master = request.user
            sala.criador = request.user
            sala.save()
            sala.jogadores.add(request.user)
            sala.participantes.add(request.user)
            # Atualiza perfil do usuário
            perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)
            perfil.sala_atual = sala
            perfil.tipo = 'game_master'
            perfil.save()
            return redirect('listar_salas')
    else:
        form = SalaForm()
    return render(request, 'salas/criar_sala.html', {'form': form})

@login_required
def listar_salas(request):
    query = request.GET.get('q', '').strip()
    salas = Sala.objects.all()
    if query:
        salas = salas.filter(
            Q(nome__icontains=query) |
            Q(codigo__icontains=query) |
            Q(criador__username__icontains=query)
        )
    perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)
    sala_atual = getattr(perfil, 'sala_atual', None)
    return render(request, 'salas/listar_salas.html', {'salas': salas, 'sala_atual': sala_atual, 'query': query})

@login_required
def excluir_sala(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id, game_master=request.user)
    if request.method == 'POST':
        sala.delete()
        return redirect('listar_salas')
    return render(request, 'salas/excluir_sala.html', {'sala': sala})

@login_required
def entrar_sala(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)
    # Se já está em outra sala, remove
    if perfil.sala_atual and perfil.sala_atual != sala:
        # Opcional: pode remover o usuário da lista de participantes da sala antiga, se necessário
        pass
    perfil.sala_atual = sala
    if sala.game_master == request.user:
        perfil.tipo = 'game_master'
    else:
        perfil.tipo = 'jogador'
    perfil.save()
    sala.participantes.add(request.user)
    sala.jogadores.add(request.user)
    # Notifica todos os participantes da sala sobre a entrada após commit
    def send_event():
        print(f"[Channels] Enviando evento ENTRADA para sala_{sala.id} ({request.user.username})")
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'sala_{sala.id}',
            {
                'type': 'sala_message',
                'message': {'evento': 'entrada', 'usuario': request.user.username}
            }
        )
    transaction.on_commit(send_event)
    return redirect('listar_combates', sala_id=sala.id)

@login_required
def sair_sala(request):
    perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)
    sala = perfil.sala_atual
    perfil.sala_atual = None
    perfil.tipo = 'jogador'
    perfil.save()
    # Notifica todos os participantes da sala sobre a saída após commit
    if sala:
        def send_event():
            print(f"[Channels] Enviando evento SAIDA para sala_{sala.id} ({request.user.username})")
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'sala_{sala.id}',
                {
                    'type': 'sala_message',
                    'message': {'evento': 'saida', 'usuario': request.user.username}
                }
            )
        transaction.on_commit(send_event)
    return redirect('listar_salas')


