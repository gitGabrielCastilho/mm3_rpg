from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('combate', '0011_posicaopersonagem_token_size'),
    ]

    operations = [
        migrations.AddField(
            model_name='participante',
            name='proximo_bonus_por_atributo',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
