#!/usr/bin/env python
"""
Smoke test para testar todas as combinações de Tipo/Modo de poder.
Testa:
- Tipos: dano, aflicao, cura, buff, aprimorar, descritivo
- Modos: area, percepcao, melee, ranged
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
sys.path.insert(0, str(Path(__file__).parent.parent))
django.setup()

from combate.models import Combate, Participante, Turno, Poder
from personagens.models import Personagem
from salas.models import Sala
from django.contrib.auth.models import User
from combate.views import realizar_ataque
from django.test import RequestFactory
from unittest.mock import patch
import traceback

# Cores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(status, message):
    if status == "PASS":
        print(f"{GREEN}[PASS]{RESET}: {message}")
    elif status == "FAIL":
        print(f"{RED}[FAIL]{RESET}: {message}")
    elif status == "SKIP":
        print(f"{YELLOW}[SKIP]{RESET}: {message}")
    else:
        print(f"{BLUE}[INFO]{RESET}: {message}")

def create_test_scenario():
    """Cria um cenário isolado de combate para um teste"""
    # Limpa dados antigos
    Combate.objects.all().delete()
    User.objects.filter(username__startswith="test_user_").delete()

    user = User.objects.create_user(
        username='test_user_ataque',
        email='test@example.com',
        password='testpass'
    )

    sala = Sala.objects.create(
        nome="TEST_Sala",
        criador=user,
        game_master=user,
        ativa=True
    )

    atacante = Personagem.objects.create(
        nome="Atacante",
        usuario=user,
        sala=sala,
        forca=10,
        destreza=10,
        vigor=10,
        inteligencia=10,
        prontidao=10,
        presenca=10,
        aparar=10,
        esquivar=10,
        resistencia=10,
        fortitude=10,
        vontade=10
    )

    alvo = Personagem.objects.create(
        nome="Alvo",
        usuario=user,
        sala=sala,
        forca=10,
        destreza=10,
        vigor=10,
        inteligencia=10,
        prontidao=10,
        presenca=10,
        aparar=10,
        esquivar=10,
        resistencia=10,
        fortitude=10,
        vontade=10
    )

    combate = Combate.objects.create(sala=sala)

    part_atacante = Participante.objects.create(combate=combate, personagem=atacante, iniciativa=20)
    part_alvo = Participante.objects.create(combate=combate, personagem=alvo, iniciativa=15)

    turno = Turno.objects.create(combate=combate, personagem=atacante, ordem=1, ativo=True)

    return combate, part_atacante, part_alvo

def create_power(personagem, tipo, modo, duracao='instantaneo', nome_base="TestePoder"):
    nome = f"{nome_base}_{tipo}_{modo}_{duracao}"
    Poder.objects.filter(nome=nome, personagem=personagem).delete()
    return Poder.objects.create(
        nome=nome,
        personagem=personagem,
        tipo=tipo,
        modo=modo,
        duracao=duracao,
        nivel_efeito=2,
        defesa_passiva='resistencia',
        casting_ability='inteligencia'
    )

def run_attack_scenario(title, tipo, modo, duracao, rolls, alvo_obrigatorio=True):
    """Executa a view realizar_ataque com dados mínimos e rolagens controladas."""
    try:
        combate, part_atacante, part_alvo = create_test_scenario()
        poder = create_power(part_atacante.personagem, tipo, modo, duracao)

        data = {
            'personagem_acao': str(part_atacante.id),
            'poder_id': str(poder.id),
        }
        if alvo_obrigatorio:
            data['alvo_id'] = [str(part_alvo.id)]

        factory = RequestFactory()
        request = factory.post(
            f'/combate/combate/{combate.id}/atacar/',
            data,
            content_type='application/x-www-form-urlencoded'
        )
        request.user = part_atacante.personagem.usuario

        side_effect = list(rolls) + [10] * 10  # evita StopIteration se a view rolar mais vezes
        with patch('random.randint', side_effect=side_effect):
            response = realizar_ataque(request, combate.id)

        if getattr(response, 'status_code', None) in (200, 302):
            print_test("PASS", title)
            return True
        print_test("FAIL", f"{title} - status {getattr(response, 'status_code', None)}")
        return False
    except Exception as e:
        print_test("FAIL", f"{title} - erro: {str(e)[:120]}")
        traceback.print_exc()
        return False

def main():
    print(f"\n{BLUE}=== SMOKE TEST: Combinações completas ==={RESET}\n")

    scenarios = [
        # Dano
        ("DANO melee hit+falha defesa (instant)", 'dano', 'melee', 'instantaneo', [20, 1], True),
        ("DANO melee erra", 'dano', 'melee', 'instantaneo', [1], True),
        ("DANO ranged hit+falha defesa", 'dano', 'ranged', 'instantaneo', [20, 1], True),
        ("DANO ranged erra", 'dano', 'ranged', 'instantaneo', [1], True),
        ("DANO area falha esquiva/defesa (sustentado)", 'dano', 'area', 'sustentado', [5, 5], True),

        # Aflição
        ("AFLICAO percepcao falha defesa (conc)", 'aflicao', 'percepcao', 'concentracao', [5], True),
        ("AFLICAO melee hit+falha defesa", 'aflicao', 'melee', 'instantaneo', [20, 1], True),

        # Buff/Cura/Aprimorar
        ("BUFF area", 'buff', 'area', 'sustentado', [10], True),
        ("CURA area", 'cura', 'area', 'instantaneo', [20], True),
        ("APRIMORAR melee hit+falha defesa (conc)", 'aprimorar', 'melee', 'concentracao', [20, 1], True),

        # Descritivo (sem alvo)
        ("DESCRITIVO area", 'descritivo', 'area', 'instantaneo', [10], False),
    ]

    resultados = {'pass': 0, 'fail': 0}

    for title, tipo, modo, duracao, rolls, precisa_alvo in scenarios:
        ok = run_attack_scenario(title, tipo, modo, duracao, rolls, alvo_obrigatorio=precisa_alvo)
        resultados['pass' if ok else 'fail'] += 1

    print(f"\n{BLUE}=== RESUMO ==={RESET}")
    print(f"{GREEN}PASS: {resultados['pass']}{RESET}")
    print(f"{RED}FAIL: {resultados['fail']}{RESET}")

    Combate.objects.all().delete()
    User.objects.filter(username__startswith="test_user_").delete()

    if resultados['fail'] == 0:
        print(f"{GREEN}Todos os testes passaram!{RESET}\n")
    else:
        print(f"{RED}{resultados['fail']} teste(s) falharam{RESET}\n")

if __name__ == "__main__":
    main()
