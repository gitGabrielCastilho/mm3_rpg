from django.core.management.base import BaseCommand
from domains_warfare.models import UnitTrait


class Command(BaseCommand):
    help = 'Popula a tabela UnitTrait com todos os traits e seus custos'

    def handle(self, *args, **options):
        traits_data = [
            {
                'nome': 'amphibious',
                'descricao': 'This unit does not suffer terrain penalties for fighting in water or on land.',
                'custo': 50,
            },
            {
                'nome': 'bred_for_war',
                'descricao': 'This unit cannot be diminished, and cannot have disadvantage on Morale checks.',
                'custo': 100,
            },
            {
                'nome': 'brutal',
                'descricao': 'This unit inflicts two casualties on a successful Power test.',
                'custo': 200,
            },
            {
                'nome': 'courageous',
                'descricao': 'Once per battle, this unit can choose to succeed at a Morale check it just failed.',
                'custo': 50,
            },
            {
                'nome': 'eternal',
                'descricao': 'This unit cannot be horrified, and it always succeeds on Morale checks to attack undead and fiends.',
                'custo': 50,
            },
            {
                'nome': 'feast',
                'descricao': 'If this unit diminishes an enemy unit, it immediately gains a free attack against that unit.',
                'custo': 50,
            },
            {
                'nome': 'horrify',
                'descricao': 'If this unit inflicts a casualty on an enemy unit, force a DC 15 Morale check. Failure exhausts the unit.',
                'custo': 200,
            },
            {
                'nome': 'martial',
                'descricao': 'Inflicts two casualties on a successful Power check if this unit\'s size is greater than their target\'s.',
                'custo': 100,
            },
            {
                'nome': 'mindless',
                'descricao': 'This unit cannot fail Morale checks.',
                'custo': 100,
            },
            {
                'nome': 'regenerate',
                'descricao': 'When this unit refreshes, increment its casualty die. This ability ceases to function if the unit suffers a casualty from battle magic.',
                'custo': 200,
            },
            {
                'nome': 'ravenous',
                'descricao': 'While there is a diminished enemy unit, this unit can spend a round feeding on the corpses. Increment their casualty die.',
                'custo': 50,
            },
            {
                'nome': 'rock_hurler',
                'descricao': 'If this unit succeeds on an Attack check, it inflicts 2 casualties, against fortifications deal 1d6.',
                'custo': 250,
            },
            {
                'nome': 'savage',
                'descricao': 'This unit has advantage on the first Attack check it makes each battle.',
                'custo': 50,
            },
            {
                'nome': 'stalwart',
                'descricao': 'Enemy battle magic has disadvantage on power tests against this unit.',
                'custo': 50,
            },
            {
                'nome': 'twisting_roots',
                'descricao': 'As an action, this unit can sap the walls of a fortification. Siege units have advantage on Power checks against sapped fortifications.',
                'custo': 200,
            },
            {
                'nome': 'undead',
                'descricao': 'Green and Regular troops must pass a Morale check to attack this unit. Each enemy unit need only do this once.',
                'custo': 50,
            },
        ]

        created_count = 0
        updated_count = 0

        for data in traits_data:
            trait, created = UnitTrait.objects.update_or_create(
                nome=data['nome'],
                defaults={
                    'descricao': data['descricao'],
                    'custo': data['custo'],
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Criado: {trait.get_nome_display()} (custo {trait.custo})'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'⬤ Atualizado: {trait.get_nome_display()} (custo {trait.custo})'))

        self.stdout.write(self.style.SUCCESS(f'\n✓ Concluído: {created_count} criados, {updated_count} atualizados'))
