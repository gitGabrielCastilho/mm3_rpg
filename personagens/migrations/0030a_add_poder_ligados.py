from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds the missing ManyToManyField 'ligados' for Poder if DB didn't get it due to earlier empty migration."""

    dependencies = [
        ('personagens', '0030_alter_poder_ligados'),  # maintain linear order; 0030 attempted alter, but DB may lack field
    ]

    operations = [
        # AddField will create the M2M table if it does not exist. If it already exists, Django will raise
        # an error; in that case you can fake this migration (manage.py migrate --fake personagens 0030a).
        migrations.AddField(
            model_name='poder',
            name='ligados',
            field=models.ManyToManyField(
                blank=True,
                help_text='Poderes que disparam em cadeia junto com este. Precisam ter mesmo nome, modo e duração.',
                to='personagens.poder'
            ),
        ),
    ]
