from django import forms
from django.template import Context, Library, Template
from django.utils.safestring import mark_safe

register = Library()


@register.simple_tag
def render_form(form):
    fields = []

    if form.errors:
        fields.append(render_form_errors(form))

    for field in form:
        fields.append(render_field(field))

    return mark_safe(''.join(fields))


FORM_ERRORS_TEMPLATE = (
    '<div class="alert alert-danger">'
    '<h4 class="alert-heading">Unfortunately there are some errors :(</h4>'
    '{% if all_errors %}<p>{{ all_errors }}</p><hr>{% endif %}'
    '{% if field_errors %}<p>{{ field_errors }}</p>{% endif %}'
    '</div>'
)


def render_form_errors(form):
    return Template(FORM_ERRORS_TEMPLATE).render(Context({
        'all_errors': form.errors.get('__all__', ''),
        'field_errors': render_summary_field_errors(form.errors)
    }))


def render_summary_field_errors(errors):
    output = []
    for fieldname, errs in errors.items():
        if fieldname == '__all__':
            continue

        errs = ', '.join(errs)
        output.append(
            f'<p><strong>{fieldname}</strong> {errs}'
        )

    return mark_safe(''.join(output))


@register.simple_tag
def render_field(field):

    if isinstance(field.field.widget, forms.widgets.PasswordInput):
        return render_password_field(field)

    if isinstance(field.field.widget, forms.widgets.EmailInput):
        return render_email_field(field)

    if isinstance(field.field.widget, forms.widgets.CheckboxInput):
        return render_checkbox_field(field)

    return "Nope not supported yet"


GENERIC_CHAR_FIELD_TEMPLATE = (
    '<div class="form-group">'
        '<label for="{{ label_for_id }}">{{ label }}</label>'
        '<input type="{{ type }}"'
               'class="form-control {{ css_classes }}" '
               'id="{{ html_id }}" '
               'name="{{ name }}" '
               'value="{{ value }}" '
               'placeholder="{{ placeholder }}">'
        '{% if help_text %}'
            '<small id="emailHelp" class="form-text text-muted">'
                '{{ help_text }}'
            '</small>'
        '{% endif %}'
    '</div>'
)


CHECKBOX_FIELD_TEMPLATE = (
    '<div class="form-check">'
        '<input type="checkbox" '
                'class="form-check-input" '
                'name="{{ name }}" '
                'id="{{ html_id }}"'
                '{% if value %} checked{% endif %}>'
        '<label for="{{ label_for_id }}">{{ label|safe }}</label>'
        '{% if help_text %}'
            '<small id="emailHelp" class="form-text text-muted">'
            '{{ help_text }}'
            '</small>'
        '{% endif %}'
    '</div>'
)


def render_password_field(field, css_classes=""):
    return Template(GENERIC_CHAR_FIELD_TEMPLATE).render(Context({
        'type': 'password',
        "label": field.label,
        "label_for_id": field.id_for_label,
        "html_id": field.id_for_label,
        'name': field.name,
        'value': field.value or "",
        'css_classes': css_classes,
        'placeholder': "placeholder",
        "help_text": field.help_text,
    }))


def render_email_field(field, css_classes=""):
    return Template(GENERIC_CHAR_FIELD_TEMPLATE).render(Context({
        'type': 'email',
        "label": field.label,
        "label_for_id": field.id_for_label,
        "html_id": field.id_for_label,
        'name': field.name,
        'value': field.value or "",
        'css_classes': css_classes,
        'placeholder': "placeholder",
        "help_text": field.help_text,
    }))


def render_checkbox_field(field, css_classes=""):
    return Template(CHECKBOX_FIELD_TEMPLATE).render(Context({
        "label": field.label,
        "label_for_id": field.id_for_label,
        "html_id": field.id_for_label,
        'name': field.name,
        'value': field.value or "",
        'css_classes': css_classes,
        'placeholder': "placeholder",
        "help_text": field.help_text,
    }))
