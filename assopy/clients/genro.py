# -*- coding: UTF-8 -*-
from assopy import settings
from assopy.clients.gnrbag import Bag

from lxml import objectify

import urllib

def _get(subpath):
    url = settings.BACKEND + subpath
    f = urllib.urlopen(url)
    return objectify.fromstring(f.read())

def _post(subpath, bag=None):
    url = settings.BACKEND + subpath
    body = {}
    if bag is not None:
        body['data'] = bag.toXml()
    f = urllib.urlopen(url, urllib.urlencode(body))
    b = Bag()
    b.fromXml(f.read())
    return b

def user(id):
    return _get('/users/%s' % id)   

def create_user(first_name, last_name, email):
    b = Bag()
    b['firstname'] = first_name
    b['lastname'] = last_name
    b['email'] = email
    return _post('/users/', b)
