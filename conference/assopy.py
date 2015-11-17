import time
import httplib2
import simplejson

ASSOPYURL = 'http://assopy.pycon.it/conference/getinfo.py/'
CACHETIME = 5 * 60

_HTTP = httplib2.Http()
_CACHE = {}

def _get(url):
    now = time.time()
    try:
        timestamp, response = _CACHE[url]
    except KeyError:
        pass
    else:
        if now <= timestamp + CACHETIME:
            return response
    response = _HTTP.request(url)
    _CACHE[url] = time.time(), response
    
    return response

def attendeeCount():
    """
    Restituisce il numero di partecipanti al pycon
    """
    response, content = _get(ASSOPYURL + 'sold')
    try:
        return int(content)
    except (ValueError, TypeError):
        return -1

if __name__ == '__main__':
    print 'partecipanti', attendeeCount()
