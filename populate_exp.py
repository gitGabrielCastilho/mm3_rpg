#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
django.setup()

from domains_warfare.models import UnitExperience

data = [
    ('green', 0, 0, 0, 0, 0),
    ('regular', 1, 0, 0, 1, 1),
    ('seasoned', 1, 0, 0, 1, 2),
    ('veteran', 1, 0, 0, 1, 3),
    ('elite', 2, 0, 0, 2, 4),
    ('super_elite', 2, 0, 0, 2, 5),
]

for nome, atk, pow, def_, res, mor in data:
    obj, created = UnitExperience.objects.update_or_create(
        nome=nome,
        defaults={
            'modificador_ataque': atk,
            'modificador_poder': pow,
            'modificador_defesa': def_,
            'modificador_resistencia': res,
            'modificador_moral': mor
        }
    )
    action = "Created" if created else "Updated"
    print(f"{action}: {nome}")

print(f'\nTotal: {UnitExperience.objects.count()} experience levels')
