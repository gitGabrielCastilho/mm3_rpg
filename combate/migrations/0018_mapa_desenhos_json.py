# Generated migration to add desenhos_json field to Mapa

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('combate', '0017_backfill_nome_ordem'),
    ]

    operations = [
        migrations.AddField(
            model_name='mapa',
            name='desenhos_json',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
