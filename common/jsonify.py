import functools
import simplejson

class MyEncode(simplejson.JSONEncoder):
    def default(self, obj):
        import datetime, decimal
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

        return simplejson.JSONEncoder.default(self, obj)

json_dumps = functools.partial(simplejson.dumps, cls=MyEncode)


