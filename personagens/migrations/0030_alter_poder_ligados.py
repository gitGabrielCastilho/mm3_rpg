from django.db import migrations


class Migration(migrations.Migration):
    """Migração vazia para resolver conflito pré-existente (antiga 0030 removida)."""

    dependencies = [
        ('personagens', '0029_poder_ligados'),
    ]

    operations = []
