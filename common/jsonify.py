import datetime
import json
import functools

from django.utils.deprecation import CallableBool


class MyEncode(json.JSONEncoder):  # pragma: no cover
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%d/%m/%Y %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%d/%m/%Y')
        elif isinstance(obj, datetime.time):
            return obj.strftime('%H:%M')
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, CallableBool):
            # required to support User.is_authenticated from Django 1.10 onwards
            # and avoid depracation warnings
            return obj == True

        return json.JSONEncoder.default(self, obj)

json_dumps = functools.partial(json.dumps, cls=MyEncode)
