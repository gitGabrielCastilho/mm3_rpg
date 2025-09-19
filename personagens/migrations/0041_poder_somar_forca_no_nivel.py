from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personagens', '0040_poder_array'),
    ]

    operations = [
        migrations.AddField(
            model_name='poder',
            name='somar_forca_no_nivel',
            field=models.BooleanField(default=False, help_text='Quando marcado e o poder for Dano Corpo a Corpo, o Nível de Efeito efetivo soma a Força do personagem.', verbose_name='Somar Força ao Nível de Efeito (melee)'),
        ),
    ]
