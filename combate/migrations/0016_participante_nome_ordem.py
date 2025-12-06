from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('combate', '0015_participante_cd_aflicao_origem'),
    ]

    operations = [
        migrations.AddField(
            model_name='participante',
            name='nome_ordem',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
