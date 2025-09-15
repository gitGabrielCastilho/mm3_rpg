from django.db import migrations


class Migration(migrations.Migration):
    # This migration is intentionally left as a no-op to resolve conflicts
    # The actual field addition is handled in 0040_poder_array depending on 0039
    dependencies = [
        ('personagens', '0034_personagem_arcana_personagem_religiao_and_more'),
    ]

    operations = []
