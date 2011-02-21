# -*- coding: UTF-8 -*-
from assopy import settings
from assopy.clients.gnrbag import Bag

from lxml import objectify

import logging
import urllib
from collections import defaultdict
from urlparse import urlparse, urlunparse

log = logging.getLogger('assopy.genro')

_url = urlparse(settings.BACKEND)

def _build(path, query=None):
    splitted = list(_url)
    if not path.startswith('/'):
        path = '/' + path
    splitted[2] = (splitted[2] + path).replace('//', '/')
    if query:
        splitted[4] = urllib.urlencode(query)
    return urlunparse(splitted)

def _get(subpath, **kwargs):
    url = _build(subpath, kwargs)
    log.debug('get -> %s', url)
    f = urllib.urlopen(url)
    b = Bag()
    b.fromXml(f.read())
    return b

def _post(subpath, bag=None):
    url = settings.BACKEND + subpath
    log.debug('post -> %s', url)
    body = {}
    if bag is not None:
        body['data'] = bag.toXml()
    f = urllib.urlopen(url, urllib.urlencode(body))
    b = Bag()
    b.fromXml(f.read())
    return b

def users(email, password=None):
    """
    restituisce gli id degli utenti remoti che hanno l'email passata
    """
    p = {
        'email': email,
    }
    if password is not None:
        p['password'] = password
    return _get('/users/', **p)

def user(id):
    return _get('/users/%s' % id)   

def setUser(id, data):
    return _post('/users/%s' % id, Bag(data))

def create_user(firstname, lastname, email):
    b = Bag()
    b['firstname'] = firstname
    b['lastname'] = lastname
    b['email'] = email
    return _post('/users/', b)['id']

def create_order(order):
    b = Bag()
    assert order.user.assopy_id
    rows = list(order.orderitem_set.select_related('ticket__fare'))
    b['event'] = rows[0].ticket.fare.conference
    b['customer_id'] = order.user.assopy_id
    #b['coupon'] = 
    #b['discount'] = 
    b['payment_method'] = order.method

    tickets = defaultdict(lambda: 0)
    for r in rows:
        tickets[r.ticket.fare.code] += 1
    for ix, t in enumerate(tickets):
        b['order_rows.r%s.fare_code' % ix] = t
        b['order_rows.r%s.quantity' % ix] = tickets[t]
    result = _post('/orders/', b)
    o.assopy_id = result['order_id']
    o.code = result['order_code']
    o.save()
    return result['paypal_url']
