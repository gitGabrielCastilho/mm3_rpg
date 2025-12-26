from django import template

register = template.Library()

@register.filter
def dano_condicao(nivel):
    """Mapeia o estado de dano (1-4) para a condição textual correspondente.
    
    Novo sistema de dano baseado em graus de falha:
        1 -> Ferimento (apenas +1 Ferimento)
        2 -> Tonto (Ferimento + Tonto)
        3 -> Abatido (Ferimento + Abatido)
        4 -> Incapacitado
    """
    if not nivel or nivel <= 0:
        return "—"
    tabela = {
        1: 'Ferimento',
        2: 'Tonto',
        3: 'Abatido',
        4: 'Incapacitado',
    }
    return tabela.get(int(nivel), '—')
