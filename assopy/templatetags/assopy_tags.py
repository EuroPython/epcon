# -*- coding: UTF-8 -*-
from django import template

register = template.Library()

_field_tpl = template.Template("""
    <div class="{{ classes|join:" " }}">
        {{ field.label_tag }}
        {{ field }}
        {{ field.errors }}
        {% if field.help_text %}<div class="help-text">{{ field.help_text }}</div>{% endif %}
    </div>
""")
@register.filter()
def field(field, cls=None):
    classes = [ 'field' ]
    if field.field.required:
        classes.append('required')
    if cls:
        classes.extend(cls.split(','))
    return _field_tpl.render(template.Context(locals()))
