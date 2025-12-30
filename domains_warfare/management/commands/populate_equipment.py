from django.core.management.base import BaseCommand
from domains_warfare.models import UnitEquipment


class Command(BaseCommand):
    help = 'Popula a tabela UnitEquipment com todos os tipos de equipamento'

    def handle(self, *args, **options):
        equipment_data = [
            {
                'nome': 'light',
                'descricao': 'Equipamento leve que melhora a mobilidade.',
                'modificador_poder': 1,
                'modificador_defesa': 1,
            },
            {
                'nome': 'medium',
                'descricao': 'Equipamento padrão que oferece boa proteção.',
                'modificador_poder': 2,
                'modificador_defesa': 2,
            },
            {
                'nome': 'heavy',
                'descricao': 'Equipamento pesado que fornece proteção significativa.',
                'modificador_poder': 4,
                'modificador_defesa': 4,
            },
            {
                'nome': 'super_heavy',
                'descricao': 'Equipamento super pesado oferecendo proteção máxima.',
                'modificador_poder': 6,
                'modificador_defesa': 6,
            },
        ]

        created_count = 0
        updated_count = 0

        for data in equipment_data:
            equipment, created = UnitEquipment.objects.update_or_create(
                nome=data['nome'],
                defaults={
                    'descricao': data['descricao'],
                    'modificador_poder': data['modificador_poder'],
                    'modificador_defesa': data['modificador_defesa'],
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Criado: {equipment.get_nome_display()}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'⬤ Atualizado: {equipment.get_nome_display()}'))

        self.stdout.write(self.style.SUCCESS(f'\n✓ Concluído: {created_count} criados, {updated_count} atualizados'))
