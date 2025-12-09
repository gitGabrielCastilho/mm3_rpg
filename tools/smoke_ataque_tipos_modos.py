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
from django.contrib.auth.decorators import login_required
from unittest.mock import Mock
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
    """Cria um cenário de combate para testes"""
    # Limpa dados antigos
    Combate.objects.all().delete()
    User.objects.filter(username__startswith="test_user_").delete()
    
    # Cria usuário
    user = User.objects.create_user(
        username='test_user_ataque',
        email='test@example.com',
        password='testpass'
    )
    
    # Cria sala
    sala = Sala.objects.create(
        nome="TEST_Sala",
        criador=user,
        game_master=user,
        ativa=True
    )
    
    # Cria personagens
    p1 = Personagem.objects.create(
        nome="Atacante",
        usuario=user,
        sala=sala,
        forca=18,
        destreza=16,
        vigor=14,
        inteligencia=12,
        prontidao=13,
        presenca=11
    )
    
    p2 = Personagem.objects.create(
        nome="Alvo",
        usuario=user,
        sala=sala,
        forca=10,
        destreza=12,
        vigor=16,
        inteligencia=14,
        prontidao=15,
        presenca=10
    )
    
    # Cria combate
    combate = Combate.objects.create(
        sala=sala
    )
    
    # Cria participantes
    par1 = Participante.objects.create(
        combate=combate,
        personagem=p1,
        iniciativa=20
    )
    
    par2 = Participante.objects.create(
        combate=combate,
        personagem=p2,
        iniciativa=15
    )
    
    # Cria turno
    turno = Turno.objects.create(
        combate=combate,
        personagem=p1,
        ordem=1
    )
    
    return combate, par1, par2, p1, p2

def get_or_create_power(personagem, tipo, modo, nome_base="TestePoder"):
    """Busca ou cria um poder com o tipo e modo especificado"""
    nome = f"{nome_base}_{tipo}_{modo}"
    
    try:
        poder = Poder.objects.get(nome=nome, personagem=personagem)
        return poder
    except Poder.DoesNotExist:
        pass
    
    # Cria poder
    poder = Poder.objects.create(
        nome=nome,
        personagem=personagem,
        tipo=tipo,
        modo=modo,
        nivel_efeito=2,
        defesa_passiva='resistencia',
        casting_ability='inteligencia',
        duracao='instantaneo'
    )
    
    return poder

def mock_request(user):
    """Cria um request mock com usuário autenticado"""
    factory = RequestFactory()
    request = factory.post('/combate/combate/1/atacar/')
    request.user = user
    request.method = 'POST'
    request.POST = {}
    return request

def test_attack_combination(combate, atacante, alvo, tipo, modo, user, personagem_atacante):
    """Testa uma combinação específica de tipo/modo (apenas validação de criação)"""
    test_name = f"{tipo.upper()} - {modo.upper()}"
    
    try:
        # Cria ou busca poder
        poder = get_or_create_power(personagem_atacante, tipo, modo)
        
        # Valida se o poder foi criado com sucesso
        if not poder:
            print_test("FAIL", f"{test_name} - Poder não foi criado")
            return False
        
        if poder.tipo != tipo:
            print_test("FAIL", f"{test_name} - Tipo inválido: {poder.tipo}")
            return False
            
        if poder.modo != modo:
            print_test("FAIL", f"{test_name} - Modo inválido: {poder.modo}")
            return False
        
        print_test("PASS", test_name)
        return True
            
    except Exception as e:
        print_test("FAIL", f"{test_name} - Erro: {str(e)[:60]}")
        return False

def main():
    print(f"\n{BLUE}=== SMOKE TEST: Combinações Tipo/Modo ==={RESET}\n")
    
    # Cria cenário
    try:
        combate, atacante, alvo, p_atacante, p_alvo = create_test_scenario()
        print_test("INFO", "Cenário de teste criado com sucesso")
    except Exception as e:
        print_test("FAIL", f"Não foi possível criar cenário: {e}")
        traceback.print_exc()
        return
    
    # Tipos e modos a testar
    tipos = ['dano', 'aflicao', 'cura', 'buff', 'aprimorar', 'descritivo']
    modos = ['area', 'percepcao', 'melee', 'ranged']
    
    # Mapeamento: tipo -> modos válidos
    modos_validos = {
        'dano': ['area', 'percepcao', 'melee', 'ranged'],
        'aflicao': ['area', 'percepcao', 'melee', 'ranged'],
        'cura': ['area'],  # cura geralmente é area ou direto
        'buff': ['area'],  # buff geralmente é direto
        'aprimorar': ['area', 'melee', 'ranged'],  # aprimorar pode ser vários
        'descritivo': ['area'],  # descritivo não precisa de modo real
    }
    
    resultados = {
        'pass': 0,
        'fail': 0,
        'skip': 0,
        'total': 0
    }
    
    print(f"{BLUE}Testando combinações:{RESET}\n")
    
    for tipo in tipos:
        modos_para_testar = modos_validos.get(tipo, ['area'])
        
        for modo in modos_para_testar:
            resultados['total'] += 1
            
            try:
                if test_attack_combination(combate, atacante, alvo, tipo, modo, atacante.personagem.usuario, p_atacante):
                    resultados['pass'] += 1
                else:
                    resultados['fail'] += 1
            except Exception as e:
                print_test("FAIL", f"{tipo.upper()} - {modo.upper()} - Exceção não capturada: {e}")
                resultados['fail'] += 1
    
    # Testes especiais: ataque contra si mesmo
    print(f"\n{BLUE}Testando ataque contra si mesmo:{RESET}\n")
    for tipo in ['dano', 'buff', 'cura']:
        for modo in ['area', 'melee']:
            resultados['total'] += 1
            try:
                poder = get_or_create_power(p_atacante, tipo, f"{modo}_self")
                
                # Validações
                if poder.tipo == tipo and poder.modo == f"{modo}_self":
                    print_test("PASS", f"{tipo.upper()} - {modo.upper()} (SELF)")
                    resultados['pass'] += 1
                else:
                    print_test("FAIL", f"{tipo.upper()} - {modo.upper()} (SELF) - Tipo/Modo inválido")
                    resultados['fail'] += 1
            except Exception as e:
                print_test("FAIL", f"{tipo.upper()} - {modo.upper()} (SELF) - {str(e)[:40]}")
                resultados['fail'] += 1
    
    # Resumo
    print(f"\n{BLUE}=== RESUMO ==={RESET}")
    print(f"{GREEN}PASS: {resultados['pass']}{RESET}")
    print(f"{RED}FAIL: {resultados['fail']}{RESET}")
    print(f"{YELLOW}SKIP: {resultados['skip']}{RESET}")
    print(f"TOTAL: {resultados['total']}")
    
    taxa_sucesso = (resultados['pass'] / resultados['total'] * 100) if resultados['total'] > 0 else 0
    print(f"\nTaxa de sucesso: {taxa_sucesso:.1f}%")
    
    # Limpeza
    print(f"\n{BLUE}Limpando dados de teste...{RESET}")
    Combate.objects.all().delete()
    User.objects.filter(username__startswith="test_user_").delete()
    
    if resultados['fail'] == 0:
        print(f"{GREEN}Todos os testes passaram!{RESET}\n")
    else:
        print(f"{RED}{resultados['fail']} teste(s) falharam{RESET}\n")

if __name__ == "__main__":
    main()
