#!/usr/bin/env python
"""Teste rápido do sistema completo de Unit Experience"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
django.setup()

from domains_warfare.models import UnitExperience, UnitAncestry, Unit, Domain
from django.contrib.auth.models import User

print("=" * 60)
print("TESTE SISTEMA DE UNIT EXPERIENCE")
print("=" * 60)

# 1. Verificar que todos os 6 níveis de experiência existem
print("\n1. Verificando níveis de experiência...")
levels = UnitExperience.objects.all()
print(f"   Total de níveis: {levels.count()}")
for level in levels:
    print(f"   - {level.get_nome_display()}: ATQ{level.modificador_ataque} / RES{level.modificador_resistencia} / MOR{level.modificador_moral}")

# 2. Tentar criar uma unit com experiência
print("\n2. Testando criação de unit com experiência...")
try:
    domain = Domain.objects.first()
    if not domain:
        print("   ✗ Nenhum domínio encontrado para teste")
    else:
        ancestry = UnitAncestry.objects.first()
        experience = UnitExperience.objects.filter(nome='regular').first()
        user = User.objects.first()
        
        if not user:
            user = User.objects.create_user(username='test', password='test')
        
        if ancestry and experience:
            unit, created = Unit.objects.get_or_create(
                nome='TestUnit',
                domain=domain,
                defaults={
                    'ancestry': ancestry,
                    'experience': experience,
                    'criador': user,
                    'ataque': 1,
                    'poder': 1,
                    'defesa': 1,
                    'resistencia': 1,
                    'moral': 5,
                }
            )
            
            action = "Criada" if created else "Já existe"
            print(f"   ✓ {action}: {unit.nome}")
            print(f"   - Ancestry: {unit.ancestry.get_nome_display()}")
            print(f"   - Experience: {unit.experience.get_nome_display()}")
            
            # Testes de atributos finais
            final = unit.get_atributos_finais()
            print(f"   - Atributos base: ATQ{unit.ataque} POD{unit.poder} DEF{unit.defesa} RES{unit.resistencia} MOR{unit.moral}")
            print(f"   - Atributos finais: ATQ{final['ataque']} POD{final['poder']} DEF{final['defesa']} RES{final['resistencia']} MOR{final['moral']}")
            
except Exception as e:
    print(f"   ✗ Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TESTE CONCLUÍDO")
print("=" * 60)
