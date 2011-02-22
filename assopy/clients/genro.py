# -*- coding: UTF-8 -*-
from assopy import settings
from assopy.clients.gnrbag import Bag

from lxml import objectify

import logging
import urllib
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

def user_local2remote(user):
    assert user.assopy_id is not None
    o = user_data(user.assopy_id)

    log.info('user local2remote %s -> %s', user.user.email, user.assopy_id)
    data = dict(o)
    data['firstname'] = user.user.first_name
    data['lastname'] = user.user.last_name
    data['www'] = user.www
    data['phone'] = user.phone
    data['card_name'] = user.card_name
    data['is_company'] = user.account_type == 'c'
    data['vat_number'] = user.vat_number
    data['tin_number'] = user.cf_number
    data['country'] = user.country_id
    data['zip'] = user.zip_code
    data['address'] = user.address
    data['city'] = user.city
    data['state'] = user.sate

    if data != o:
        set_user_data(user.assopy_id, data)
    return user

def user_remote2local(user):
    assert user.assopy_id is not None
    data = user_data(user.assopy_id)

    log.info('user remote2local %s -> %s', user.assopy_id, user.user.email)
    g = lambda k: (data.get(k) or '').strip()
    user.user.first_name = g('firstname')
    user.user.last_name = g('lastname')
    user.user.save()
    user.www = g('www')
    user.phone = g('phone')
    user.card_name = g('card_name')
    user.account_type = 'c' if data.get('is_company') else 'p'
    user.vat_number = g('vat_number')
    user.cf_number = g('tin_number')

    from assopy.models import Country
    try:
        country = Country.objects.get(pk=data['country'])
    except Country.DoesNotExist:
        country = None
    user.country = country
    user.zip_code = g('zip')
    user.address = g('address')
    user.city = g('city')
    user.provincia = g('state')
    user.save()
    return user

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

def user_data(id):
    return _get('/users/%s' % id)   

def set_user_data(id, data):
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
    b['event'] = rows[0].ticket.fare.conference_id
    b['customer_id'] = order.user.assopy_id
    #b['coupon'] = 
    #b['discount'] = 
    b['payment_method'] = o.method
    items = {}
    for r in rows:
        fcode = r.ticket.fare.code
        if fcode not in items:
            x = Bag()
            x['quantity'] = 1
            x['fare_code'] = fcode
            items[fcode] = x
        else:
            items[fcode]['quantity'] += 1
    b['order_rows'] = items.values()
    result = _post('/orders/', b)
    o.assopy_id = result['order_id']
    o.code = result['order_code']
    o.save()
    return result['paypal_url']
