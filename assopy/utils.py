# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.core.mail import send_mail as real_send_mail

from assopy import settings

def send_email(force=False, *args, **kwargs):
    if force is False and not settings.SEND_EMAIL_TO:
        return
    if 'recipient_list' not in kwargs:
        kwargs['recipient_list'] = settings.SEND_EMAIL_TO
    if 'from_email' not in kwargs:
        kwargs['from_email'] = dsettings.DEFAULT_FROM_EMAIL
    real_send_mail(*args, **kwargs)

def dotted_import(path):
    from django.utils.importlib import import_module
    from django.core.exceptions import ImproperlyConfigured
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]

    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error importing %s: "%s"' % (path, e))

    try:
        o = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define "%s"' % (module, attr))

    return o

def geocode(address, region=''):
    import json
    import urllib

    def _e(s):
        return s.encode('utf-8') if isinstance(s, unicode) else s

    params = {
        'address': _e(address.strip()),
        'sensor': 'false',
    }
    if region:
        params['region'] = _e(region.strip())
    url = 'http://maps.googleapis.com/maps/api/geocode/json?' + urllib.urlencode(params)
    data = json.loads(urllib.urlopen(url).read())
    return data

def geocode_country(address, region=''):
    gdata = geocode(address, region)
    if not gdata:
        return None
    for r in gdata['results']:
        for address in r.get('address_components', []):
            if 'country' in address.get('types', []):
                return address['short_name']
    return None
