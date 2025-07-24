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
    participantes = Participante.objects.filter(combate=combate).order_by('-iniciativa')
    if not participantes.exists():
        messages.error(request, "Nenhum participante encontrado para iniciar o turno.")
        return redirect('detalhes_combate', combate_id=combate.id)

    primeiro_participante = participantes.first()
    Turno.objects.create(
        combate=combate,
        personagem=primeiro_participante.personagem,
        ordem=0,
        ativo=True
    )
    messages.success(request, f"Turno iniciado para {primeiro_participante.personagem.nome}.")
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



@csrf_exempt
def realizar_ataque(request, combate_id):
    if request.method == 'POST':
        turno_ativo = Turno.objects.filter(combate_id=combate_id, ativo=True).first()
        atacante = turno_ativo.personagem
        alvo_ids = request.POST.getlist('alvo_id')  # Permite múltiplos alvos
        poder_id = request.POST.get('poder_id')
        poder = get_object_or_404(Poder, id=poder_id)
        resultados = []

        for alvo_id in alvo_ids:
            alvo = get_object_or_404(Personagem, id=alvo_id)
            participante_alvo = Participante.objects.get(combate=combate_id, personagem=alvo)
            
            # CURA
            if poder.tipo == 'cura':
                rolagem = random.randint(1, 20) + getattr(atacante, poder.casting_ability)
                cd = 10 - poder.nivel_efeito
                if rolagem >= cd:
                    # Remove o que estiver mais alto, em empate remove dano
                    if participante_alvo.dano >= participante_alvo.aflicao and participante_alvo.dano > 0:
                        participante_alvo.dano -= 1
                        resultado = f"{atacante.nome} curou {alvo.nome} (Rolagem {rolagem} vs CD {cd}): sucesso! Dano reduzido em 1."
                    elif participante_alvo.aflicao > participante_alvo.dano and participante_alvo.aflicao > 0:
                        participante_alvo.aflicao -= 1
                        resultado = f"{atacante.nome} curou {alvo.nome} (Rolagem {rolagem} vs CD {cd}): sucesso! Aflição reduzida em 1."
                    else:
                        resultado = f"{atacante.nome} curou {alvo.nome} (Rolagem {rolagem} vs CD {cd}): sucesso! Nada para curar."
                    participante_alvo.save()
                else:
                    resultado = f"{atacante.nome} tentou curar {alvo.nome} (Rolagem {rolagem} vs CD {cd}): falhou."
                
            # BUFF
            elif poder.tipo == 'buff':
                # Implemente um campo temporário ou lógica para bônus na próxima rolagem
                resultado = f"{alvo.nome} recebe um bônus de +{poder.nivel_efeito} na próxima rolagem."
            # DEBUFF
            elif poder.tipo == 'debuff':
                resultado = f"{alvo.nome} recebe uma penalidade de -{poder.nivel_efeito} na próxima rolagem."
            # ÁREA
            elif poder.modo == 'area':
                esquiva = getattr(alvo, 'esquivar', 0)
                rolagem_esquiva = random.randint(1, 20) + esquiva
                if poder.tipo == 'dano':
                    cd = poder.nivel_efeito + 15
                    cd_sucesso = (15 + poder.nivel_efeito) // 2
                else:  # aflicao
                    cd = poder.nivel_efeito + 10
                    cd_sucesso = (10 + poder.nivel_efeito) // 2
                if rolagem_esquiva < cd:
                    # Falhou, faz teste de defesa_passiva
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    rolagem_defesa = random.randint(1, 20) + defesa_valor
                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = f"{alvo.nome} falhou na esquiva ({rolagem_esquiva} vs {cd}), defesa {poder.defesa_passiva}: {rolagem_defesa} <b>Sofreu 1 de dano!</b>"
                        else:
                            resultado = f"{alvo.nome} falhou na esquiva ({rolagem_esquiva} vs {cd}), defesa {poder.defesa_passiva}: {rolagem_defesa} (sem dano)"
                    else:  # aflicao
                        if rolagem_defesa < cd:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = f"{alvo.nome} falhou na esquiva ({rolagem_esquiva} vs {cd}), defesa {poder.defesa_passiva}: {rolagem_defesa} <b>Sofreu 1 de aflição!</b>"
                        else:
                            resultado = f"{alvo.nome} falhou na esquiva ({rolagem_esquiva} vs {cd}), defesa {poder.defesa_passiva}: {rolagem_defesa} (sem aflição)"
                else:
                    # Sucesso parcial
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    rolagem_defesa = random.randint(1, 20) + defesa_valor
                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd_sucesso:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva} vs {cd}), defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {rolagem_defesa} <b>Sofreu 1 de dano!</b>"
                        else:
                            resultado = f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva} vs {cd}), defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {rolagem_defesa} (sem dano)"
                    else:
                        if rolagem_defesa < cd_sucesso:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva} vs {cd}), defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {rolagem_defesa} <b>Sofreu 1 de aflição!</b>"
                        else:
                            resultado = f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva} vs {cd}), defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {rolagem_defesa} (sem aflição)"
            # PERCEPÇÃO
            elif poder.modo == 'percepcao':
                if poder.tipo == 'dano':
                    cd = poder.nivel_efeito + 15
                else:
                    cd = poder.nivel_efeito + 10
                defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                rolagem_defesa = random.randint(1, 20) + defesa_valor
                if poder.tipo == 'dano':
                    if rolagem_defesa < cd:
                        participante_alvo.dano += 1
                        participante_alvo.save()
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} <b>Sofreu 1 de dano!</b>"
                    else:
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} (sem dano)"
                else:
                    if rolagem_defesa < cd:
                        participante_alvo.aflicao += 1
                        participante_alvo.save()
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} <b>Sofreu 1 de aflição!</b>"
                    else:
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} (sem aflição)"
            # MELEE
            elif poder.modo == 'melee':
                ataque = random.randint(1, 20) + poder.bonus_ataque
                aparar = getattr(alvo, 'aparar', 0)
                if poder.tipo == 'dano':
                    cd = 15 + poder.nivel_efeito
                else:
                    cd = 10 + poder.nivel_efeito
                if ataque > 10 + aparar:
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    rolagem_defesa = random.randint(1, 20) + defesa_valor
                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = f"{atacante.nome} acertou {alvo.nome} (ataque {ataque} vs {10+aparar}), defesa {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} <b>Sofreu 1 de dano!</b>"
                        else:
                            resultado = f"{atacante.nome} acertou {alvo.nome} (ataque {ataque} vs {10+aparar}), defesa {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} (sem dano)"
                    else:
                        if rolagem_defesa < cd:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = f"{atacante.nome} acertou {alvo.nome} (ataque {ataque} vs {10+aparar}), defesa {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} <b>Sofreu 1 de aflição!</b>"
                        else:
                            resultado = f"{atacante.nome} acertou {alvo.nome} (ataque {ataque} vs {10+aparar}), defesa {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} (sem aflição)"
                else:
                    resultado = f"{atacante.nome} errou {alvo.nome} (ataque {ataque} vs {10+aparar})"
            # RANGED
            elif poder.modo == 'ranged':
                ataque = random.randint(1, 20) + poder.bonus_ataque
                esquiva = getattr(alvo, 'esquivar', 0)
                if poder.tipo == 'dano':
                    cd = 15 + poder.nivel_efeito
                else:
                    cd = 10 + poder.nivel_efeito
                if ataque > 10 + esquiva:
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    rolagem_defesa = random.randint(1, 20) + defesa_valor
                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = f"{atacante.nome} acertou {alvo.nome} (ataque {ataque} vs {10+esquiva}), defesa {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} <b>Sofreu 1 de dano!</b>"
                        else:
                            resultado = f"{atacante.nome} acertou {alvo.nome} (ataque {ataque} vs {10+esquiva}), defesa {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} (sem dano)"
                    else:
                        if rolagem_defesa < cd:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = f"{atacante.nome} acertou {alvo.nome} (ataque {ataque} vs {10+esquiva}), defesa {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} <b>Sofreu 1 de aflição!</b>"
                        else:
                            resultado = f"{atacante.nome} acertou {alvo.nome} (ataque {ataque} vs {10+esquiva}), defesa {poder.defesa_passiva} ({rolagem_defesa}) contra CD {cd} (sem aflição)"
                else:
                    resultado = f"{atacante.nome} errou {alvo.nome} (ataque {ataque} vs {10+esquiva})"
            else:
                resultado = "Ação não implementada."

            resultados.append(resultado)

        # Salve o histórico no turno
        nova_descricao = "<br>".join(resultados)
        if turno_ativo.descricao:
            turno_ativo.descricao += "<br>" + nova_descricao
        else:
            turno_ativo.descricao = nova_descricao
        turno_ativo.save()

    return redirect('detalhes_combate', combate_id=combate_id)