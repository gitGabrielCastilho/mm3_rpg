from django.core.management.base import BaseCommand
from domains_warfare.models import UnitExperience


class Command(BaseCommand):
    help = 'Popula a tabela UnitExperience com todos os níveis e seus modificadores'

    def handle(self, *args, **options):
        experience_data = [
            {
                'nome': 'green',
                'descricao': 'Tropas recrutas sem experiência de combate.',
                'modificador_ataque': 0,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 0,
                'modificador_moral': 0,
            },
            {
                'nome': 'regular',
                'descricao': 'Tropas com treinamento básico completo.',
                'modificador_ataque': 1,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 1,
                'modificador_moral': 1,
            },
            {
                'nome': 'seasoned',
                'descricao': 'Tropas que participaram de vários combates.',
                'modificador_ataque': 1,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 1,
                'modificador_moral': 2,
            },
            {
                'nome': 'veteran',
                'descricao': 'Tropas veteranas com muito tempo de experiência.',
                'modificador_ataque': 1,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 1,
                'modificador_moral': 3,
            },
            {
                'nome': 'elite',
                'descricao': 'Tropas de elite com habilidades excepcionais.',
                'modificador_ataque': 2,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 2,
                'modificador_moral': 4,
            },
            {
                'nome': 'super_elite',
                'descricao': 'Tropas lendárias de extraordinário poder e disciplina.',
                'modificador_ataque': 2,
                'modificador_poder': 0,
                'modificador_defesa': 0,
                'modificador_resistencia': 2,
                'modificador_moral': 5,
            },
        ]

        created_count = 0
        updated_count = 0

        for data in experience_data:
            experience, created = UnitExperience.objects.update_or_create(
                nome=data['nome'],
                defaults={
                    'descricao': data['descricao'],
                    'modificador_ataque': data['modificador_ataque'],
                    'modificador_poder': data['modificador_poder'],
                    'modificador_defesa': data['modificador_defesa'],
                    'modificador_resistencia': data['modificador_resistencia'],
                    'modificador_moral': data['modificador_moral'],
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Criado: {experience.get_nome_display()}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'⬤ Atualizado: {experience.get_nome_display()}'))

        self.stdout.write(self.style.SUCCESS(f'\n✓ Concluído: {created_count} criados, {updated_count} atualizados'))
