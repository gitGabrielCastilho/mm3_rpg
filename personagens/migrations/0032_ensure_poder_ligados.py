from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('personagens', '0031_create_m2m_ligados_table'),
    ]

    operations = [
        # Re-declare the field in case earlier empty migration prevented creation in prod.
        migrations.AlterField(
            model_name='poder',
            name='ligados',
            field=models.ManyToManyField(
                to='personagens.poder',
                blank=True,
                help_text='Poderes que disparam em cadeia junto com este. Precisam ter mesmo nome, modo e duração.'
            ),
        ),
    ]