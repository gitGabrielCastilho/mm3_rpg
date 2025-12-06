from django.db import migrations


def backfill_nome_ordem(apps, schema_editor):
    Participante = apps.get_model('combate', 'Participante')
    # Group by combate + personagem
    qs = Participante.objects.all().order_by('combate_id', 'personagem_id', 'id')
    current_key = None
    idx = 0
    updates = []
    for p in qs:
        key = (p.combate_id, p.personagem_id)
        if key != current_key:
            current_key = key
            idx = 1
        else:
            idx += 1
        if p.nome_ordem != idx:
            p.nome_ordem = idx
            updates.append(p)
    if updates:
        Participante.objects.bulk_update(updates, ['nome_ordem'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('combate', '0016_participante_nome_ordem'),
    ]

    operations = [
        migrations.RunPython(backfill_nome_ordem, noop),
    ]
