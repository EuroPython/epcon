# -*- coding: UTF-8 -*-
from assopy import settings

from django import template
from django.conf import settings as dsettings
from django.core.urlresolvers import reverse

from urllib import quote_plus

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

@register.inclusion_tag('assopy/render_janrain_box.html')
def render_janrain_box():
    if settings.JANRAIN:
        domain = settings.JANRAIN['domain']
        if not domain.endswith('/'):
            domain += '/'
        u = '%sopenid/embed?token_url=%s' % (domain, quote_plus(dsettings.DEFAULT_URL_PREFIX + reverse('assopy-janrain-token')))
    else:
        u = None
    return {
        'url': u,
    }
