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

    pericias = [
        'acrobacias', 'atletismo', 'combate_distancia', 'combate_corpo', 'enganacao',
        'especialidade', 'furtividade', 'intimidacao', 'intuicao', 'investigacao',
        'percepcao', 'persuasao', 'prestidigitacao', 'tecnologia', 'tratamento',
        'veiculos', 'historia', 'sobrevivencia'
    ]
    caracteristicas = [
        'forca', 'vigor', 'destreza', 'agilidade', 'luta', 'inteligencia', 'prontidao', 'presenca'
    ]

    personagens_no_combate_ids = participantes.values_list('personagem_id', flat=True)
    personagens_disponiveis = Personagem.objects.filter(usuario=request.user).exclude(id__in=personagens_no_combate_ids)
    
    context = {
        'combate': combate,
        'participantes': participantes,
        'turnos': turnos,
        'turno_ativo': turno_ativo,
        'poderes_disponiveis': poderes_disponiveis,  # <-- Corrija aqui!
        'defesas': defesas_disponiveis,
        'personagens_disponiveis': personagens_disponiveis,
        'pericias': pericias,
        'caracteristicas': caracteristicas,
    }

    return render(request, 'combate/detalhes_combate.html', context)


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


@require_POST
@login_required
def adicionar_participante(request, combate_id):
    combate = get_object_or_404(Combate, id=combate_id)
    personagem_id = request.POST.get('personagem_id')
    personagem = get_object_or_404(Personagem, id=personagem_id, usuario=request.user)
    iniciativa = random.randint(1, 20) + personagem.prontidao
    Participante.objects.create(personagem=personagem, combate=combate, iniciativa=iniciativa)
    return redirect('detalhes_combate', combate_id=combate_id)


@require_POST
def remover_participante(request, combate_id, participante_id):
    participante = get_object_or_404(Participante, id=participante_id, combate_id=combate_id)
    participante.delete()
    return redirect('detalhes_combate', combate_id=combate_id)

@csrf_exempt
def realizar_ataque(request, combate_id):
    if request.method == 'POST':
        turno_ativo = Turno.objects.filter(combate_id=combate_id, ativo=True).first()
        atacante = turno_ativo.personagem
        resultados = []

        PERICIA_CARACTERISTICA = {
            'acrobacias': 'agilidade',
            'atletismo': 'forca',
            'combate_distancia': 'destreza',
            'combate_corpo': 'luta',
            'enganacao': 'presenca',
            'especialidade': 'casting_ability',  
            'furtividade': 'agilidade',
            'intimidacao': 'presenca',
            'intuicao': 'prontidao',
            'investigacao': 'inteligencia',
            'percepcao': 'prontidao',
            'persuasao': 'presenca',
            'prestidigitacao': 'destreza',
            'tecnologia': 'inteligencia',
            'tratamento': 'inteligencia',
            'veiculos': 'destreza',
            'historia': 'inteligencia',
            'sobrevivencia': 'prontidao',
        }

        if request.POST.get('rolar_pericia'):
            pericia_escolhida = request.POST.get('pericia')
            if pericia_escolhida:
                participante_atacante = Participante.objects.get(combate=combate_id, personagem=atacante)
                valor_pericia = getattr(atacante, pericia_escolhida, None)
                buff = participante_atacante.bonus_temporario
                debuff = participante_atacante.penalidade_temporaria

                # Descobre a característica base
                caracteristica_base = PERICIA_CARACTERISTICA.get(pericia_escolhida)
                if pericia_escolhida == 'especialidade':
                    valor_caracteristica = getattr(atacante, atacante.especialidade_casting_ability, 0)
                else:
                    valor_caracteristica = getattr(atacante, caracteristica_base, 0)


                if valor_pericia is not None:
                    rolagem_base = random.randint(1, 20)
                    total = rolagem_base + valor_pericia + valor_caracteristica + buff - debuff
                    resultados.append(
                        f"{atacante.nome} rolou {pericia_escolhida.capitalize()}: {rolagem_base} + {valor_pericia} (perícia) + {valor_caracteristica} ({caracteristica_base.replace('_', ' ').capitalize()})"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f" = <b>{total}</b>"
                    )
                    participante_atacante.bonus_temporario = 0
                    participante_atacante.penalidade_temporaria = 0
                    participante_atacante.save()
                else:
                    resultados.append(f"{atacante.nome} não possui a perícia {pericia_escolhida}.")
            else:
                resultados.append("Nenhuma perícia selecionada.")

            nova_descricao = "<br>".join(resultados)
            if turno_ativo.descricao:
                turno_ativo.descricao += "<br>" + nova_descricao
            else:
                turno_ativo.descricao = nova_descricao
            turno_ativo.save()
            return redirect('detalhes_combate', combate_id=combate_id)

        if request.POST.get('rolar_caracteristica'):
            caracteristica_escolhida = request.POST.get('caracteristica')
            if caracteristica_escolhida:
                participante_atacante = Participante.objects.get(combate=combate_id, personagem=atacante)
                valor_caracteristica = getattr(atacante, caracteristica_escolhida, None)
                buff = participante_atacante.bonus_temporario
                debuff = participante_atacante.penalidade_temporaria
                if valor_caracteristica is not None:
                    rolagem_base = random.randint(1, 20)
                    total = rolagem_base + valor_caracteristica + buff - debuff
                    resultados.append(
                        f"{atacante.nome} rolou {caracteristica_escolhida.capitalize()}: {rolagem_base} + {valor_caracteristica}"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f" = <b>{total}</b>"
                    )
                    participante_atacante.bonus_temporario = 0
                    participante_atacante.penalidade_temporaria = 0
                    participante_atacante.save()
                else:
                    resultados.append(f"{atacante.nome} não possui a característica {caracteristica_escolhida}.")
            else:
                resultados.append("Nenhuma característica selecionada.")

            nova_descricao = "<br>".join(resultados)
            if turno_ativo.descricao:
                turno_ativo.descricao += "<br>" + nova_descricao
            else:
                turno_ativo.descricao = nova_descricao
            turno_ativo.save()
            return redirect('detalhes_combate', combate_id=combate_id)
        
        if request.POST.get('rolar_d20'):
            rolagem_base = random.randint(1, 20)
            resultados.append(f"{atacante.nome} rolou um d20: <b>{rolagem_base}</b>")
            nova_descricao = "<br>".join(resultados)
            if turno_ativo.descricao:
                turno_ativo.descricao += "<br>" + nova_descricao
            else:
                turno_ativo.descricao = nova_descricao
            turno_ativo.save()
            return redirect('detalhes_combate', combate_id=combate_id)

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
                participante_alvo.bonus_temporario += poder.nivel_efeito
                participante_alvo.save()
                resultado = f"{alvo.nome} recebe um bônus de +{poder.nivel_efeito} na próxima rolagem."

            # DEBUFF
            elif poder.tipo == 'debuff':
                participante_alvo.penalidade_temporaria += poder.nivel_efeito
                participante_alvo.save()
                resultado = f"{alvo.nome} recebe uma penalidade de -{poder.nivel_efeito} na próxima rolagem."

            # ÁREA
            elif poder.modo == 'area':
                esquiva = getattr(alvo, 'esquivar', 0)
                rolagem_esquiva_base = random.randint(1, 20)
                rolagem_esquiva = rolagem_esquiva_base + esquiva
                if poder.tipo == 'dano':
                    cd = poder.nivel_efeito + 15
                    cd_sucesso = (15 + poder.nivel_efeito) // 2
                else:
                    cd = poder.nivel_efeito + 10
                    cd_sucesso = (10 + poder.nivel_efeito) // 2
                if rolagem_esquiva < cd:
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    buff = participante_alvo.bonus_temporario
                    debuff = participante_alvo.penalidade_temporaria
                    rolagem_defesa_base = random.randint(1, 20)
                    rolagem_defesa = rolagem_defesa_base + defesa_valor + buff - debuff
                    participante_alvo.bonus_temporario = 0
                    participante_alvo.penalidade_temporaria = 0
                    participante_alvo.save()

                    defesa_msg = (
                        f"{rolagem_defesa_base} + {defesa_valor}"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f" = {rolagem_defesa}"
                    )

                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = (
                                f"{alvo.nome} falhou na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva}: {defesa_msg} <b>Sofreu 1 de dano!</b>"
                            )
                        else:
                            resultado = (
                                f"{alvo.nome} falhou na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva}: {defesa_msg} (sem dano)"
                            )
                    else:
                        if rolagem_defesa < cd:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = (
                                f"{alvo.nome} falhou na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva}: {defesa_msg} <b>Sofreu 1 de aflição!</b>"
                            )
                        else:
                            resultado = (
                                f"{alvo.nome} falhou na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva}: {defesa_msg} (sem aflição)"
                            )
                else:
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    buff = participante_alvo.bonus_temporario
                    debuff = participante_alvo.penalidade_temporaria
                    rolagem_defesa_base = random.randint(1, 20)
                    rolagem_defesa = rolagem_defesa_base + defesa_valor + buff - debuff
                    participante_alvo.bonus_temporario = 0
                    participante_alvo.penalidade_temporaria = 0
                    participante_alvo.save()

                    defesa_msg = (
                        f"{rolagem_defesa_base} + {defesa_valor}"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f" = {rolagem_defesa}"
                    )

                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd_sucesso:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = (
                                f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {defesa_msg} <b>Sofreu 1 de dano!</b>"
                            )
                        else:
                            resultado = (
                                f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {defesa_msg} (sem dano)"
                            )
                    else:
                        if rolagem_defesa < cd_sucesso:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = (
                                f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {defesa_msg} <b>Sofreu 1 de aflição!</b>"
                            )
                        else:
                            resultado = (
                                f"{alvo.nome} teve sucesso parcial na esquiva ({rolagem_esquiva_base} + {esquiva} = {rolagem_esquiva} vs {cd}), "
                                f"defesa {poder.defesa_passiva} contra CD {cd_sucesso}: {defesa_msg} (sem aflição)"
                            )

            # PERCEPÇÃO
            elif poder.modo == 'percepcao':
                if poder.tipo == 'dano':
                    cd = poder.nivel_efeito + 15
                else:
                    cd = poder.nivel_efeito + 10
                defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                buff = participante_alvo.bonus_temporario
                debuff = participante_alvo.penalidade_temporaria
                rolagem_defesa_base = random.randint(1, 20)
                rolagem_defesa = rolagem_defesa_base + defesa_valor + buff - debuff
                participante_alvo.bonus_temporario = 0
                participante_alvo.penalidade_temporaria = 0
                participante_alvo.save()

                defesa_msg = (
                    f"{rolagem_defesa_base} + {defesa_valor}"
                    f"{' + ' + str(buff) if buff else ''}"
                    f"{' - ' + str(debuff) if debuff else ''}"
                    f" = {rolagem_defesa}"
                )

                if poder.tipo == 'dano':
                    if rolagem_defesa < cd:
                        participante_alvo.dano += 1
                        participante_alvo.save()
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de dano!</b>"
                    else:
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem dano)"
                else:
                    if rolagem_defesa < cd:
                        participante_alvo.aflicao += 1
                        participante_alvo.save()
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de aflição!</b>"
                    else:
                        resultado = f"{alvo.nome} faz teste de {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem aflição)"

            # MELEE
            elif poder.modo == 'melee':
                participante_atacante = Participante.objects.get(combate=combate_id, personagem=atacante)
                buff_atacante = participante_atacante.bonus_temporario
                debuff_atacante = participante_atacante.penalidade_temporaria
                ataque_base = random.randint(1, 20)
                ataque = ataque_base + poder.bonus_ataque + buff_atacante - debuff_atacante
                aparar = getattr(alvo, 'aparar', 0)
                participante_atacante.bonus_temporario = 0
                participante_atacante.penalidade_temporaria = 0
                participante_atacante.save()
                if poder.tipo == 'dano':
                    cd = 15 + poder.nivel_efeito
                else:
                    cd = 10 + poder.nivel_efeito
                if ataque > 10 + aparar:
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    buff = participante_alvo.bonus_temporario
                    debuff = participante_alvo.penalidade_temporaria
                    rolagem_defesa_base = random.randint(1, 20)
                    rolagem_defesa = rolagem_defesa_base + defesa_valor + buff - debuff
                    participante_alvo.bonus_temporario = 0
                    participante_alvo.penalidade_temporaria = 0
                    participante_alvo.save()

                    defesa_msg = (
                        f"{rolagem_defesa_base} + {defesa_valor}"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f" = {rolagem_defesa}"
                    )

                    ataque_msg = (
                        f"{ataque_base} + {poder.bonus_ataque}"
                        f"{' + ' + str(buff_atacante) if buff_atacante else ''}"
                        f"{' - ' + str(debuff_atacante) if debuff_atacante else ''}"
                        f" = {ataque}"
                    )

                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+aparar}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de dano!</b>"
                            )
                        else:
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+aparar}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem dano)"
                            )
                    else:
                        if rolagem_defesa < cd:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+aparar}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de aflição!</b>"
                            )
                        else:
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+aparar}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem aflição)"
                            )
                else:
                    ataque_msg = (
                        f"{ataque_base} + {poder.bonus_ataque}"
                        f"{' + ' + str(buff_atacante) if buff_atacante else ''}"
                        f"{' - ' + str(debuff_atacante) if debuff_atacante else ''}"
                        f" = {ataque}"
                    )
                    resultado = f"{atacante.nome} errou {alvo.nome} (ataque {ataque_msg} vs {10+aparar})"

            # RANGED
            elif poder.modo == 'ranged':
                participante_atacante = Participante.objects.get(combate=combate_id, personagem=atacante)
                buff_atacante = participante_atacante.bonus_temporario
                debuff_atacante = participante_atacante.penalidade_temporaria
                ataque_base = random.randint(1, 20)
                ataque = ataque_base + poder.bonus_ataque + buff_atacante - debuff_atacante
                esquiva = getattr(alvo, 'esquivar', 0)
                participante_atacante.bonus_temporario = 0
                participante_atacante.penalidade_temporaria = 0
                participante_atacante.save()
                if poder.tipo == 'dano':
                    cd = 15 + poder.nivel_efeito
                else:
                    cd = 10 + poder.nivel_efeito
                if ataque > 10 + esquiva:
                    defesa_valor = getattr(alvo, poder.defesa_passiva, 0)
                    buff = participante_alvo.bonus_temporario
                    debuff = participante_alvo.penalidade_temporaria
                    rolagem_defesa_base = random.randint(1, 20)
                    rolagem_defesa = rolagem_defesa_base + defesa_valor + buff - debuff
                    participante_alvo.bonus_temporario = 0
                    participante_alvo.penalidade_temporaria = 0
                    participante_alvo.save()

                    defesa_msg = (
                        f"{rolagem_defesa_base} + {defesa_valor}"
                        f"{' + ' + str(buff) if buff else ''}"
                        f"{' - ' + str(debuff) if debuff else ''}"
                        f" = {rolagem_defesa}"
                    )

                    ataque_msg = (
                        f"{ataque_base} + {poder.bonus_ataque}"
                        f"{' + ' + str(buff_atacante) if buff_atacante else ''}"
                        f"{' - ' + str(debuff_atacante) if debuff_atacante else ''}"
                        f" = {ataque}"
                    )

                    if poder.tipo == 'dano':
                        if rolagem_defesa < cd:
                            participante_alvo.dano += 1
                            participante_alvo.save()
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+esquiva}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de dano!</b>"
                            )
                        else:
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+esquiva}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem dano)"
                            )
                    else:
                        if rolagem_defesa < cd:
                            participante_alvo.aflicao += 1
                            participante_alvo.save()
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+esquiva}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} <b>Sofreu 1 de aflição!</b>"
                            )
                        else:
                            resultado = (
                                f"{atacante.nome} acertou {alvo.nome} (ataque {ataque_msg} vs {10+esquiva}), "
                                f"defesa {poder.defesa_passiva} ({defesa_msg}) contra CD {cd} (sem aflição)"
                            )
                else:
                    ataque_msg = (
                        f"{ataque_base} + {poder.bonus_ataque}"
                        f"{' + ' + str(buff_atacante) if buff_atacante else ''}"
                        f"{' - ' + str(debuff_atacante) if debuff_atacante else ''}"
                        f" = {ataque}"
                    )
                    resultado = f"{atacante.nome} errou {alvo.nome} (ataque {ataque_msg} vs {10+esquiva})"

            resultados.append(resultado)

        # Salve o histórico no turno
        nova_descricao = "<br>".join(resultados)
        if turno_ativo.descricao:
            turno_ativo.descricao += "<br>" + nova_descricao
        else:
            turno_ativo.descricao = nova_descricao
        turno_ativo.save()

    return redirect('detalhes_combate', combate_id=combate_id)