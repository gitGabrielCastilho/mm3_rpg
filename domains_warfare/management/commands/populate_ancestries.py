from django.core.management.base import BaseCommand
from domains_warfare.models import UnitAncestry


class Command(BaseCommand):
    help = 'Popula a tabela UnitAncestry com todas as ancestries e seus modificadores'

    def handle(self, *args, **options):
        ancestries_data = [
            {
                'nome': 'bugbear',
                'modificador_ataque': 2,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 0,
                'modificador_moral': 1,
                'traits': 'Martial'
            },
            {
                'nome': 'dragonborn',
                'modificador_ataque': 2,
                'modificador_poder': 2,
                'modificador_defesa': 1,
                'modificador_resistencia': 1,
                'modificador_moral': 1,
                'traits': 'Courageous'
            },
            {
                'nome': 'dwarf',
                'modificador_ataque': 3,
                'modificador_poder': 1,
                'modificador_defesa': 1,
                'modificador_resistencia': 1,
                'modificador_moral': 2,
                'traits': ''
            },
            {
                'nome': 'elf',
                'modificador_ataque': 2,
                'modificador_poder': 0,
                'modificador_defesa': 1,
                'modificador_resistencia': 1,
                'modificador_moral': 0,
                'traits': ''
            },
            {
                'nome': 'elf_winged',
                'modificador_ataque': 1,
                'modificador_poder': 1,
                'modificador_defesa': 0,
                'modificador_resistencia': 0,
                'modificador_moral': 1,
                'traits': ''
            },
            {
                'nome': 'ghoul',
                'modificador_ataque': -1,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 1,
                'modificador_moral': 0,
                'traits': 'Eternal'
            },
            {
                'nome': 'gnoll',
                'modificador_ataque': 2,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 0,
                'modificador_moral': 0,
                'traits': 'Brutal'
            },
            {
                'nome': 'gnome',
                'modificador_ataque': 1,
                'modificador_poder': -1,
                'modificador_defesa': 1,
                'modificador_resistencia': 0,
                'modificador_moral': 0,
                'traits': ''
            },
            {
                'nome': 'goblin',
                'modificador_ataque': -1,
                'modificador_poder': -1,
                'modificador_defesa': 0,
                'modificador_resistencia': 0,
                'modificador_moral': 0,
                'traits': 'Savage'
            },
            {
                'nome': 'hobgoblin',
                'modificador_ataque': 2,
                'modificador_poder': 0,
                'modificador_defesa': 1,
                'modificador_resistencia': 0,
                'modificador_moral': 1,
                'traits': 'Martial'
            },
            {
                'nome': 'human',
                'modificador_ataque': 2,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 0,
                'modificador_moral': 0,
                'traits': ''
            },
            {
                'nome': 'kobold',
                'modificador_ataque': -1,
                'modificador_poder': -1,
                'modificador_defesa': 0,
                'modificador_resistencia': 0,
                'modificador_moral': 0,
                'traits': ''
            },
            {
                'nome': 'lizardfolk',
                'modificador_ataque': 2,
                'modificador_poder': 1,
                'modificador_defesa': 0,
                'modificador_resistencia': 1,
                'modificador_moral': 0,
                'traits': ''
            },
            {
                'nome': 'ogre',
                'modificador_ataque': 0,
                'modificador_poder': 2,
                'modificador_defesa': 0,
                'modificador_resistencia': 0,
                'modificador_moral': 0,
                'traits': 'Brutal'
            },
            {
                'nome': 'orc',
                'modificador_ataque': 2,
                'modificador_poder': 1,
                'modificador_defesa': 0,
                'modificador_resistencia': 0,
                'modificador_moral': 0,
                'traits': 'Frenzy'
            },
            {
                'nome': 'skeleton',
                'modificador_ataque': -2,
                'modificador_poder': -1,
                'modificador_defesa': 0,
                'modificador_resistencia': 2,
                'modificador_moral': 0,
                'traits': 'Mindless'
            },
            {
                'nome': 'treant',
                'modificador_ataque': 0,
                'modificador_poder': 2,
                'modificador_defesa': 1,
                'modificador_resistencia': 1,
                'modificador_moral': 0,
                'traits': ''
            },
            {
                'nome': 'troll',
                'modificador_ataque': 0,
                'modificador_poder': 2,
                'modificador_defesa': 0,
                'modificador_resistencia': 1,
                'modificador_moral': 0,
                'traits': 'Regenerate'
            },
            {
                'nome': 'zombie',
                'modificador_ataque': -2,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 0,
                'modificador_moral': 0,
                'traits': 'Mindless'
            },
        ]

        created_count = 0
        updated_count = 0

        for data in ancestries_data:
            ancestry, created = UnitAncestry.objects.update_or_create(
                nome=data['nome'],
                defaults={
                    'modificador_ataque': data['modificador_ataque'],
                    'modificador_poder': data['modificador_poder'],
                    'modificador_defesa': data['modificador_defesa'],
                    'modificador_resistencia': data['modificador_resistencia'],
                    'modificador_moral': data['modificador_moral'],
                    'traits': data['traits'],
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Criada: {ancestry.get_nome_display()}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'⬤ Atualizada: {ancestry.get_nome_display()}'))

        self.stdout.write(self.style.SUCCESS(f'\n✓ Concluído: {created_count} criadas, {updated_count} atualizadas'))
