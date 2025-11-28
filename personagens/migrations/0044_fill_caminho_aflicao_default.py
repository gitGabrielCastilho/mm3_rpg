from django.db import migrations


def fill_caminho_aflicao_default(apps, schema_editor):
    Poder = apps.get_model('personagens', 'Poder')
    # Para todos os poderes antigos de Aflição sem caminho definido, assume-se caminho mental
    Poder.objects.filter(tipo='aflicao').filter(
        caminho_aflicao__isnull=True
    ).update(caminho_aflicao='mental')
    Poder.objects.filter(tipo='aflicao', caminho_aflicao='').update(caminho_aflicao='mental')


def reverse_fill_caminho_aflicao_default(apps, schema_editor):
    # reversão inofensiva: não desfazemos o caminho, apenas deixamos como está
    pass


class Migration(migrations.Migration):

    dependencies = [
		('personagens', '0043_poder_caminho_aflicao'),
    ]

    operations = [
        migrations.RunPython(fill_caminho_aflicao_default, reverse_fill_caminho_aflicao_default),
    ]
