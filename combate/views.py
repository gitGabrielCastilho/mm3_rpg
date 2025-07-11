from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Combate, Turno, Participante
from personagens.models import Personagem, Poder
from django.utils import timezone
import random
from django.views.decorators.http import require_POST
from django.contrib import messages

def criar_combate(request):
    if request.method == 'POST':
        personagem_ids = request.POST.getlist('personagens')
        personagens = Personagem.objects.filter(id__in=personagem_ids)

        combate = Combate.objects.create(ativo=True)

        ordem = []
        for personagem in personagens:
            iniciativa = random.randint(1, 20) + personagem.prontidao
            p = Participante.objects.create(personagem=personagem, combate=combate, iniciativa=iniciativa)
            ordem.append((p, iniciativa))

        ordem.sort(key=lambda x: x[1], reverse=True)

        for idx, (participante, _) in enumerate(ordem):
            Turno.objects.create(
                combate=combate,
                personagem=participante.personagem,
                ordem=idx,
                ativo=(idx == 0)
            )

        return redirect('detalhes_combate', combate_id=combate.id)

    personagens = Personagem.objects.all()
    return render(request, 'combate/criar_combate.html', {'personagens': personagens})


def detalhes_combate(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    participantes = Participante.objects.filter(combate=combate).order_by('-iniciativa')
    turnos = Turno.objects.filter(combate=combate).order_by('criado_em')  # ou por ordem
    turno_ativo = turnos.filter(ativo=True).first()

    poderes_disponiveis = Poder.objects.filter(personagem=turno_ativo.personagem) if turno_ativo else []

    defesas_disponiveis = ["vontade", "fortitude", "resistencia", "aparar", "esquivar"]
    context = {
        'combate': combate,
        'participantes': participantes,
        'turnos': turnos,
        'turno_ativo': turno_ativo,
        'poderes_disponiveis': poderes_disponiveis,  # <-- Corrija aqui!
        'defesas': defesas_disponiveis,
    }

    return render(request, 'combate/detalhes_combate.html', context)


from django.views.decorators.http import require_POST

@require_POST
def passar_turno(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    turnos = Turno.objects.filter(combate=combate).order_by('ordem')

    ativo = turnos.filter(ativo=True).first()

    if ativo:
        ativo.ativo = False
        ativo.save()

        proximo = turnos.filter(ordem__gt=ativo.ordem).first()
        if not proximo:
            proximo = turnos.first()

        proximo.ativo = True
        proximo.save()

    return redirect('detalhes_combate', combate_id=combate.id)

def listar_combates(request):
    combates = Combate.objects.all().order_by('-criado_em')
    return render(request, 'combate/listar_combates.html', {'combates': combates})

@require_POST
def iniciar_turno(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)

    ordem = Turno.objects.filter(combate=combate).count() + 1
    turno = Turno.objects.create(combate=combate, ordem=ordem, ativo=True)
    messages.success(request, f"Turno {ordem} iniciado.")
    return redirect('detalhes_combate', combate_id=combate.id)


@require_POST
def avancar_turno(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    turnos = Turno.objects.filter(combate=combate).order_by('ordem')
    turno_ativo = turnos.filter(ativo=True).first()

    if turno_ativo:
        turno_ativo.ativo = False
        turno_ativo.save()

        participantes = Participante.objects.filter(combate=combate).order_by('-iniciativa')
        participante_ids = list(participantes.values_list('id', flat=True))
        personagem_ids = list(participantes.values_list('personagem_id', flat=True))

        if turno_ativo.personagem_id in personagem_ids:
            idx = personagem_ids.index(turno_ativo.personagem_id)
            proximo_idx = (idx + 1) % len(personagem_ids)
        else:
            proximo_idx = 0  

        personagem_proximo = participantes[proximo_idx].personagem

        Turno.objects.create(
            combate=combate,
            personagem=personagem_proximo,
            ordem=turno_ativo.ordem + 1,
            ativo=True
        )
    return redirect('detalhes_combate', combate_id=combate.id)


@require_POST
def finalizar_combate(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    combate.ativo = False
    combate.save()

    Turno.objects.filter(combate=combate, ativo=True).update(ativo=False)
    messages.success(request, "Combate finalizado.")
    return redirect('listar_combates')



@login_required
def deletar_combate(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    combate.delete()
    return redirect('listar_combates')

@csrf_exempt  # remova essa linha em produção!
def realizar_ataque(request, combate_id):
    if request.method == 'POST':
        atacante = Turno.objects.filter(combate_id=combate_id, ativo=True).first().personagem
        alvo_id = request.POST.get('alvo_id')
        poder_id = request.POST.get('poder_id')
        defesa_escolhida = request.POST.get('defesa')

        alvo = get_object_or_404(Personagem, id=alvo_id)
        poder = get_object_or_404(Poder, id=poder_id)

        defesa_valor = getattr(alvo, defesa_escolhida.lower(), 10)
        rolagem = random.randint(1, 20) + poder.bonus_ataque
        acertou = rolagem >= defesa_valor

        Turno.objects.create(
            combate_id=combate_id,
            personagem=atacante,
            ordem=Turno.objects.filter(combate_id=combate_id).count(),
            ativo=False,
            descricao=f"{atacante.nome} usou {poder.nome} em {alvo.nome} ({rolagem} vs {defesa_valor}) – {'ACERTOU' if acertou else 'ERROU'}",
            criado_em=timezone.now()
        )

    return redirect('detalhes_combate', combate_id=combate_id)

@csrf_exempt  # se der erro de CSRF, pode remover se csrf_token estiver no template
def realizar_ataque(request, combate_id):
    if request.method == 'POST':
        atacante = Turno.objects.filter(combate_id=combate_id, ativo=True).first().personagem
        alvo_id = request.POST.get('alvo_id')
        poder_id = request.POST.get('poder_id')

        alvo = get_object_or_404(Personagem, id=alvo_id)
        poder = get_object_or_404(Poder, id=poder_id)

        defesa_escolhida = request.POST.get('defesa')
        defesa_valor = getattr(alvo, defesa_escolhida.lower(), 10)
        rolagem = random.randint(1, 20) + poder.bonus_ataque
        acertou = rolagem >= defesa_valor

        Turno.objects.create(
            combate_id=combate_id,
            personagem=atacante,
            ordem=Turno.objects.filter(combate_id=combate_id).count(),
            ativo=False,
            descricao=f"{atacante.nome} usou {poder.nome} em {alvo.nome} ({rolagem} vs {defesa_valor}) – {'ACERTOU' if acertou else 'ERROU'}",
            criado_em=timezone.now()
        )

    return redirect('detalhes_combate', combate_id=combate_id)