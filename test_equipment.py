#!/usr/bin/env python
"""Test equipment system"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
sys.path.insert(0, '/d/TI/mm3_rpg')
django.setup()

from domains_warfare.models import UnitEquipment, UnitAncestry, Unit, Domain
from django.contrib.auth.models import User

print("=" * 60)
print("TESTE SISTEMA DE UNIT EQUIPMENT")
print("=" * 60)

# 1. Verificar equipamentos
print("\n1. Verificando tipos de equipamento...")
equipments = UnitEquipment.objects.all()
print(f"   Total de tipos: {equipments.count()}")
for eq in equipments:
    print(f"   - {eq.get_nome_display()}: POD+{eq.modificador_poder}, DEF+{eq.modificador_defesa}")

# 2. Testes de modificadores
print("\n2. Testando modificadores...")
for eq in equipments:
    mods = eq.get_modificadores()
    print(f"   - {eq.get_nome_display()}: {mods}")

# 3. Criar test unit com equipamento
print("\n3. Testando unit com equipamento...")
try:
    domain = Domain.objects.first()
    user = User.objects.first()
    ancestry = UnitAncestry.objects.first()
    
    if domain and user and ancestry:
        equipment = UnitEquipment.objects.filter(nome='heavy').first()
        
        if equipment:
            unit, created = Unit.objects.get_or_create(
                nome='HeavyUnit',
                domain=domain,
                defaults={
                    'ancestry': ancestry,
                    'equipment': equipment,
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
            print(f"   - Equipment: {unit.equipment.get_nome_display()}")
            
            final = unit.get_atributos_finais()
            print(f"   - Atributos base: POD{unit.poder} DEF{unit.defesa}")
            print(f"   - Equipment mods: +{equipment.modificador_poder} Poder, +{equipment.modificador_defesa} Defesa")
            print(f"   - Atributos finais: POD{final['poder']} DEF{final['defesa']}")
            
            expected_poder = unit.poder + equipment.modificador_poder
            expected_defesa = unit.defesa + equipment.modificador_defesa
            
            if final['poder'] == expected_poder and final['defesa'] == expected_defesa:
                print(f"   ✓ CORRETO!")
            else:
                print(f"   ✗ Esperado: POD{expected_poder} DEF{expected_defesa}")
        else:
            print("   ✗ Heavy equipment não encontrado")
    else:
        print("   ✗ Faltam dados (domain, user, ancestry)")
        
except Exception as e:
    print(f"   ✗ Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TESTE CONCLUÍDO")
print("=" * 60)
