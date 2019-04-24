import datetime
import json
import functools

from django.utils.deprecation import CallableBool


class CustomEPEncode(json.JSONEncoder):  # pragma: no cover
    def default(self, obj):

        if isinstance(obj, datetime.datetime):
            return obj.strftime('%d/%m/%Y %H:%M:%S')

        if isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')

        if isinstance(obj, datetime.time):
            return obj.strftime('%H:%M')

        if isinstance(obj, set):
            return list(obj)

        if isinstance(obj, CallableBool):
            # required to support User.is_authenticated from Django 1.10
            # onwards avoid depracation warnings
            return obj is True

        return json.JSONEncoder.default(self, obj)


json_dumps = functools.partial(json.dumps, cls=CustomEPEncode)
