# Generated migration for reformulated damage system

from django.db import migrations


def ajustar_dano_para_novo_sistema(apps, schema_editor):
    """
    Ajusta valores de dano existentes para o novo sistema de condições.
    
    Novo sistema:
    - dano representa o ESTADO da condição (1-4), não é cumulativo
    - 1 = Ferimento
    - 2 = Tonto
    - 3 = Abatido
    - 4 = Incapacitado
    
    Valores > 4 são truncados para 4 (Incapacitado).
    """
    Participante = apps.get_model('combate', 'Participante')
    
    # Limita valores de dano a 4 (Incapacitado é o máximo)
    participantes_com_dano_alto = Participante.objects.filter(dano__gt=4)
    if participantes_com_dano_alto.exists():
        participantes_com_dano_alto.update(dano=4)
        print(f"Ajustados {participantes_com_dano_alto.count()} participantes com dano > 4 para dano = 4 (Incapacitado)")


def reverter_ajuste(apps, schema_editor):
    """
    Reversão: não há necessidade de fazer nada, pois não sabemos
    quais eram os valores originais > 4.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('combate', '0018_mapa_desenhos_json'),
    ]

    operations = [
        migrations.RunPython(ajustar_dano_para_novo_sistema, reverter_ajuste),
    ]
