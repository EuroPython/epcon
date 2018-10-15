# -*- coding: utf-8 -*-
from django import forms
from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string


register = template.Library()


@register.filter
def form_field(field, classes=None):
    if not isinstance(field, forms.forms.BoundField):
        return mark_safe("<strong>[formstyle.form_field] Input parameter is not a form field</strong>")

    instance_name = '{}.{}'.format(field.form.__class__.__name__, field.name)
    field_name = field.field.__class__.__name__
    widget_name = field.field.widget.__class__.__name__

    if not classes:
        classes = ""
    elif isinstance(classes, (list, tuple)):
        classes = ' '.join(classes)
    classes += " field {} {}".format(widget_name.lower(), field_name.lower())

    return render_to_string(
        template_name=[
            'formstyle/{}.html'.format(instance_name.lower()),
            'formstyle/{}.html'.format(widget_name.lower()),
            'formstyle/base.html'
        ],
        context={
            'field': field,
            'classes': classes
        },
    )

@register.filter
def form_errors(form, classes=None):
    if not form.errors:
        return ''

    form_name = form.__class__.__name__

    if not classes:
        classes = ""
    elif isinstance(classes, (list, tuple)):
        classes = ' '.join(classes)
    classes += form_name

    return render_to_string(
        template_name=[
            'formstyle/form_{}_errors.html'.format(form_name.lower()),
            'formstyle/form_errors.html',
        ],
        context={
            'form': form,
            'classes': classes
        },
    )
