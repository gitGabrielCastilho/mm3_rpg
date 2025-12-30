from django import template

register = template.Library()


@register.filter
def mul(value, arg):
    """Multiplica o valor pelo argumento."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def add_sign(value):
    """Adiciona sinal de + para valores positivos."""
    try:
        num = int(value)
        if num > 0:
            return f"+{num}"
        return str(num)
    except (ValueError, TypeError):
        return str(value)
