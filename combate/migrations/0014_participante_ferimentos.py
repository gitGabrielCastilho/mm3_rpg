from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('combate', '0013_participante_penalidade_salv_aflicao_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='participante',
            name='ferimentos',
            field=models.IntegerField(default=0),
        ),
        migrations.RunSQL(
            sql='UPDATE combate_participante SET ferimentos = COALESCE(penalidade_salv_dano,0) + COALESCE(penalidade_salv_aflicao,0);',
            reverse_sql='UPDATE combate_participante SET ferimentos = 0;',
        ),
        migrations.RemoveField(
            model_name='participante',
            name='penalidade_salv_dano',
        ),
        migrations.RemoveField(
            model_name='participante',
            name='penalidade_salv_aflicao',
        ),
    ]
