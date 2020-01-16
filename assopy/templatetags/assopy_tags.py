from django import forms
from django import template
from django.core import paginator
from django.utils.translation import ugettext as _

import urllib.request, urllib.parse, urllib.error

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
    if isinstance(widget, forms.HiddenInput):
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


@register.filter
def user_coupons(user):
    output = {'valid': [], 'invalid': []}
    for c in user.coupon_set.all():
        if c.valid(user):
            output['valid'].append(c)
        else:
            output['invalid'].append(c)
    return output


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
    return urllib.parse.urlencode(get)
