# -*- coding: UTF-8 -*-
from django.conf import settings
from django.db.models import Count, Q

from conference.models import Conference, Ticket
from p3 import models

import datetime
import os.path
from collections import defaultdict

def conference_stats(conference, stat=None):
    stats = []
    tickets = Ticket.objects.filter(
        orderitem__order___complete=True,
        fare__ticket_type='conference',
        fare__conference=conference,
    ).select_related('p3_conference', 'orderitem__order__user__user')
    compiled = tickets.exclude(p3_conference=None).exclude(name='')
    not_compiled = tickets.exclude(p3_conference=None).filter(name='') | tickets.filter(p3_conference=None)
    if stat in (None, 'all'):
        stats.append({
            'code': 'all',
            'title': 'Biglietti venduti',
            'count': tickets.count(),
            'have_details': True,
            'details': tickets,
        })
    if stat in (None, 'not_compiled'):
        stats.append({
            'code': 'not_compiled',
            'title': 'Biglietti non compilati',
            'count': not_compiled.count(),
            'have_details': True,
            'details': not_compiled,
        })
    if stat in (None, 'compiled'):
        stats.append({
            'code': 'compiled',
            'title': 'Biglietti compilati',
            'count': compiled.count(),
            'have_details': True,
            'details': compiled,
        })
    if stat is None or stat.startswith('tshirt_'):
        sizes = dict(models.TICKET_CONFERENCE_SHIRT_SIZES)
        for x in compiled.values('p3_conference__shirt_size').annotate(c=Count('id')):
            scode = 'tshirt_%s' % x['p3_conference__shirt_size']
            if stat in (None, scode):
                stats.append({
                    'code': scode,
                    'title': 'Taglia maglietta: %s' % sizes.get(x['p3_conference__shirt_size']),
                    'count': x['c'], 
                    'have_details': True,
                    'details': compiled.filter(p3_conference__shirt_size=x['p3_conference__shirt_size']),
                })
    if stat is None or stat.startswith('diet_'):
        diets = dict(models.TICKET_CONFERENCE_DIETS)
        for x in compiled.values('p3_conference__diet').annotate(c=Count('id')):
            scode = 'diet_%s' % x['p3_conference__diet']
            if stat in (None, scode):
                stats.append({
                    'code': scode,
                    'title': 'Dieta: %s' % diets.get(x['p3_conference__diet']),
                    'count': x['c'], 
                    'have_details': True,
                    'details': compiled.filter(p3_conference__diet=x['p3_conference__diet']),
                })
    if stat is None or stat.startswith('days_'):
        days = defaultdict(lambda: 0)
        for x in compiled:
            data = filter(None, map(lambda x: x.strip(), x.p3_conference.days.split(',')))
            if not data:
                days['x'] += 1
            else:
                for v in data:
                    days[v] += 1
        compiled_count = compiled.count()
        not_compiled_count = not_compiled.count()
        for day, count in days.items():
            scode = 'days_%s' % day
            if stat in (None, scode):
                if day != 'x':
                    info = float(count) / (compiled_count - days['x']) * (compiled_count + not_compiled_count)
                else:
                    info = 0.0
                stats.append({
                    'code': scode,
                    'title': 'Giorno di presenza: %s' % day,
                    'count': count,
                    'have_details': False,
                    'additional_info': info,
                })

    if stat in (None, 'sim_not_compiled'):
        tickets = Ticket.objects.filter(
            orderitem__order___complete=True,
            fare__code__startswith='SIM',
            fare__conference=conference,
        ).select_related('p3_conference_sim', 'orderitem__order__user__user')
        qs = tickets.exclude(p3_conference_sim=None).filter(Q(name='')|Q(p3_conference_sim__document='')) | tickets.filter(p3_conference_sim=None)
        stats.append({
            'code': 'sim_not_compiled',
            'title': 'Biglietti SIM non completi',
            'count': qs.count(),
            'have_details': True,
            'details': qs,
        })
    return stats

def conference_ticket_badge(tickets):
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
                'args': ['-c', os.path.join(settings.OTHER_STUFF, 'badge', t.fare.conference, 'conf.py'), ],
                'tickets': []
            }
        if t.p3_conference is None:
            tagline = ''
            days = '1'
            experience = 0
        else:
            tagline = t.p3_conference.tagline
            experience = t.p3_conference.python_experience
            tdays = map(lambda x: datetime.date(*map(int, x.split('-'))), filter(None, t.p3_conference.days.split(',')))
            cdays = conferences[t.fare.conference]['days']
            days = ','.join(map(str,[cdays.index(x)+1 for x in tdays]))
        groups[t.fare.conference]['tickets'].append({
            'name': t.name or t.orderitem.order.user.name(),
            'tagline': tagline,
            'days': days,
            'fare': {
                'code': t.fare.code,
                'type': t.fare.recipient_type,
            },
            'experience': experience,
            'staff': t.ticket_type == 'staff',
        })
    return groups.values()
