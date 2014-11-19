# -*- coding: UTF-8 -*-
import datetime
import os.path
from collections import defaultdict
from conference.models import Conference, AttendeeProfile
from django.conf import settings
from django.core.urlresolvers import reverse

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
            .select_related('fare', 'p3_conference', 'orderitem__order__user__user')
    for t in qs:
        if t.fare.conference not in groups:
            groups[t.fare.conference] = {
                'name': t.fare.conference,
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
        if p3c and p3c.assigned_to:
            profile = AttendeeProfile.objects\
                        .select_related('user')\
                        .get(user__email=p3c.assigned_to)
        else:
            profile = t.user.attendeeprofile
        name = t.name.strip()
        if not name:
            if profile.user.first_name or profile.user.last_name:
                name = '%s %s' % (profile.user.first_name, profile.user.last_name)
            else:
                name = t.orderitem.order.user.name()
                if p3c and p3c.assigned_to:
                    name = p3c.assigned_to + ' (%s)' % name
        groups[t.fare.conference]['tickets'].append({
            'name': name,
            'tagline': tagline,
            'days': days,
            'fare': {
                'code': t.fare.code,
                'type': t.fare.recipient_type,
            },
            'experience': experience,
            'badge_image': badge_image,
            'staff': t.ticket_type == 'staff',
            'profile-link': settings.DEFAULT_URL_PREFIX + reverse(
                'conference-profile-link', kwargs={'uuid': profile.uuid}),
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

def spam_recruiter_by_conf(conf):
    """
    Restituisce un queryset con gli User che hanno accettato di essere
    contattati via email per motivi di recruiting
    """
    from django.contrib.auth.models import User

    tickets = settings.CONFERENCE_TICKETS(conf, ticket_type='conference')
    owned = tickets.filter(p3_conference__assigned_to='')
    assigned = tickets.exclude(p3_conference__assigned_to='')

    first_run = User.objects\
        .filter(\
            id__in=owned.values('user'),\
            attendeeprofile__p3_profile__spam_recruiting=True)

    second_run = User.objects\
        .filter(\
            email__in=assigned.values('p3_conference__assigned_to'),\
            attendeeprofile__p3_profile__spam_recruiting=True)
    return first_run | second_run

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
                # this is a custom event, if it starts with an anchor I can
                # extract the reference
                import re
                m = re.match(r'<a href="(.*)">(.*)</a>', data['summary'])
                if m:
                    url = m.group(1)
                    if url.startswith('/'):
                        url = settings.DEFAULT_URL_PREFIX + url
                    data['summary'] = (m.group(2), {'ALTREP': url})
            if abstract:
                e = dataaccess.event_data(eid)
                if e['talk']:
                    from conference.templatetags.conference import name_abbrv
                    speakers = [ name_abbrv(s['name']) for s in e['talk']['speakers'] ]
                    speakers = ", ".join(speakers)
                    data['summary'] = (data['summary'][0] + ' by ' + speakers, data['summary'][1])
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

class RawSubquery(object):
    """
    An utility class to use a raw query as a subquery without incurring in the
    performance loss caused by evaluating the two queries independently.

    Given this raw query (rawq):

        SELECT t1.user_id
        FROM (
            ...
        ) t1 INNER JOIN (
            ...
        ) t2
            ON t1.something = t2.something_else

    You can write this:

    MyModel.objects.filter(id__in=RawSubquery(rawq))

    instead of:

    cursor = connection.cursor()
    data = [ x[0] for x in cursor.execute(rawq, []).fetchall() ]
    MyModel.objects.filter(id__in=data)
    """
    def __init__(self, raw, params=()):
        self.raw = raw
        self.params = params

    def prepare(self):
        return self

    def as_sql(self):
        return (self.raw, self.params)

