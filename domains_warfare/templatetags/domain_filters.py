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


@register.filter
def split(value, arg):
    """Divide uma string pelo separador especificado."""
    if not value:
        return []
    try:
        return [item.strip() for item in value.split(arg)]
    except (ValueError, TypeError, AttributeError):
        return [value]
