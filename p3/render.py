
import datetime, decimal
from functools import partial
import simplejson as json

from django import http
from django.conf import settings as dsettings


class MyEncode(simplejson.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%d/%m/%Y %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%d/%m/%Y')
        elif isinstance(obj, datetime.time):
            return obj.strftime('%H:%M')
        elif isinstance(obj, decimal.Decimal):
            return str(obj)
        elif isinstance(obj, set):
            return list(obj)

        return json.JSONEncoder.default(self, obj)


def render_to_json(f):
    json_dumps = functools.partial(simplejson.dumps, cls=MyEncode)

    if dsettings.DEBUG:
        ct = 'text/plain'
        j = lambda d: json_dumps(d, indent=2)
    else:
        ct = 'application/json'
        j = json_dumps
    def wrapper(*args, **kw):
        try:
            result = f(*args, **kw)
        except Exception, e:
            result = j(str(e))
            status = 500
        else:
            if isinstance(result, http.HttpResponse):
                return result
            else:
                from django.forms.util import ErrorDict
                status = 200 if not isinstance(result, ErrorDict) else 400
                result = j(result)
        return http.HttpResponse(content=result, content_type=ct, status=status)
    return wrapper
