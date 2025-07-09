from django.shortcuts import render
from .forms import AtaqueForm
from personagens.models import Personagem
import random

def usar_poder(request):
    resultado = None
    if request.method == 'POST':
        form = AtaqueForm(request.POST)
        if form.is_valid():
            atacante = form.cleaned_data['atacante']
            alvo = form.cleaned_data['alvo']
            tipo = form.cleaned_data['tipo']
            alcance = form.cleaned_data['alcance']
            nivel = form.cleaned_data['nivel']
            bonus = form.cleaned_data['bonus_ataque']
            defesa = form.cleaned_data['defesa']

            if alcance == "comum":
                rolagem = random.randint(1, 20) + bonus
                defesa_valor = getattr(alvo, defesa.lower())
                acertou = rolagem >= defesa_valor
                resultado = f"{atacante.nome} atacou {alvo.nome} ({rolagem} vs {defesa_valor}) – {'ACERTOU' if acertou else 'ERROU'}"
            else:
                resultado = f"{atacante.nome} usou {tipo} em {alvo.nome} (alcance {alcance})"
    else:
        form = AtaqueForm()

    return render(request, 'combate/usar_poder.html', {'form': form, 'resultado': resultado})