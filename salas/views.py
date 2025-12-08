from django.http import HttpResponse, JsonResponse
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
from django.views.decorators.http import require_POST
from .models import Sala, NotaSessao
from django.db.models import Q
from django import forms
from personagens.models import PerfilUsuario
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
import logging

logger = logging.getLogger(__name__)


class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ['nome', 'senha']
        widgets = {
            'senha': forms.PasswordInput(render_value=False, attrs={'placeholder': 'Opcional'})
        }

    def save(self, commit=True):
        sala = super().save(commit=False)
        senha = self.cleaned_data.get('senha')
        # Hash only if provided and not already hashed
        if senha:
            try:
                # If it's not a recognized hasher string, make a new hash
                if '$' not in senha:
                    sala.senha = make_password(senha)
                else:
                    # Likely already encoded (defensive, in case of reuse)
                    sala.senha = senha
            except Exception:
                sala.senha = make_password(senha)
        if commit:
            sala.save()
        return sala

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
            perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user, defaults={'tipo': 'jogador'})
            perfil.sala_atual = sala
            perfil.tipo = 'game_master'
            perfil.save()
            return redirect('listar_salas')
    else:
        form = SalaForm()
    return render(request, 'salas/criar_sala.html', {'form': form})

def listar_salas(request):
    query = request.GET.get('q', '').strip()
    salas = Sala.objects.all()
    if query:
        salas = salas.filter(
            Q(nome__icontains=query) |
            Q(codigo__icontains=query) |
            Q(criador__username__icontains=query)
        )
    sala_atual = None
    if request.user.is_authenticated:
        perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user, defaults={'tipo': 'jogador'})
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
    # Se a sala possui senha e a requisição é GET, exibe o formulário de senha.
    if request.method == 'GET' and sala.senha:
        return render(request, 'salas/entrar_sala.html', { 'sala': sala })

    # Se a sala possui senha, valida a senha enviada via POST.
    if sala.senha:
        if request.method != 'POST':
            return redirect('listar_salas')
        senha_digitada = request.POST.get('senha', '')
        is_valid = False
        try:
            is_valid = check_password(senha_digitada, sala.senha)
        except Exception:
            # Backward compatibility: if stored plain, compare directly
            is_valid = (senha_digitada == sala.senha)
        if not is_valid:
            messages.error(request, 'Senha incorreta para entrar na sala.')
            return render(request, 'salas/entrar_sala.html', { 'sala': sala })
    perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user, defaults={'tipo': 'jogador'})
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
        try:
            logger.info("[Channels] Enviando evento ENTRADA para sala_%s (%s)", sala.id, request.user.username)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'sala_{sala.id}',
                {
                    'type': 'sala_message',
                    'message': {'evento': 'entrada', 'usuario': request.user.username}
                }
            )
        except Exception:
            logger.warning("Falha ao enviar evento 'entrada' via Channels (ignorado)", exc_info=True)
    transaction.on_commit(send_event)
    return redirect('listar_combates', sala_id=sala.id)

@login_required
def sair_sala(request):
    perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user, defaults={'tipo': 'jogador'})
    sala = perfil.sala_atual
    perfil.sala_atual = None
    perfil.tipo = 'jogador'
    perfil.save()
    # Notifica todos os participantes da sala sobre a saída após commit
    if sala:
        def send_event():
            try:
                logger.info("[Channels] Enviando evento SAIDA para sala_%s (%s)", sala.id, request.user.username)
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'sala_{sala.id}',
                    {
                        'type': 'sala_message',
                        'message': {'evento': 'saida', 'usuario': request.user.username}
                    }
                )
            except Exception:
                logger.warning("Falha ao enviar evento 'saida' via Channels (ignorado)", exc_info=True)
        transaction.on_commit(send_event)
    return redirect('listar_salas')


@login_required
def editar_senha_sala(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id, game_master=request.user)
    if request.method == 'POST':
        nova_senha = request.POST.get('senha', '').strip()
        if nova_senha:
            sala.senha = make_password(nova_senha)
            messages.success(request, 'Senha da sala atualizada com sucesso.')
        else:
            sala.senha = ''
            messages.success(request, 'Senha da sala removida (sala sem senha).')
        sala.save()
        return redirect('listar_salas')
    return render(request, 'salas/editar_senha.html', {'sala': sala})


@login_required
def notas_sala(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    # Permissão básica: qualquer participante da sala pode ver/anotar
    if request.user not in sala.participantes.all():
        return redirect('listar_salas')
    notas = sala.notas.select_related('usuario').all()
    return render(request, 'salas/notas_sala.html', {'sala': sala, 'notas': notas})


@login_required
@require_POST
def criar_nota_sala(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    if request.user not in sala.participantes.all():
        return JsonResponse({'ok': False, 'erro': 'Permissão negada.'}, status=403)

    conteudo = request.POST.get('conteudo', '').strip()
    if not conteudo:
        return JsonResponse({'ok': False, 'erro': 'Conteúdo vazio.'}, status=400)

    nota = NotaSessao.objects.create(
        sala=sala,
        usuario=request.user,
        nome_usuario=request.user.get_username(),
        conteudo=conteudo,
    )

    payload = {
        'tipo': 'nota',
        'id': nota.id,
        'sala_id': sala.id,
        'usuario_id': nota.usuario_id,
        'nome_usuario': nota.nome_usuario,
        'conteudo': nota.conteudo,
        'criada_em': nota.criada_em.isoformat(),
    }

    # Broadcast via Channels para o grupo da sala (melhor esforço)
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'sala_{sala.id}',
            {
                'type': 'sala_message',
                'message': payload,
            },
        )
    except Exception:
        logger.warning('Falha ao enviar evento de nota via Channels (ignorado).', exc_info=True)

    return JsonResponse({'ok': True, 'nota': payload})


def _pode_gerenciar_nota(user, nota):
    """Retorna True se o usuário pode editar/apagar a nota.

    Regras:
    - Autor da nota pode editar/apagar.
    - GM da sala pode editar/apagar qualquer nota.
    """
    if user == nota.usuario:
        return True
    sala = nota.sala
    return sala.game_master == user


@login_required
@require_POST
def editar_nota_sala(request, sala_id, nota_id):
    sala = get_object_or_404(Sala, id=sala_id)
    nota = get_object_or_404(NotaSessao, id=nota_id, sala=sala)

    if not _pode_gerenciar_nota(request.user, nota):
        return JsonResponse({'ok': False, 'erro': 'Permissão negada.'}, status=403)

    conteudo = request.POST.get('conteudo', '').strip()
    if not conteudo:
        return JsonResponse({'ok': False, 'erro': 'Conteúdo vazio.'}, status=400)

    nota.conteudo = conteudo
    nota.save(update_fields=['conteudo'])

    payload = {
        'tipo': 'nota_editada',
        'id': nota.id,
        'sala_id': sala.id,
        'usuario_id': nota.usuario_id,
        'nome_usuario': nota.nome_usuario,
        'conteudo': nota.conteudo,
        'criada_em': nota.criada_em.isoformat(),
    }

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'sala_{sala.id}',
            {
                'type': 'sala_message',
                'message': payload,
            },
        )
    except Exception:
        logger.warning('Falha ao enviar evento de nota_editada via Channels (ignorado).', exc_info=True)

    return JsonResponse({'ok': True, 'nota': payload})


@login_required
@require_POST
def deletar_nota_sala(request, sala_id, nota_id):
    sala = get_object_or_404(Sala, id=sala_id)
    nota = get_object_or_404(NotaSessao, id=nota_id, sala=sala)

    if not _pode_gerenciar_nota(request.user, nota):
        return JsonResponse({'ok': False, 'erro': 'Permissão negada.'}, status=403)

    nota_id_local = nota.id
    nota.delete()

    payload = {
        'tipo': 'nota_deletada',
        'id': nota_id_local,
        'sala_id': sala.id,
    }

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'sala_{sala.id}',
            {
                'type': 'sala_message',
                'message': payload,
            },
        )
    except Exception:
        logger.warning('Falha ao enviar evento de nota_deletada via Channels (ignorado).', exc_info=True)

    return JsonResponse({'ok': True, 'id': nota_id_local})


