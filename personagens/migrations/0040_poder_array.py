from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personagens', '0039_alter_poder_casting_ability'),
        ('personagens', '0035_poder_array'),  # ensure linear chain to avoid multiple leaf nodes
    ]

    operations = [
        migrations.AddField(
            model_name='poder',
            name='array',
            field=models.CharField(
                verbose_name='Array',
                max_length=100,
                blank=True,
                default='',
                help_text=(
                    'Nome do grupo de efeitos alternativos. Entre todos os poderes com o mesmo nome, '
                    'o custo do grupo é o do poder mais caro + 1 por efeito alternativo.'
                ),
            ),
        ),
    ]
