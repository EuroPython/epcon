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

    return mark_safe('\n'.join(fields))


FORM_ERRORS_TEMPLATE = (
    '<div class="alert alert-danger">'
    '<h4 class="alert-heading">Unfortunately there are some errors :(</h4>'
    '{% if all_errors %}<p>{{ all_errors }}</p><hr>{% endif %}'
    '{% if field_errors %}<p>{{ field_errors }}</p>{% endif %}'
    '</div>'
)


def render_form_errors(form):
    return Template(FORM_ERRORS_TEMPLATE).render(Context({
        'all_errors': '; '.join(form.errors.get('__all__', '')),
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

    if isinstance(field.field.widget, forms.widgets.TextInput):
        return render_text_input_field(field)

    if isinstance(field.field.widget, forms.widgets.Textarea):
        return render_textarea_field(field)

    # TODO(artcz): select and multi select widgets

    return f'{field.name} -- widget not supported'


GENERIC_CHAR_FIELD_TEMPLATE = (
    '<div class="form-group">'
        '<label for="{{ label_for_id }}"'
            '{% if errors %} class="text-danger"{% endif %}>'
            '{{ label }}'
        '</label>'
        '<input type="{{ type }}" '
               'class="form-control {{ css_classes }}'
                    '{% if errors %} is-invalid{% endif %}" '
               'id="{{ html_id }}" '
               'name="{{ name }}" '
               'value="{{ value }}" '
               'placeholder="{{ placeholder }}" />'

        '{% if errors %}'
            '<p class="text-danger">'
                '{{ errors|join:", " }}'
            '</p>'
        '{% endif %}'  # errors

        '{% if help_text %}'
            '<small id="emailHelp" class="form-text text-muted">'
                '{{ help_text }}'
            '</small>'
        '{% endif %}'  # help_text

    '</div>'
)


TEXTAREA_FIELD_TEMPLATE = (
    '<div class="form-group">'
        '<label for="{{ label_for_id }}"'
            '{% if errors %} class="text-danger"{% endif %}>'
            '{{ label }}'
        '</label>'

        '<textarea '
               'class="form-control {{ css_classes }}'
                    '{% if errors %} is-invalid{% endif %}" '
               'id="{{ html_id }}" '
               'name="{{ name }}" '
               'rows="5" '
               'placeholder="{{ placeholder }}">'
               '{{ value }}'
        '</textarea>'

        '{% if errors %}'
            '<p class="text-danger">'
                '{{ errors|join:", " }}'
            '</p>'
        '{% endif %}'  # errors

        '{% if help_text %}'
            '<small id="emailHelp" class="form-text text-muted">'
                '{{ help_text }}'
            '</small>'
        '{% endif %}'  # help_text

    '</div>'
)


CHECKBOX_FIELD_TEMPLATE = (
    '<div class="form-check">'
        '<input type="checkbox" '
                'class="form-check-input" '
                'name="{{ name }}" '
                'id="{{ html_id }}"'
                '{% if value %} checked{% endif %}>'

        '<label for="{{ label_for_id }}"'
            '{% if errors %} class="text-danger"{% endif %}>'
            '{{ label|safe }}'
        '</label>'

        '{% if errors %}'
            '<p class="text-danger">'
                '{{ errors|join:", " }}'
            '</p>'
        '{% endif %}'  # errors

        '{% if help_text %}'
            '<small id="emailHelp" class="form-text text-muted">'
            '{{ help_text }}'
            '</small>'
        '{% endif %}'  # help_text

    '</div>'
)


def render_password_field(field, css_classes=""):
    return render_generic_char_field(field, type="password")


def render_email_field(field, css_classes=""):
    return render_generic_char_field(field, type="email")


def render_text_input_field(field, css_classes=""):
    return render_generic_char_field(field, type="text")


def render_generic_char_field(field, type, css_classes=""):
    return Template(GENERIC_CHAR_FIELD_TEMPLATE).render(Context({
        'type': type,
        'css_classes': css_classes,
        **default_values_for_field(field),
    }))


def render_checkbox_field(field, css_classes=""):
    return Template(CHECKBOX_FIELD_TEMPLATE).render(Context({
        'css_classes': css_classes,
        **default_values_for_field(field)
    }))


def render_textarea_field(field, css_classes=""):
    return Template(TEXTAREA_FIELD_TEMPLATE).render(Context({
        'css_classes': css_classes,
        **default_values_for_field(field)
    }))


def default_values_for_field(field):
    return {
        "label": field.label,
        "label_for_id": field.id_for_label,
        "html_id": field.id_for_label,
        'name': field.name,
        'value': field.value() or "",
        "help_text": field.help_text,
        "errors": field.errors,
        # FIXME(artcz): this is just a placeholder for a placeholder...
        'placeholder': field.label,
    }
