from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Sala
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
            sala.save()
            sala.jogadores.add(request.user)  # Opcional: adiciona o GM como jogador também
            return redirect('listar_salas')
    else:
        form = SalaForm()
    return render(request, 'salas/criar_sala.html', {'form': form})

@login_required
def listar_salas(request):
    salas = Sala.objects.filter(game_master=request.user)
    return render(request, 'salas/listar_salas.html', {'salas': salas})

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
    # Cria perfil se não existir
    perfil, created = PerfilUsuario.objects.get_or_create(user=request.user)
    perfil.sala_atual = sala
    # Atualiza tipo: GM se for criador, jogador se não for
    if sala.game_master == request.user:
        perfil.tipo = 'game_master'
    else:
        perfil.tipo = 'jogador'
    perfil.save()
    return redirect('listar_combates', sala_id=sala.id)

@login_required
def sair_sala(request):
    perfil, created = PerfilUsuario.objects.get_or_create(user=request.user)
    perfil.sala_atual = None
    perfil.tipo = 'jogador'
    perfil.save()
    return redirect('listar_salas')