# -*- coding: UTF-8 -*-
from datetime import datetime

def encode(line):
    if isinstance(line, unicode):
        line = line.encode('utf-8')
    if not line.endswith('\r\n'):
        line += '\r\n'
    if len(line) > 75:
        fold = [ line ]
        while len(fold[-1]) > 75:
            l = fold[-1]
            fold[-1] = fold[-1][:73]
            fold.append(' ' + l[73:])
        line = '\r\n'.join(fold)
    return line

def content(name, value, params=None):
    if params:
        t = []
        for pname, pvalue in params.items():
            if ',' in pvalue or ';' in pvalue or ':' in pvalue:
                pvalue = '"%s"' % pvalue
            t.append('%s=%s' % (pname, pvalue))
        name += ';' + ';'.join(t)
    return encode('%s:%s' % (name, value))

def TEXT(value):
    if isinstance(value, unicode):
        value = value.encode('utf-8')
    elif not isinstance(value, str):
        value = str(value)
    return value\
        .replace('\\', '\\\\')\
        .replace('\n', '\\n')\
        .replace(';', '\\;')\
        .replace(',', '\\,')

def DATE_TIME(value):
    return  value.strftime('%Y%m%dT%H%M%S')

def FLOAT(value):
    return '%+.6f' % value

def DURATION(value):
    r = value.seconds
    h = r / 3600
    m = (r - (h * 3600)) / 60
    s = r - (h * 3600) - (m * 60)
    return 'P%sDT%sH%sM%sS' % (value.days, h, m, s)

def URI(value):
    return value
        
def Property(value, params=None, fmt=TEXT, property_values=1):
    if value is None:
        return None

    if isinstance(value, tuple):
        value, params = value

    if not isinstance(value, (tuple, list)):
        value = [ value ]

    if property_values > 0 and len(value) != property_values:
        raise ValueError("Invalid number of values")

    values = ','.join(map(fmt, value))
    return values, params

class Component(dict):
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.subcomponents = []
        super(Component, self).__init__(*args, **kwargs)

    def encode(self):
        yield content('BEGIN', self.name)
        for name, prop in self.items():
            if prop is None:
                continue
            value, params = prop
            yield content(name, value, params)
        for comp in self.subcomponents:
            for line in comp.encode():
                yield line
        yield content('END', self.name)

class Event(Component):
    def __init__(
        self,
        uid,
        start,
        end=None,
        duration=None,
        classification='PUBLIC',
        revised=None,
        summary=None,
        description=None,
        location=None,
        coordinates=None,
        organizer=None,
        url=None,
    ):
        assert not (end and duration)
        if revised is None:
            revised = datetime.now()
        d = {
            'UID': Property(uid, fmt=TEXT),
            'DTSTART': Property(start, fmt=DATE_TIME),
            'DTEND': Property(end, fmt=DATE_TIME),
            'DURATION': Property(duration, fmt=DURATION),
            'DTSTAMP': Property(revised, fmt=DATE_TIME),
            'CLASS': Property(classification, fmt=TEXT),
            'SUMMARY': Property(summary, fmt=TEXT),
            'DESCRIPTION': Property(description, fmt=TEXT),
            'GEO': Property(coordinates, fmt=FLOAT, property_values=2),
            'LOCATION': Property(location, fmt=TEXT),
            'URL': Property(url, fmt=URI),
            'ORGANIZER': Property(organizer, fmt=URI),
        }
        super(Event, self).__init__('VEVENT', d)

class Calendar(Component):
    def __init__(self, uid, events, ttl=None):
        d = {
            'VERSION': Property('2.0'),
            'PRODID': Property(uid),
            'X-PUBLISHED-TTL': Property(ttl, fmt=DURATION),
        }
        super(Calendar, self).__init__('VCALENDAR', d)
        self.subcomponents = events

