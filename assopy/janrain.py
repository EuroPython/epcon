# -*- coding: UTF-8 -*-
import json
import logging
import random
import re
import urllib

log = logging.getLogger('assopy.janrain')

BASE = 'https://rpxnow.com/api/v2/'

class JanRainException(Exception):
    pass

def _request(method, params):
    url = BASE + method
    log.debug('call %s', url)

    # supportiamo solo json
    params = dict(params)
    params['format'] = 'json'
    r = urllib.urlopen(url, urllib.urlencode(params))
    message = r.read()
    try:
        data = json.loads(message)
    except ValueError:
        log.warn('malformed response from janrain, not a json: message=%s', message)
        raise JanRainException(-10, '')
    try:
        stat = data['stat']
    except KeyError:
        log.warn('malformed response from janrain: message=%s', message)
        raise JanRainException(-10, '')
    if stat == 'fail':
        log.warn('call failed: err=%s', r.read())
        raise JanRainException(data['err']['code'], data['err']['msg'])
    return data

def auth_info(api_key, token):
    params = {
        'apiKey': api_key,
        'token': token,
    }
    return _request('auth_info', params)['profile']

def _valid_username(u):
    from django.contrib import auth
    try:
        auth.models.User.objects.get(username=u)
    except auth.models.User.DoesNotExist:
        return True
    else:
        return False

def suggest_username_from_email(email):
    try:
        # Prendo le prime due iniziali dello username dell'email
        prefix = ''.join(( x[0] for x in re.split(r'\W|_', email.split('@')[0]) if x ))[:2]
    except KeyError:
        prefix = 'xx'

    while True:
        uname = prefix + str(random.randint(1, 99999)).zfill(5)
        if _valid_username(uname):
            return uname

def suggest_username(profile):
    """
    suggerisce uno username da usare per creare l'utente django che verrà
    associato al profilo
    """
    # lo username in django può essere al max 30 caratteri; se il profilo
    # suggerisce un preferredUsername utilizzo il suo valore come prima
    # opzione, altrimenti provo a derivarne uno dall'email (paddandola con un
    # numero random)
    try:
        uname = profile['preferredUsername'][:30]
    except KeyError:
        uname = None

    if uname is not None and _valid_username(uname):
        return uname

    return suggest_username_from_email(profile.get('email', 'nomail@example.com'))
