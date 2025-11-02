from django.db import migrations, models


def purge_items(apps, schema_editor):
    Item = apps.get_model('itens', 'Item')
    Item.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('itens', '0003_item_mods'),
    ]

    operations = [
        # Ensure nome is unique and remove previous unique_together implicitly
        migrations.AlterField(
            model_name='item',
            name='nome',
            field=models.CharField(max_length=100, unique=True),
        ),
        # Create ItemPoder
        migrations.CreateModel(
            name='ItemPoder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('tipo', models.CharField(choices=[('descritivo', 'Descritivo'), ('aflicao', 'Aflição'), ('dano', 'Dano'), ('cura', 'Cura'), ('buff', 'Buff/Debuff'), ('aprimorar', 'Aprimorar/Reduzir')], default='dano', max_length=20)),
                ('modo', models.CharField(choices=[('area', 'Área'), ('percepcao', 'Percepção'), ('ranged', 'À Distância'), ('melee', 'Corpo a Corpo')], default='melee', max_length=20)),
                ('duracao', models.CharField(choices=[('instantaneo', 'Instantâneo'), ('concentracao', 'Concentração'), ('sustentado', 'Sustentado')], default='instantaneo', max_length=20)),
                ('nivel_efeito', models.IntegerField(default=0)),
                ('bonus_ataque', models.IntegerField(default=0)),
                ('somar_forca_no_nivel', models.BooleanField(default=False)),
                ('defesa_ativa', models.CharField(choices=[('esquiva', 'Esquiva'), ('aparar', 'Aparar')], default='aparar', max_length=20)),
                ('defesa_passiva', models.CharField(choices=[('fortitude', 'Fortitude'), ('resistencia', 'Resistência'), ('vontade', 'Vontade')], default='resistencia', max_length=20)),
                ('casting_ability', models.CharField(choices=[('forca', 'Força'), ('vigor', 'Vigor'), ('destreza', 'Destreza'), ('agilidade', 'Agilidade'), ('luta', 'Luta'), ('inteligencia', 'Inteligência'), ('prontidao', 'Prontidão'), ('presenca', 'Presença'), ('aparar', 'Aparar'), ('esquivar', 'Esquiva'), ('fortitude', 'Fortitude'), ('vontade', 'Vontade'), ('resistencia', 'Resistência')], default='inteligencia', max_length=20)),
                ('charges', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('array', models.CharField(blank=True, default='', max_length=100)),
                ('item', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='poderes', to='itens.item')),
            ],
        ),
        migrations.RunPython(purge_items, migrations.RunPython.noop),
    ]
