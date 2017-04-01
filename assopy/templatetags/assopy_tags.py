# -*- coding: UTF-8 -*-
from assopy import models
from assopy import settings

from django import forms
from django import template
from django.conf import settings as dsettings
from django.core import paginator
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

import urllib

register = template.Library()

_field_template_standard = template.Template("""
    <div class="{{ classes }}">
        <label for="{{ field.auto_id }}">{{ field.label|safe }}{% if field.field.required %}<span class="required">{{ required_text }}</span>{% endif %}</label>
        {{ field }}
        {% if field.help_text %}<div class="help-text">{{ field.help_text|safe }}</div>{% endif %}
        {{ field.errors }}
    </div>
""")

_field_template_label_inline = template.Template("""
    <div class="{{ classes }}">
        <label for="{{ field.auto_id }}">{{ field }} {{ field.label|safe }}{% if field.field.required %}<span class="required">{{ required_text }}</span>{% endif %}</label>
        {% if field.help_text %}<div class="help-text">{{ field.help_text|safe }}</div>{% endif %}
        {{ field.errors }}
    </div>
""")

_field_template_input_list = template.Template("""
    <div class="{{ classes }}">
        <label>{{ field.label|safe }}{% if field.field.required %}<span class="required">{{ required_text }}</span>{% endif %}</label>
        {{ field }}
        {% if field.help_text %}<div class="help-text">{{ field.help_text|safe }}</div>{% endif %}
        {{ field.errors }}
    </div>
""")

_field_template_no_label = template.Template("""
    <div class="{{ classes }}">
        {{ field }}
        {% if field.help_text %}<div class="help-text">{{ field.help_text|safe }}</div>{% endif %}
        {{ field.errors }}
    </div>
""")

fields_template = {
    None: _field_template_standard,
    forms.widgets.CheckboxInput: _field_template_label_inline,
    forms.widgets.RadioSelect: _field_template_input_list,
    'no_label': _field_template_no_label,
}

@register.filter()
def field(field, cls=None):
    if not hasattr(field, 'field'):
        return 'Invalid field "%r"' % field

    tpl_key = None
    extra = []
    if cls:
        extra = cls.split(None)
        for v in cls.split(None):
            if v.startswith('tpl:'):
                tpl_key = v[4:]
            else:
                extra.append(v)

    classes = [ 'field' ]
    if field.field.required:
        classes.append('required')
    classes.extend(extra)
    classes.append(field.field.__class__.__name__.lower())
    if field.errors:
        classes.append('error')

    widget = field.field.widget
    if isinstance(widget, (forms.HiddenInput,)):
        return str(field)
    else:
        if not tpl_key:
            tpl_key = type(widget)
        try:
            tpl = fields_template[tpl_key]
        except KeyError:
            tpl = fields_template[None]

        ctx = {
            'classes': ' '.join(classes),
            'field': field,
            'required_text': _('(required)'),
        }
        return tpl.render(template.Context(ctx))

_form_errors_tpl = template.Template("""
    {% load i18n %}
    <div class="error-notice">
        {% if form.non_field_errors %}
            {% for e in form.non_field_errors %}
            <div>↓ {{ e }}</div>
            {% endfor %}
        {% else %}
            <div>↓ {% trans "Warning, check your data on the form below" %}</div>
        {% endif %}
    </div>
""")
@register.filter()
def form_errors(form, cls=None):
    if not form.errors:
        return ''
    classes = [ 'error-notice' ]
    return _form_errors_tpl.render(template.Context(locals()))

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

@register.filter
def field_display_value(field):
    val = field_value(field)
    if hasattr(field.field, 'choices'):
        data = dict(field.field.choices)
        if isinstance(field.field, (forms.MultipleChoiceField,)):# forms.TypedMultipleChoiceField)):
            output = []
            for x in val:
                output.append(data.get(x, ''))
        else:
            output = data.get(val, '')
        val = output
    return val

@register.filter
def field_widget(field, attrs):
    attrs = dict(map(lambda _: _.strip(), x.split('=')) for x in attrs.split(','))
    field.field.widget.attrs.update(attrs)
    return field

@register.filter
def as_range(value):
    return range(value)

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
        u = '%sopenid/embed?token_url=%s' % (domain, urllib.quote_plus(dsettings.DEFAULT_URL_PREFIX + reverse('assopy-janrain-token')))
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

def _get_cached_order_status(request, order_id):
    try:
        cache = request._order_cache
    except AttributeError:
        cache = request._order_cache = {}

    if order_id not in cache:
        cache[order_id] = models.Order.objects.get(pk=order_id).complete()
    return cache[order_id]

@register.tag
def order_complete(parser, token):
    """
    {% order_complete order_id as var %}
    Equivalente a `Order.objects.get(id=order_id).complete()` ma memorizza il
    risultato in una cache che dura quanto la richiesta corrente.
    """
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" %tag_name)
    var_name = contents[-1]
    order_id = contents[1]

    class Node(template.Node):
        def __init__(self, order_id, var_name):
            self.order_id = template.Variable(order_id)
            self.var_name = var_name
        def render(self, context):
            try:
                order_id = self.order_id.resolve(context)
            except AttributeError:
                complete = False
            else:
                request = context.get('request')
                if request:
                    complete = _get_cached_order_status(request, order_id)
                else:
                    complete = models.Order.objects.get(id=order_id).complete()

            context[self.var_name] = complete
            return ''
    return Node(order_id, var_name)

@register.filter()
def include_payment(order, type):
    return order.orderitem_set.filter(ticket__fare__payment_type=type).exists()

@register.filter()
def include_fare(order, codes):
    return order.orderitem_set.filter(ticket__fare__code__in=codes.split(',')).exists()

@register.filter
def user_coupons(user):
    output = {'valid': [], 'invalid': []}
    for c in user.coupon_set.all():
        if c.valid(user):
            output['valid'].append(c)
        else:
            output['invalid'].append(c)
    return output

@register.inclusion_tag('assopy/render_profile_last_block.html', takes_context=True)
def render_profile_last_block(context):
    return context

@register.simple_tag(takes_context=True)
def paginate(context, qs, count=20):
    pages = paginator.Paginator(qs, int(count))
    try:
        ix = int(context['request'].GET.get('page', 1))
    except ValueError:
        ix = 1
    try:
        return pages.page(ix)
    except:
        ix = 1 if ix < 1 else pages.num_pages
        return pages.page(ix)

@register.simple_tag(takes_context=True)
def add_page_number_to_query(context, page, get=None):
    if get is None:
        get = context['request'].GET.copy()
    else:
        get = dict(get)
    get['page'] = page
    return urllib.urlencode(get)

@register.inclusion_tag('assopy/render_voucher.html', takes_context=True)
def render_voucher(context, item):
    return {
        'item': item,
    }

@register.assignment_tag(takes_context=True)
def orderitem_can_be_refunded(context, item):
    req = context['request']
    try:
        d = req.session['doppelganger']
    except KeyError:
        user = context['user']
    else:
        from django.contrib.auth.models import User
        user = User.objects.get(id=d[0])
    return settings.ORDERITEM_CAN_BE_REFUNDED(user, item)
