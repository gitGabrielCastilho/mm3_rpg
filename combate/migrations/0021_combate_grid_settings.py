from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('combate', '0020_participante_charges_estado'),
    ]

    operations = [
        migrations.AddField(
            model_name='combate',
            name='grid_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='combate',
            name='grid_size',
            field=models.PositiveIntegerField(default=40),
        ),
    ]