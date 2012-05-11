# -*- coding: UTF-8 -*-
from collections import defaultdict
from conference.models import Ticket, Speaker
from django.db.models import Q, Count
from p3 import models

def _tickets(conf, ticket_type=None, fare_code=None):
    qs = Ticket.objects\
        .filter(
            orderitem__order___complete=True,
            fare__conference=conf,
        )
    if ticket_type:
        qs = qs.filter(fare__ticket_type=ticket_type)
    if fare_code:
        if fare_code.endswith('%'):
            qs = qs.filter(fare__code__startswith=fare_code[:-1])
        else:
            qs = qs.filter(fare__code=fare_code)
    return qs

def _compiled(conf, ticket_type='conference'):
    return _tickets(conf, ticket_type)\
        .exclude(p3_conference=None)\
        .exclude(name='')

def _not_compiled(conf, ticket_type='conference'):
    return _tickets(conf, ticket_type)\
        .filter(Q(p3_conference=None)|Q(name=''))

def shirt_sizes(conf):
    sizes = dict(models.TICKET_CONFERENCE_SHIRT_SIZES)
    qs = _compiled(conf)\
        .values('p3_conference__shirt_size')\
        .annotate(total=Count('id'))

    output = []
    for x in qs:
        output.append({
            'title': sizes.get(x['p3_conference__shirt_size']),
            'total': x['total'],
        })
    return output
shirt_sizes.short_description = "Taglie maglette (solo biglietti compilati)"

def diet_types(conf):
    diets = dict(models.TICKET_CONFERENCE_DIETS)
    qs = _compiled(conf)\
        .values('p3_conference__diet')\
        .annotate(total=Count('id'))

    output = []
    for x in qs:
        output.append({
            'title': diets.get(x['p3_conference__diet']),
            'total': x['total'],
        })
    return output
diet_types.short_description = "Dieta partecipanti (solo biglietti compilati)"

def presence_days(conf):
    totals = {
        'c': _compiled(conf).count(),
        'n': _not_compiled(conf).count(),
    }
    output = {
        'columns': (
            ('total', 'Totale'),
            ('total_nc', '<span title="Considerando i non completi">Proiezione NC</span>'),
        ),
        'data': [],
    }

    days = defaultdict(lambda: 0)
    qs = _compiled(conf)\
        .values_list('p3_conference__days', flat=True)
    for x in qs:
        val = filter(None, map(lambda v: v.strip(), x.split(',')))
        if not val:
            days['x'] += 1
        else:
            for v in val:
                days[v] += 1

    for day, count in sorted(days.items()):
        if day != 'x':
            nc = float(count) / (totals['c'] - days['x']) * (totals['c'] + totals['n'])
        else:
            nc = 0.0
        output['data'].append({
            'title': day,
            'total': count,
            'total_nc': int(round(nc)),
        })
    return output
presence_days.short_description = "Affluenza per giorno (solo biglietti compilati)"

def tickets_status(conf):
    output = [
        {
            'title': 'Venduti',
            'total': _tickets(conf, 'conference').count(),
        },
        {
            'title': 'Compilati',
            'total': _compiled(conf).count(),
        },
        {
            'title': 'Non compilati',
            'total': _not_compiled(conf).count(),
        }
    ]
    qs = _tickets(conf, fare_code='SIM%')\
        .filter(Q(p3_conference_sim=None)|Q(name='')|Q(p3_conference_sim__document=''))\
        .select_related('p3_conference_sim')
    output.append({
        'title': 'SIM non compilati',
        'total': qs.count(),
    })
    return output
tickets_status.short_description = 'Statistiche biglietti'

def speaker_status(conf, code=None):
    t = _tickets(conf, 'conference')
    spk = Speaker.objects.byConference(conf)\
        .exclude(
            user__in=t.values('user'),
            user__email__in=t.values('p3_conference__assigned_to'))
    if code is None:
        output = {
            'columns': (
                ('total', 'Total'),
            ),
            'data': [
                {
                    'id': 'no_ticket',
                    'title': 'Senza biglietto',
                    'total': spk.count(),
                }
            ]
        }
    elif code == "no_ticket":
        output = {
            'columns': (
                ('name', 'Name'),
                ('email', 'Email'),
            ),
            'data': [],
        }
        data = output['data']
        spk = spk\
            .select_related('user')\
            .order_by('user__first_name', 'user__last_name')
        for x in spk.select_related('user'):
            data.append({
                'name': '%s %s' % (x.user.first_name, x.user.last_name),
                'email': x.user.email,
            })
    return output
speaker_status.short_description = 'Statistiche speaker'
