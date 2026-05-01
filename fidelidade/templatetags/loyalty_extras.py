from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value
