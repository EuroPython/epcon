# -*- coding: utf-8 -*-
from django.template import Template, Context


def process_templatetags(instance, placeholder, rendered_content, original_context):
    """
    This plugin processor render the resulting content to parse for templatetags
    in the plugin output
    """
    context = Context(original_context)

    try:
        template = Template(rendered_content)
    except Exception as e:
        return '<p><strong>Template Error: {}</strong></p>{}'.format(str(e), rendered_content)
    return template.render(context)
