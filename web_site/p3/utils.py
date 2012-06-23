# -*- coding: UTF-8 -*-
from collections import defaultdict
from conference.models import Conference
import datetime
from django.conf import settings
from django.core.urlresolvers import reverse
import os.path

def conference_ticket_badge(tickets):
    """
    vedi conference.settings.TICKET_BADGE_PREPARE_FUNCTION
    """
    conferences = {}
    for c in Conference.objects.all():
        conferences[c.code] = {
            'obj': c,
            'days': c.days(),
        }
    groups = {}
    qs = tickets\
            .filter(orderitem__order___complete=True)\
            .select_related('fare', 'p3_conference', 'orderitem__order__user__user')
    for t in qs:
        if t.fare.conference not in groups:
            groups[t.fare.conference] = {
                'plugin': os.path.join(settings.OTHER_STUFF, 'badge', t.fare.conference, 'conf.py'),
                'tickets': [],
            }
        p3c = t.p3_conference
        if p3c is None:
            tagline = ''
            days = '1'
            experience = 0
            badge_image = None
        else:
            tagline = p3c.tagline
            experience = p3c.python_experience
            tdays = map(lambda x: datetime.date(*map(int, x.split('-'))), filter(None, p3c.days.split(',')))
            cdays = conferences[t.fare.conference]['days']
            days = ','.join(map(str,[cdays.index(x)+1 for x in tdays]))
            badge_image = p3c.badge_image.path if p3c.badge_image else None
        groups[t.fare.conference]['tickets'].append({
            'name': t.name or t.orderitem.order.user.name(),
            'tagline': tagline,
            'days': days,
            'fare': {
                'code': t.fare.code,
                'type': t.fare.recipient_type,
            },
            'experience': experience,
            'badge_image': badge_image,
            'staff': t.ticket_type == 'staff',
        })
    return groups.values()

def gravatar(email, size=80, default='identicon', rating='r', protocol='https'):
    import urllib, hashlib

    if protocol == 'https':
        host = 'https://secure.gravatar.com'
    else:
        host = 'http://www.gravatar.com'
    gravatar_url = host + "/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode({
        'default': default,
        'size': size,
        'rating': rating,
    })
    return gravatar_url


from django.core.cache import cache
from django.utils.http import urlquote
from django.utils.hashcompat import md5_constructor

def template_cache_name(fragment_name, *variables):
    args = md5_constructor(u':'.join([urlquote(var) for var in variables]))
    return 'template.cache.%s.%s' % (fragment_name, args.hexdigest())

def invalidate_template_cache(fragment_name, *variables):
    args = md5_constructor(u':'.join([urlquote(var) for var in variables]))
    cache_key = 'template.cache.%s.%s' % (fragment_name, args.hexdigest())
    cache.delete(cache_key)
    return

def conference2ical(conf, user=None, abstract=False):
    from conference import dataaccess
    from conference import models as cmodels
    from datetime import timedelta

    curr = cmodels.Conference.objects.current()
    try:
        hotel = cmodels.SpecialPlace.objects.get(type='conf-hq')
    except cmodels.SpecialPlace.DoesNotExist:
        hotel = None
    else:
        if not hotel.lat or not hotel.lng:
            hotel = None

    def altf(data, component):
        if component == 'calendar':
            if user is None:
                url = reverse('p3-schedule', kwargs={'conference': conf})
            else:
                url = reverse('p3-schedule-my-schedule', kwargs={'conference': conf})
            data['uid'] = settings.DEFAULT_URL_PREFIX + url
            if curr.code == conf:
                data['ttl'] = timedelta(seconds=3600)
            else:
                data['ttl'] = timedelta(days=365)
        elif component == 'event':
            eid = data['uid']
            data['uid'] = settings.DEFAULT_URL_PREFIX + '/p3/event/' + str(data['uid'])
            data['organizer'] = ('mailto:info@pycon.it', {'CN': 'Python Italia'})
            if hotel:
                data['coordinates'] = [hotel.lat, hotel.lng]
            if not isinstance(data['summary'], tuple):
                # questo è un evento custom, se inizia con un anchor posso
                # estrane il riferimento
                import re
                m = re.match(r'<a href="(.*)">(.*)</a>', data['summary'])
                if m:
                    url = m.group(1)
                    if url.startswith('/'):
                        url = settings.DEFAULT_URL_PREFIX + url
                    data['summary'] = (m.group(2), {'ALTREP': url})
            if abstract:
                e = dataaccess.event_data(eid)
                ab = e['talk']['abstract'] if e['talk'] else e['abstract']
                data['description'] = ab
        return data
    if user is None:
        from conference.utils import conference2ical as f
        cal = f(conf, altf=altf)
    else:
        from conference.utils import TimeTable2
        from conference.utils import timetables2ical as f

        qs = cmodels.Event.objects\
            .filter(eventinterest__user=user, eventinterest__interest__gt=0)\
            .filter(schedule__conference=conf)\
            .values('id', 'schedule')

        events = defaultdict(list)
        for x in qs:
            events[x['schedule']].append(x['id'])

        sids = sorted(events.keys())
        timetables = [ TimeTable2.fromEvents(x, events[x]) for x in sids ]
        cal = f(timetables, altf=altf)
    return cal
