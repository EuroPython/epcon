from __future__ import absolute_import

import functools

import simplejson
from decorator import decorator
from django import http
from django.conf import settings as dsettings
from django.forms.utils import ErrorDict

from .jsonify import json_dumps

def render_to_json(f):
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