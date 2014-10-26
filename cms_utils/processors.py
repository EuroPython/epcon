# -*- coding: utf-8 -*-
from django.template import Template


def process_templatetags(instance, placeholder, rendered_content, original_context):
    """
    This plugin processor render the resulting content to parse for templatetags
    in the plugin output
    """
    template = Template(rendered_content)
    return template.render(original_context)