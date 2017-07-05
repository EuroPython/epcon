from __future__ import absolute_import

import functools
import os.path

from decorator import decorator
from django import http
from django.conf import settings as dsettings
from django.forms.utils import ErrorDict
from django.shortcuts import render_to_response
from django.template import RequestContext

from .jsonify import json_dumps


def render_to_json(f): # pragma: no cover
    """
    Decorator to be applied to a view to serialize json in the result.
    """
    if dsettings.DEBUG:
        ct = 'text/plain'
        j = lambda d: json_dumps(d, indent = 2)
    else:
        ct = 'application/json'
        j = json_dumps

    @functools.wraps(f)
    def wrapper(func, *args, **kw):
        try:
            result = func(*args, **kw)
        except Exception, e:
            result = j(str(e))
            status = 500
        else:
            if isinstance(result, http.HttpResponse):
                return result
            else:
                result = j(result)
                status = 200 if not isinstance(result, ErrorDict) else 400
        return http.HttpResponse(content = result, content_type = ct, status = status)
    return decorator(wrapper, f)


# see: http://www.djangosnippets.org/snippets/821/
def render_to_template(template):  # pragma: no cover
    """
    Decorator for Django views that sends returned dict to render_to_response function
    with given template and RequestContext as context instance.

    If view doesn't return dict then decorator simply returns output.
    Additionally view can return two-tuple, which must contain dict as first
    element and string with template name as second. This string will
    override template name, given as parameter

    Parameters:

     - template: template name to use
    """
    def renderer(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kw):
            output = func(request, *args, **kw)
            if isinstance(output, (list, tuple)):
                output, tpl = output
            else:
                tpl = template
            ct = 'text/html'
            if tpl.endswith('xml'):
                ct = 'text/xml' if dsettings.DEBUG else 'application/xml'
            if isinstance(output, dict):
                if request.is_ajax() and dsettings.TEMPLATE_FOR_AJAX_REQUEST:
                    tpl = ('%s_body%s' % os.path.splitext(tpl), tpl)
                return render_to_response(tpl, output, RequestContext(request), content_type=ct)
            else:
                return output
        return wrapper
    return renderer
