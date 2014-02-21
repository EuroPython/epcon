# -*- coding: UTF-8 -*-
from django import forms
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def form_field(field, classes=None):
    if not isinstance(field, forms.forms.BoundField):
        return mark_safe("<strong>[formstyle.form_field] Input parameter is not a form field</strong>")

    instance_name = '{}.{}'.format(field.form.__class__.__name__, field.name)
    field_name = field.field.__class__.__name__
    widget_name = field.field.widget.__class__.__name__
    tpl =template.loader.select_template((
        'formstyle/{}.html'.format(instance_name.lower()),
        'formstyle/{}.html'.format(widget_name.lower()),
        'formstyle/base.html'))

    if not classes:
        classes = ""
    elif isinstance(classes, (list, tuple)):
        classes = ' '.join(classes)
    classes += " {} {}".format(widget_name.lower(), field_name.lower())

    ctx = template.Context({
        'field': field,
        'classes': classes
    })
    return tpl.render(ctx)
