#!/usr/bin/env python
"""Script para popular as fortificações padrão usando Django ORM."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
django.setup()

from domains_warfare.models_warfare import Fortificacao

FORTIFICACOES_DATA = [
    {
        'nome': 'cerca_pedra',
        'moral': 1,
        'defesa': 2,
        'poder': 0,
        'hp_fortificacao': 4,
        'descricao': 'Uma cerca simples de pedra. Fornece proteção básica.'
    },
    {
        'nome': 'torre_guarda',
        'moral': 1,
        'defesa': 2,
        'poder': 2,
        'hp_fortificacao': 6,
        'descricao': 'Uma torre de guarda elevada que oferece ponto de vista estratégico e suporte de archeiros.'
    },
    {
        'nome': 'muros_cidade',
        'moral': 2,
        'defesa': 2,
        'poder': 2,
        'hp_fortificacao': 8,
        'descricao': 'Os muros fortificados de uma cidade. Oferece proteção significativa ao exército defendedor.'
    },
    {
        'nome': 'portoes_cidade',
        'moral': 2,
        'defesa': 2,
        'poder': 2,
        'hp_fortificacao': 8,
        'descricao': 'Os portões principais de uma cidade. Excelente ponto defensivo com suporte de múltiplos níveis.'
    },
    {
        'nome': 'torreao_keep',
        'moral': 3,
        'defesa': 2,
        'poder': 2,
        'hp_fortificacao': 10,
        'descricao': 'Um grande torreão tipo Keep. Uma fortificação muito poderosa que oferece defesa superior.'
    },
    {
        'nome': 'castelo',
        'moral': 4,
        'defesa': 2,
        'poder': 2,
        'hp_fortificacao': 12,
        'descricao': 'Um castelo completo com múltiplas torres e defesas. A fortificação mais poderosa possível.'
    },
]

created_count = 0
print("\n" + "="*70)
print("POPULANDO FORTIFICAÇÕES")
print("="*70 + "\n")

for fort_data in FORTIFICACOES_DATA:
    fort, created = Fortificacao.objects.get_or_create(
        nome=fort_data['nome'],
        defaults={
            'moral': fort_data['moral'],
            'defesa': fort_data['defesa'],
            'poder': fort_data['poder'],
            'hp_fortificacao': fort_data['hp_fortificacao'],
            'descricao': fort_data['descricao'],
        }
    )
    
    if created:
        created_count += 1
        print(f'✓ Criada: {fort.get_nome_display()}')
        print(f'  - Moral: +{fort.moral}, Defesa: +{fort.defesa}, Poder: +{fort.poder}, HP: {fort.hp_fortificacao}')
        print()
    else:
        print(f'→ Já existe: {fort.get_nome_display()}')
        print()

print("="*70)
print(f'✓ População concluída! {created_count} nova(s) fortificação(ões) criada(s).')
print("="*70 + "\n")
