from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('combate', '0019_ajustar_dano_novo_sistema'),
    ]

    operations = [
        migrations.AddField(
            model_name='participante',
            name='charges_atuais',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='participante',
            name='charges_maximos',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
