from django import template

register = template.Library()

@register.filter
def attr(obj, nome_attr):
    return getattr(obj, nome_attr, '')

@register.filter
def field(form, field_name):
    return form[field_name]

@register.filter
def dict_get(d, key):
    """Safe dict getter for templates. Returns None when d is falsy or not a mapping."""
    try:
        return (d or {}).get(key)
    except Exception:
        return None

@register.filter
def lookup(form, campo):
    return form[campo]

@register.simple_tag(takes_context=True)
def get_perfil(context):
    """Return PerfilUsuario for the authenticated user or None if missing.

    Using this tag avoids RelatedObjectDoesNotExist errors when templates
    access user.perfilusuario before a PerfilUsuario row exists.
    """
    request = context.get('request')
    if not request or not getattr(request, 'user', None) or not request.user.is_authenticated:
        return None
    try:
        return request.user.perfilusuario
    except Exception:
        return None

@register.simple_tag
def get_perfil_de(usuario):
        """Return PerfilUsuario for the given user or None if missing.

        Use in templates that iterate over users/participants:
            {% get_perfil_de participante as perfil %}
        """
        try:
                return getattr(usuario, 'perfilusuario', None)
        except Exception:
                return None

