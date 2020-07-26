import functools
from decorator import decorator

from django import http
from django.conf import settings
from django.forms.utils import ErrorDict

from common.jsonify import json_dumps


def render_to_json(f):
    """
    Decorator to be applied to a view to serialize json in the result.
    """
    @functools.wraps(f)
    def wrapper(func, *args, **kw):
        if settings.DEBUG:
            ct = 'text/plain'
            j = lambda d: json_dumps(d, indent=2)
        else:
            ct = 'application/json'
            j = json_dumps

        try:
            result = func(*args, **kw)
        except Exception as e:
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
