# -*- coding: utf-8 -*-
from django.template import Template


def process_templatetags(instance, placeholder, rendered_content, original_context):
    """
    This plugin processor render the resulting content to parse for templatetags
    in the plugin output
    """
    try:
        template = Template(rendered_content)
    except Exception, e:
        return u'<p><strong>Template Error: {}</strong></p>{}'.format(str(e), rendered_content)
    return template.render(original_context)
