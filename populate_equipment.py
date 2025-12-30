#!/usr/bin/env python
"""Direct population of equipment"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
django.setup()

from domains_warfare.models import UnitEquipment

data = [
    ('light', 'Equipamento leve que melhora a mobilidade.', 1, 1),
    ('medium', 'Equipamento padrão que oferece boa proteção.', 2, 2),
    ('heavy', 'Equipamento pesado que fornece proteção significativa.', 4, 4),
    ('super_heavy', 'Equipamento super pesado oferecendo proteção máxima.', 6, 6),
]

for nome, desc, pow, def_ in data:
    obj, created = UnitEquipment.objects.get_or_create(
        nome=nome,
        defaults={
            'descricao': desc,
            'modificador_poder': pow,
            'modificador_defesa': def_,
        }
    )
    action = "Created" if created else "Updated"
    print(f"{action}: {nome} (POD+{pow}, DEF+{def_})")

print(f'\nTotal: {UnitEquipment.objects.count()} equipment types')
