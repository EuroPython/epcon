# -*- coding: UTF-8 -*-
from collections import defaultdict
from conference.models import Ticket, Speaker
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
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

def tickets_status(conf, code=None):
    orphan_tickets = _tickets(conf, 'conference')\
        .filter(p3_conference__isnull=False)\
        .exclude(p3_conference__assigned_to='')\
        .exclude(p3_conference__assigned_to__in=User.objects.values('email'))
    multiple_assignments = _tickets(conf, 'conference')\
        .exclude(Q(p3_conference=None)|Q(p3_conference__assigned_to=''))\
        .values('p3_conference__assigned_to')\
        .annotate(total=Count('id'))\
        .filter(total__gt=1)
    sim_tickets = _tickets(conf, fare_code='SIM%')\
        .filter(Q(p3_conference_sim=None)|Q(name='')|Q(p3_conference_sim__document=''))\
        .select_related('p3_conference_sim')
    if code is None:
        output = [
            {
                'id': 'ticket_sold',
                'title': 'Venduti',
                'total': _tickets(conf, 'conference').count(),
            },
            {
                'title': 'Compilati',
                'total': _compiled(conf).count(),
            },
            {
                'id': 'not_compiled',
                'title': 'Non compilati',
                'total': _not_compiled(conf).count(),
            },
            {
                'id': 'sim_tickets',
                'title': 'SIM non compilati',
                'total': sim_tickets.count(),
            },
        ]

        qs = _tickets(conf, 'conference')\
            .exclude(Q(p3_conference=None)|Q(p3_conference__assigned_to=''))
        output.append({
            'title': 'Biglietti assegnati',
            'total': qs.count(),
        })

        output.append({
            'id': 'multiple_assignments',
            'title': 'Biglietti multipli assegnati alla stessa persona',
            'total': multiple_assignments.count(),
        })

        output.append({
            'id': 'orphan_tickets',
            'title': 'Biglietti assegnati orfani',
            'total': orphan_tickets.count(),
        })
    else:
        if code in ('ticket_sold', 'not_compiled'):
            output = {
                'columns': (
                    ('name', 'Name'),
                    ('email', 'Email'),
                    ('buyer', 'Buyer'),
                    ('buyer_email', 'Buyer Email'),
                ),
                'data': [],
            }
            if code == 'ticket_sold':
                qs = _tickets(conf, 'conference')
            else:
                qs = _not_compiled(conf)
            qs = qs.select_related('p3_conference', 'user')
            assignees = dict([
                (u.email, u) for u in User.objects\
                    .filter(email__in=qs\
                        .exclude(p3_conference__assigned_to='')\
                        .values('p3_conference__assigned_to'))])
            data = output['data']
            for x in qs:
                # p3_conference può essere None perché viene costruito lazy al
                # primo salvataggio del biglietto.
                if x.p3_conference and x.p3_conference.assigned_to:
                    email = x.p3_conference.assigned_to
                    u = assignees.get(email)
                else:
                    email = x.user.email
                    u = x.user
                if u:
                    name = '<a href="%s">%s %s</a>' % (
                        reverse('admin:auth_user_change', args=(u.id,)),
                        u.first_name,
                        u.last_name)
                    order = u.first_name + u.last_name
                else:
                    name = '%s <strong>Biglietto orfano</strong>' % x.name
                    order = x.name
                if x.user == u:
                    buyer = ''
                else:
                    buyer = '<a href="%s">%s %s</a>' % (
                        reverse('admin:auth_user_change', args=(x.user.id,)),
                        x.user.first_name,
                        x.user.last_name)
                    if not order:
                        order = x.user.first_name + x.user.last_name
                if x.user.email == email:
                    buyer_email = ''
                else:
                    buyer_email = x.user.email
                row = {
                    'name': name,
                    'email': email,
                    'buyer': buyer,
                    'buyer_email': buyer_email,
                    '_order': order,
                    'uid': (u or x.user).id,
                }
                data.append(row)
            data.sort(key=lambda x: x['_order'])
        elif code in ('orphan_tickets', 'multiple_assignments'):
            output = {
                'columns': (
                    ('name', 'Name'),
                    ('email', 'Email'),
                    ('fare', 'Fare code'),
                    ('buyer', 'Buyer'),
                    ('buyer_email', 'Buyer Email'),
                ),
                'data': [],
            }
            if code == 'orphan_tickets':
                qs = orphan_tickets
            else:
                qs = _tickets(conf, 'conference')\
                    .filter(p3_conference__assigned_to__in=multiple_assignments\
                        .values('p3_conference__assigned_to'))
            qs = qs.select_related('p3_conference', 'user', 'fare')
            data = output['data']
            for x in qs:
                buyer = '<a href="%s">%s %s</a>' % (
                    reverse('admin:auth_user_change', args=(x.user.id,)),
                    x.user.first_name,
                    x.user.last_name)
                data.append({
                    'name': x.name,
                    'email': x.p3_conference.assigned_to,
                    'fare': x.fare.code,
                    'buyer': buyer,
                    'buyer_email': x.user.email,
                })
        elif code in ('sim_tickets',):
            output = {
                'columns': (
                    ('name', 'Name'),
                    ('email', 'Email'),
                    ('fare', 'Fare code'),
                ),
                'data': [],
            }
            if code == 'sim_tickets':
                qs = sim_tickets
            qs = qs.select_related('user', 'fare')
            data = output['data']
            for x in qs:
                buyer = '<a href="%s">%s %s</a>' % (
                    reverse('admin:auth_user_change', args=(x.user.id,)),
                    x.user.first_name,
                    x.user.last_name)
                data.append({
                    'name': buyer,
                    'email': x.user.email,
                    'fare': x.fare.code,
                    'uid': x.user.id,
                })
    return output
tickets_status.short_description = 'Statistiche biglietti'

def speaker_status(conf, code=None):
    t = _tickets(conf, 'conference')
    spk_noticket = Speaker.objects.byConference(conf)\
        .exclude(user__in=t.values('user'))\
        .exclude(user__email__in=t.extra(where=["assigned_to!=''"]).values('p3_conference__assigned_to'))
    spk_nodata = Speaker.objects.byConference(conf)\
        .filter(Q(
                user__attendeeprofile__image='',
                user__attendeeprofile__p3_profile__image_gravatar=False,
                user__attendeeprofile__p3_profile__image_url='')
            | Q(user__attendeeprofile__bios__language=None)
            | Q(
                user__attendeeprofile__bios__language='en',
                user__attendeeprofile__bios__content='bios',
                user__attendeeprofile__bios__body='')
            )
    if code is None:
        output = {
            'columns': (
                ('total', 'Total'),
                ('note', 'Note'),
            ),
            'data': [
                {
                    'id': 'no_ticket',
                    'title': 'Senza biglietto',
                    'total': spk_noticket.count(),
                    'note': '',
                },
                {
                    'id': 'no_data',
                    'title': 'Senza avatar o biografia',
                    'total': spk_nodata.count(),
                    'note': 'Non vengono inclusi gli utenti con gravatar (ma l\'avatar potrebbe non essere significativo)',
                }
            ]
        }
    else:
        if code == 'no_ticket':
            qs = spk_noticket
        elif code == 'no_data':
            qs = spk_nodata
        output = {
            'columns': (
                ('name', 'Name'),
                ('email', 'Email'),
            ),
            'data': [],
        }
        data = output['data']
        qs = qs\
            .select_related('user')\
            .order_by('user__first_name', 'user__last_name')
        for x in qs:
            data.append({
                'name': '<a href="%s">%s %s</a>' % (
                    reverse('admin:auth_user_change', args=(x.user_id,)),
                    x.user.first_name,
                    x.user.last_name),
                'email': x.user.email,
                'uid': x.user_id,
            })
    return output
speaker_status.short_description = 'Statistiche speaker'

def hotel_tickets(conf, code=None):
    qs = {}
    for x in ('1', '2', '3', '4'):
        qs['HR' + x] = User.objects.filter(
            id__in=_tickets(conf, fare_code='HR' + x).values('orderitem__order__user__user'))
    for x in ('2', '3', '4'):
        qs['HB' + x] = User.objects.filter(
            id__in=_tickets(conf, fare_code='HB' + x).values('orderitem__order__user__user'))
    if code is None:
        output = [
            {
                'id': 'HR1',
                'title': 'Camere singole',
                'total': qs['HR1'].count(),
            },
            {
                'id': 'HR2',
                'title': 'Camere doppie',
                'total': qs['HR2'].count(),
            },
            {
                'id': 'HR3',
                'title': 'Camere triple',
                'total': qs['HR3'].count(),
            },
            {
                'id': 'HR4',
                'title': 'Camere quadruple',
                'total': qs['HR4'].count(),
            },
            {
                'id': 'HB2',
                'title': 'Posto letto in doppia',
                'total': qs['HB2'].count(),
            },
            {
                'id': 'HB3',
                'title': 'Posto letto in tripla',
                'total': qs['HB3'].count(),
            },
            {
                'id': 'HB3',
                'title': 'Posto letto in quadruple',
                'total': qs['HB3'].count(),
            },
        ]
    else:
        output = {
            'columns': (
                ('name', 'Name'),
                ('email', 'Email'),
            ),
            'data': [],
        }
        data = output['data']
        for x in qs[code]:
            data.append({
                'name': '<a href="%s">%s %s</a>' % (
                    reverse('admin:auth_user_change', args=(x.id,)),
                    x.first_name,
                    x.last_name),
                'email': x.email,
                'uid': x.id,
            })

    return output

hotel_tickets.short_description = 'Biglietti hotel'
