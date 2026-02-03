from django import template

register = template.Library()

@register.filter
def absolute(value):
    """Devuelve el valor absoluto de un número."""
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value

@register.filter(name='abs')
def abs_filter(value):
    """Alias para el filtro absolute."""
    return absolute(value)