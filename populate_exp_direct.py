#!/usr/bin/env python
"""Direct population without Django shell to avoid timeout issues"""
import sys
import os

# Add the project to the path
sys.path.insert(0, '/d/TI/mm3_rpg')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')

import django
django.setup()

# Now import models
from domains_warfare.models import UnitExperience

# Data to insert
data = [
    ('green', 'Tropas recrutas sem experiência de combate.', 0, 0, 0, 0, 0),
    ('regular', 'Tropas com treinamento básico completo.', 1, 0, 0, 1, 1),
    ('seasoned', 'Tropas que participaram de vários combates.', 1, 0, 0, 1, 2),
    ('veteran', 'Tropas veteranas com muito tempo de experiência.', 1, 0, 0, 1, 3),
    ('elite', 'Tropas de elite com habilidades excepcionais.', 2, 0, 0, 2, 4),
    ('super_elite', 'Tropas lendárias de extraordinário poder e disciplina.', 2, 0, 0, 2, 5),
]

created_count = 0
updated_count = 0

for nome, desc, atk, pow, def_, res, mor in data:
    try:
        obj, created = UnitExperience.objects.get_or_create(
            nome=nome,
            defaults={
                'descricao': desc,
                'modificador_ataque': atk,
                'modificador_poder': pow,
                'modificador_defesa': def_,
                'modificador_resistencia': res,
                'modificador_moral': mor,
            }
        )
        if created:
            created_count += 1
            print(f'✓ Created: {nome}')
        else:
            updated_count += 1
            # Update just in case
            obj.descricao = desc
            obj.modificador_ataque = atk
            obj.modificador_poder = pow
            obj.modificador_defesa = def_
            obj.modificador_resistencia = res
            obj.modificador_moral = mor
            obj.save()
            print(f'⬤ Updated: {nome}')
    except Exception as e:
        print(f'✗ Error for {nome}: {e}')

print(f'\n✓ Complete: {created_count} created, {updated_count} updated')
print(f'✓ Total in database: {UnitExperience.objects.count()}')
