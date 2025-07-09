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
    return d.get(key)

@register.filter
def lookup(form, campo):
    return form[campo]

