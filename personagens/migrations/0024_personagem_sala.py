from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('salas', '0004_sala_senha'),
        ('personagens', '0023_personagem_is_npc'),
    ]

    operations = [
        migrations.AddField(
            model_name='personagem',
            name='sala',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='personagens', to='salas.sala'),
        ),
    ]
