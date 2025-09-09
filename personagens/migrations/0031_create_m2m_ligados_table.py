from django.db import migrations

SQL_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS personagens_poder_ligados (
    id SERIAL PRIMARY KEY,
    from_poder_id integer NOT NULL REFERENCES personagens_poder (id) ON DELETE CASCADE,
    to_poder_id integer NOT NULL REFERENCES personagens_poder (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS personagens_poder_ligados_from_to_uniq ON personagens_poder_ligados (from_poder_id, to_poder_id);
CREATE INDEX IF NOT EXISTS personagens_poder_ligados_from_idx ON personagens_poder_ligados (from_poder_id);
CREATE INDEX IF NOT EXISTS personagens_poder_ligados_to_idx ON personagens_poder_ligados (to_poder_id);
"""

SQL_DROP_TABLE = """
DROP TABLE IF EXISTS personagens_poder_ligados;
"""


class Migration(migrations.Migration):
    """
    Cria manualmente a tabela M2M de 'ligados' caso a migração 0029 (alterada depois de aplicada)
    já tenha sido marcada como aplicada sem criar a tabela. Segura para re-execução (IF NOT EXISTS).
    """

    dependencies = [
        ('personagens', '0030_alter_poder_ligados'),
    ]

    operations = [
        migrations.RunSQL(SQL_CREATE_TABLE, SQL_DROP_TABLE),
    ]
