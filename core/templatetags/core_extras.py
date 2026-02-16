from django import template

register = template.Library()


@register.filter
def dict_get(mapping, key):
    if isinstance(mapping, dict):
        return mapping.get(key)
    return None
