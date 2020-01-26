import datetime
import json
import functools


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

        return json.JSONEncoder.default(self, obj)

json_dumps = functools.partial(json.dumps, cls=MyEncode)
