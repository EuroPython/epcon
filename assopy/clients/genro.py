# -*- coding: UTF-8 -*-
from assopy import settings

from lxml import objectify

import urllib

def _get(subpath):
    url = settings.BACKEND + subpath
    f = urllib.urlopen(url)
    return objectify.fromstring(f.read())

def user(id):
    return _get('/users/%s' % id)   

