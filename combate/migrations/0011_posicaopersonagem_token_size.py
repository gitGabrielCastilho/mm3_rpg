from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('combate', '0010_efeitoconcentracao'),
    ]

    operations = [
        migrations.AddField(
            model_name='posicaopersonagem',
            name='token_size',
            field=models.PositiveIntegerField(default=40),
        ),
    ]
