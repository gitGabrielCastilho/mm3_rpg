from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("combate", "0014_participante_ferimentos"),
    ]

    operations = [
        migrations.AddField(
            model_name="participante",
            name="cd_aflicao_origem",
            field=models.IntegerField(default=0),
        ),
    ]
