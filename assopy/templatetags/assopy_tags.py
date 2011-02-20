# -*- coding: UTF-8 -*-
from assopy import settings

from django import forms
from django import template
from django.conf import settings as dsettings
from django.core.urlresolvers import reverse

from urllib import quote_plus

register = template.Library()

_field_tpl = template.Template("""
    <div class="{{ classes|join:" " }}">
        <label for="{{ field.auto_id }}">{% if field.field.required %}<span class="show-tooltip required" title="required">*</span>{% endif %}{{ field.label }}</label>
        {{ field }}
        {% if field.help_text %}<div class="help-text">{{ field.help_text|safe }}</div>{% endif %}
        {{ field.errors }}
    </div>
""")
@register.filter()
def field(field, cls=None):
    classes = [ 'field' ]
    if field.field.required:
        classes.append('required')
    if cls:
        classes.extend(cls.split(','))
    classes.append(field.field.__class__.__name__.lower())
    if field.errors:
        classes.append('error')
    if isinstance(field.field.widget, (forms.HiddenInput,)):
        return str(field)
    else:
        return _field_tpl.render(template.Context(locals()))

# in django 1.3 questo filtro non serve più, si potrà usare direttamente
# field.value
# http://code.djangoproject.com/ticket/10427
@register.filter
def field_value(field):
	""" 
	Returns the value for this BoundField, as rendered in widgets. 
	""" 
	if field.form.is_bound: 
		if isinstance(field.field, forms.FileField) and field.data is None: 
			val = field.form.initial.get(field.name, field.field.initial) 
		else: 
			val = field.data 
	else:
		val = field.form.initial.get(field.name, field.field.initial)
		if callable(val):
			val = val()
	if val is None:
		val = ''
	return val

@register.inclusion_tag('assopy/render_janrain_box.html', takes_context=True)
def render_janrain_box(context, next=None, mode='embed'):
    if settings.JANRAIN:
        # mi salvo, nella sessione corrente, dove vuol essere rediretto
        # l'utente una volta loggato
        if next:
            context['request'].session['jr_next'] = next
        domain = settings.JANRAIN['domain']
        if not domain.endswith('/'):
            domain += '/'
        u = '%sopenid/embed?token_url=%s' % (domain, quote_plus(dsettings.DEFAULT_URL_PREFIX + reverse('assopy-janrain-token')))
    else:
        u = None
    return {
        'url': u,
        'mode': mode,
    }

class TNode(template.Node):
    def _set_var(self, v):
        if not v:
            return v
        if v.startswith('"') and v.endswith('"'):
            return v[1:-1]
        else:
            return template.Variable(v)

    def _get_var(self, v, context):
        try:
            return v.resolve(context)
        except AttributeError:
            return v

