from django.db import migrations, models


class Migration(migrations.Migration):
    """Merge 0030a_add_poder_ligados and 0032_ensure_poder_ligados to resolve multiple leaf nodes.

    Keeps the latest help_text for campo 'ligados'.
    """

    dependencies = [
        ('personagens', '0030a_add_poder_ligados'),
        ('personagens', '0032_ensure_poder_ligados'),
    ]

    operations = [
        migrations.AlterField(
            model_name='poder',
            name='ligados',
            field=models.ManyToManyField(
                'self',
                blank=True,
                symmetrical=False,
                help_text='Poderes que disparam em cadeia junto com este. Precisam ter mesmo nome, modo e duração.'
            ),
        ),
    ]