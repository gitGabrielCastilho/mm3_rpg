from django.db import migrations


def forwards(apps, schema_editor):
    Poder = apps.get_model('personagens', 'Poder')
    # Convert any existing 'debuff' tipos to 'buff' and negate nivel_efeito to maintain semantics if needed.
    # Here we keep nivel_efeito as-is; combat uses sign to decide add/subtract. We only unify the type.
    Poder.objects.filter(tipo='debuff').update(tipo='buff')


def backwards(apps, schema_editor):
    # No safe automatic split back; leave as no-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('personagens', '0034_personagem_arcana_personagem_religiao_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
