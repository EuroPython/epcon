# -*- coding: UTF-8 -*-
import urllib
import httplib
import simplejson

G = 'maps.google.com'

def geocode(address, key, country):
    """
    interroga google maps e ritorna le coordinate geografiche
    dell'indirizzo passato
    """
    # see http://code.google.com/intl/it/apis/maps/documentation/geocoding/#GeocodingRequests
    params = {
        'q': address.encode('utf-8') if isinstance(address, unicode) else address,
        'key': key,
        'sensor': 'false',
        'output': 'json',
        'oe': 'utf8',
    }
    if country:
        params['gl'] = country

    url = '/maps/geo?' + urllib.urlencode(params.items())
    conn = httplib.HTTPConnection(G)
    try:
        conn.request('GET', url)
        r = conn.getresponse()
        if r.status == 200:
            return simplejson.loads(r.read())
        else:
            return {'Status': {'code': r.status }}
    finally:
        conn.close()
