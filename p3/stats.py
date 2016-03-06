# -*- coding: UTF-8 -*-
from collections import defaultdict
from conference.models import Ticket, Speaker, Talk
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Q, Count
from p3 import models
from conference import models as cmodels

def _tickets(conf, ticket_type=None, fare_code=None, only_complete=True):
    qs = Ticket.objects\
        .filter(fare__conference=conf)
    if only_complete:
        qs = qs.filter(orderitem__order___complete=True)
    else:
        qs = qs.filter(Q(orderitem__order___complete=True)|Q(orderitem__order__method='bank'))

    if ticket_type:
        qs = qs.filter(fare__ticket_type=ticket_type)
    if fare_code:
        if fare_code.endswith('%'):
            qs = qs.filter(fare__code__startswith=fare_code[:-1])
        else:
            qs = qs.filter(fare__code=fare_code)
    return qs

def _assigned_tickets(conf, ticket_type='conference'):
    return _tickets(conf, ticket_type)\
        .exclude(p3_conference=None)\
        .exclude(name='')\
        .exclude(p3_conference__assigned_to='')

def _unassigned_tickets(conf, ticket_type='conference', only_complete=True):
    return _tickets(conf, ticket_type, only_complete=only_complete)\
        .filter(Q(p3_conference=None)|Q(name='')|Q(p3_conference__assigned_to=''))

def shirt_sizes(conf):
    sizes = dict(models.TICKET_CONFERENCE_SHIRT_SIZES)
    qs = _assigned_tickets(conf)\
        .values('p3_conference__shirt_size')\
        .annotate(total=Count('id'))

    output = []
    for x in qs:
        output.append({
            'title': sizes.get(x['p3_conference__shirt_size']),
            'total': x['total'],
        })
    return output
shirt_sizes.short_description = "Tshirts size"

def diet_types(conf):
    diets = dict(models.TICKET_CONFERENCE_DIETS)
    qs = _assigned_tickets(conf)\
        .values('p3_conference__diet')\
        .annotate(total=Count('id'))

    output = []
    for x in qs:
        output.append({
            'title': diets.get(x['p3_conference__diet']),
            'total': x['total'],
        })
    return output
diet_types.short_description = "Diet"

def presence_days(conf, code=None):
    qs = {
        'all': {
            'c': _assigned_tickets(conf),
            'n': _unassigned_tickets(conf, only_complete=False),
        },
        'nostaff': {
            'c': _assigned_tickets(conf).exclude(ticket_type='staff'),
            'n': _unassigned_tickets(conf, only_complete=False).exclude(ticket_type='staff'),
        }
    }
    totals = {}
    for key in qs:
        totals[key] = {
            'c': qs[key]['c'].count(),
            'n': qs[key]['n'].count(),
        }
    output = {
        'columns': (
            ('total', 'Total'),
            ('total_nc', '<span title="Estimate with unassigned tickets and incomplete bank orders">Estimate with NA/NC</span>'),
        ),
        'data': [],
    }

    days = {
        'all': defaultdict(lambda: 0),
        'nostaff': defaultdict(lambda: 0),
    }
    for key in qs:
        for x in qs[key]['c'].values_list('p3_conference__days', flat=True):
            val = filter(None, map(lambda v: v.strip(), x.split(',')))
            if not val:
                days[key]['x'] += 1
            else:
                for v in val:
                    days[key][v] += 1

    for key in days:
        dX = days[key].get('x', 0)
        tC = totals[key]['c']
        tN = totals[key]['n']
        for day, count in sorted(days[key].items()):
            if day != 'x':
                nc = float(count) / (tC - dX) * (tC + tN)
            else:
                nc = 0.0
            title = day
            if key == 'nostaff':
                title += ' (no staff)'
            output['data'].append({
                'title': title,
                'total': count,
                'total_nc': int(round(nc)),
            })
    return output
presence_days.short_description = "Conference attendance"

def tickets_status(conf, code=None):
    orphan_tickets = _tickets(conf, 'conference')\
        .filter(p3_conference__isnull=False)\
        .exclude(p3_conference__assigned_to='')\
        .exclude(p3_conference__assigned_to__in=User.objects.values('email'))
    multiple_assignments = _assigned_tickets(conf, 'conference')\
        .values('p3_conference__assigned_to')\
        .annotate(total=Count('id'))\
        .filter(total__gt=1)
    sim_tickets = _tickets(conf, fare_code='SIM%')\
        .filter(Q(p3_conference_sim=None)|Q(name='')|Q(p3_conference_sim__document=''))\
        .select_related('p3_conference_sim')
    voupe03 = _tickets(conf, fare_code='VOUPE03')
    from p3.utils import spam_recruiter_by_conf
    spam_recruiting = spam_recruiter_by_conf(conf)
    if code is None:
        output = [
            {
                'id': 'ticket_sold',
                'title': 'Sold tickets',
                'total': _tickets(conf, 'conference').count(),
            },
            {
                'id': 'assigned_tickets',
                'title': 'Assigned tickets',
                'total': _assigned_tickets(conf).count(),
            },
            {
                'id': 'unassigned_tickets',
                'title': 'Unassigned tickets',
                'total': _unassigned_tickets(conf).count(),
            },
            {
                'id': 'sim_tickets',
                'title': 'Tickets with SIM card orders',
                'total': sim_tickets.count(),
            },
            {
                'id': 'voupe03_tickets',
                'title': 'Social event tickets (VOUPE03)',
                'total': voupe03.count(),
            },
            {
                'id': 'spam_recruiting',
                'title': 'Recruiting emails (opt-in)',
                'total': spam_recruiting.count(),
            },
        ]

        # MAL: This looks like a duplicate of the above row
        #
        # qs = _tickets(conf, 'conference')\
        #     .exclude(Q(p3_conference=None)|Q(p3_conference__assigned_to=''))
        # output.append({
        #     'title': 'Assigned tickets',
        #     'total': qs.count(),
        # })

        output.append({
            'id': 'multiple_assignments',
            'title': 'Tickets assigned to the same person',
            'total': multiple_assignments.count(),
        })

        output.append({
            'id': 'orphan_tickets',
            'title': 'Assigned tickets without user record (orphaned)',
            'total': orphan_tickets.count(),
        })

    else:
        if code in ('ticket_sold',
                    'assigned_tickets',
                    'unassigned_tickets',
                    'multiple_assignments',
                    ):
            output = {
                'columns': (
                    ('ticket', 'Ticket'),
                    ('name', 'Attendee name'),
                    ('email', 'Email'),
                    ('fare', 'Fare code'),
                    ('buyer', 'Buyer'),
                    ('buyer_email', 'Buyer Email'),
                ),
                'data': [],
            }
            if code == 'ticket_sold':
                qs = _tickets(conf, 'conference')
            elif code == 'assigned_tickets':
                qs = _assigned_tickets(conf)
            elif code == 'unassigned_tickets':
                qs = _unassigned_tickets(conf)
            elif code == 'multiple_assignments':
                qs = _tickets(conf, 'conference')\
                    .filter(p3_conference__assigned_to__in=multiple_assignments\
                        .values('p3_conference__assigned_to'))
            else:
                raise ValueError('Unsupported stats code: %r' % code)
            qs = qs.select_related('p3_conference', 'user')
            assignees = dict([
                (u.email, u) for u in User.objects\
                    .filter(email__in=qs\
                        .exclude(p3_conference__assigned_to='')\
                        .values('p3_conference__assigned_to'))])
            data = output['data']
            for x in qs:
                ticket = '<a href="%s">%s</a>' % (
                    reverse('admin:conference_ticket_change', args=(x.id,)),
                    x.id)
                # p3_conference can be None because it's filled lazily when
                # the ticket is saved for the first time
                try:
                    x.p3_conference
                except models.TicketConference.DoesNotExist:
                    continue
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
                    name = '%s <strong>Ticket not assigned</strong>' % x.name
                    order = x.name
                buyer = '<a href="%s">%s %s</a>' % (
                    reverse('admin:auth_user_change', args=(x.user.id,)),
                    x.user.first_name,
                    x.user.last_name)
                if not order:
                    order = x.user.first_name + x.user.last_name
                buyer_email = x.user.email
                row = {
                    'ticket': ticket,
                    'name': name,
                    'email': email,
                    'fare': x.fare.code,
                    'buyer': buyer,
                    'buyer_email': buyer_email,
                    '_order': order,
                    'uid': (u or x.user).id,
                }
                data.append(row)
            data.sort(key=lambda x: x['_order'])

        elif code in ('orphan_tickets',
                      ):
            output = {
                'columns': (
                    ('ticket', 'Ticket'),
                    ('name', 'Attendee name'),
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
                raise ValueError('Unsupported stats code: %r' % code)
            qs = qs.select_related('p3_conference', 'user', 'fare')
            data = output['data']
            for x in qs:
                ticket = '<a href="%s">%s</a>' % (
                    reverse('admin:conference_ticket_change', args=(x.id,)),
                    x.id)
                buyer = '<a href="%s">%s %s</a>' % (
                    reverse('admin:auth_user_change', args=(x.user.id,)),
                    x.user.first_name,
                    x.user.last_name)
                data.append({
                    'ticket': ticket,
                    'name': x.name,
                    'email': x.p3_conference.assigned_to,
                    'fare': x.fare.code,
                    'buyer': buyer,
                    'buyer_email': x.user.email,
                })

        elif code in ('sim_tickets',):
            output = {
                'columns': (
                    ('ticket', 'Ticket'),
                    ('name', 'Attendee name'),
                    ('email', 'Email'),
                    ('fare', 'Fare code'),
                ),
                'data': [],
            }
            if code == 'sim_tickets':
                qs = sim_tickets
            else:
                raise ValueError('Unsupported stats code: %r' % code)
            qs = qs.select_related('user', 'fare')
            data = output['data']
            for x in qs:
                ticket = '<a href="%s">%s</a>' % (
                    reverse('admin:conference_ticket_change', args=(x.id,)),
                    x.id)
                buyer = '<a href="%s">%s %s</a>' % (
                    reverse('admin:auth_user_change', args=(x.user.id,)),
                    x.user.first_name,
                    x.user.last_name)
                data.append({
                    'ticket': ticket,
                    'name': buyer,
                    'email': x.user.email,
                    'fare': x.fare.code,
                    'uid': x.user.id,
                })

        elif code in ('voupe03_tickets',):
            output = {
                'columns': (
                    ('uid', 'User ID'),
                    ('name', 'Attendee name'),
                    ('buyer', 'Buyer'),
                ),
                'data': [],
            }
            if code == 'voupe03_tickets':
                qs = voupe03
            else:
                raise ValueError('Unsupported stats code: %r' % code)
            qs = qs.select_related('user')
            data = output['data']
            for x in sorted(qs, key=lambda x: x.name or '%s %s' % (x.user.first_name, x.user.last_name)):
                buyer_name = '%s %s' % (x.user.first_name, x.user.last_name)
                buyer = '<a href="%s">%s</a>' % (
                    reverse('admin:auth_user_change', args=(x.user.id,)), buyer_name)
                data.append({
                    'name': x.name or buyer_name,
                    'buyer': buyer,
                    'uid': x.user.id,
                    'email': x.user.email,
                })

        elif code == 'spam_recruiting':
            output = {
                'columns': (
                    ('uid', 'User ID'),
                    ('name', 'Attendee name'),
                ),
                'data': [],
            }
            qs = spam_recruiting.order_by('first_name', 'last_name')
            data = output['data']
            for x in qs:
                buyer_name = '%s %s' % (x.first_name, x.last_name)
                name = '<a href="%s">%s</a>' % (
                    reverse('admin:auth_user_change', args=(x.id,)), buyer_name)
                data.append({
                    'name': name,
                    'uid': x.id,
                    'email': x.email,
                })
    return output
tickets_status.short_description = 'Tickets stats'

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
                    'title': 'Without ticket',
                    'total': spk_noticket.count(),
                    'note': '',
                },
                {
                    'id': 'no_data',
                    'title': 'Without avatar or biography',
                    'total': spk_nodata.count(),
                    'note': 'Acccount with gravatar are not included',
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
speaker_status.short_description = 'Speakers stats'

def conference_speakers(conf, code=None):
    all_spks = Speaker.objects.byConference(conf, only_accepted=False)
    accepted_spks = Speaker.objects.byConference(conf)
    not_scheduled = Speaker.objects\
        .filter(talkspeaker__talk__in=Talk.objects\
            .filter(conference=conf, status='accepted', event=None))\
        .distinct()
    if code is None:
        return [
            {
                'id': 'all_speakers',
                'title': 'All speakers',
                'total': all_spks.count()
            },
            {
                'id': 'accepted_speakers',
                'title': 'Speakers with accepted talks',
                'total': accepted_spks.count()
            },
            {
                'id': 'speakers_not_scheduled',
                'title': 'Speakers with unscheduled accepted talks',
                'total': not_scheduled.count()
            },
        ]
    else:
        if code == 'all_speakers':
            qs = all_spks
        elif code == 'accepted_speakers':
            qs = accepted_spks
        elif code == 'speakers_not_scheduled':
            qs = not_scheduled
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
conference_speakers.short_description = 'Speakers'

def conference_speakers_day(conf, code=None):
    from p3 import dataaccess
    from conference.dataaccess import talks_data
    from conference.dataaccess import events

    schedules = cmodels.Schedule.objects.filter(conference=conf)
    data = {}
    for s in schedules:
        people = dataaccess.profiles_data(s.speakers()\
            .order_by('user__first_name', 'user__last_name')\
            .values_list('user', flat=True))
        people_data = []
        for p in people:
            o = {
                'uid': p['id'],
                'email': p['email'],
                'name': p['name'],
                'phones': [p['phone']],
                'talks': p['talks']['accepted'].get(conf, []),
            }
            people_data.append(o)
        data[s.date.strftime('%Y-%m-%d')] = people_data
    if code is None:
        output = []
        for date, peoples in sorted(data.items()):
            output.append({
                'id': 'd%s' % date,
                'title': date,
                'total': len(peoples),
            })
        return output
    else:
        people_data = data[code[1:]]
        conf_events = dict([(x['id'], x) for x in events(conf='ep2016')])
        tracks = defaultdict(list)
        for p in people_data:
            tickets = [
                tid for tid, _, fare, complete in dataaccess.all_user_tickets(p['uid'], conf)
                if complete and fare.startswith('SIM') ]
            if tickets:
                p['phones'].extend(
                    models.TicketSIM.objects\
                        .filter(ticket__in=tickets)\
                        .values_list('number', flat=True))
            p['phones'] = filter(None, p['phones'])
            for talk in talks_data(p['talks']):
                for event_id in talk['events_id']:
                    if conf_events[event_id]['time'].date().strftime('%Y-%m-%d') == code[1:]:
                        for track in conf_events[event_id]['tracks']:
                            if p not in tracks[track]:
                                tracks[track].append(p)
        output = {
            'columns': (
                ('name', 'Name'),
                ('email', 'Email'),
                ('phones', 'Phones'),
                ('track', 'Track'),
            ),
            'data': [],
        }
        data = output['data']
        for track, people in sorted(tracks.items()):
            for x in people:
                data.append({
                    'name': '<a href="%s">%s</a>' % (
                        reverse('admin:auth_user_change', args=(x['uid'],)),
                        x['name']),
                    'email': x['email'],
                    'uid': x['uid'],
                    'phones': ', '.join(x['phones']),
                    'track': track,
                })
        return output

conference_speakers_day.short_description = 'Speaker for day'

def hotel_tickets(conf, code=None):
    qs = {}
    for x in ('1', '2', '3', '4'):
        qs['HR' + x] = _tickets(conf, fare_code='HR' + x)\
            .select_related(
                'orderitem__order__user__user',
                'p3_conference_room')
    for x in ('2', '3', '4'):
        qs['HB' + x] = _tickets(conf, fare_code='HB' + x)\
            .select_related(
                'user',
                'orderitem__order__user__user__attendeeprofile__p3_profile',
                'p3_conference_room')

    # unfilled hotel tickets
    # ----------------------
    # It's the union between tickets with empty name or document (and haven't
    # been marked as unused) and the ones with the same name as the buyer.
    #
    # Being valid for a person to buy an hotel ticket for him/herself, the second
    # condition only triggers if the name of the buyer is present more than once.
    #
    # The second query (for the second check) is quite long because I've to repeat
    # in the where parts the conditions (and consequently the joins) to be able to
    # identify exactly in all the tickets of a certain user which are the
    # ones with the problem.
    #
    # Suppose someone bought 4 tickets:
    #
    # . buyer   ticket_name
    # 1 Mr. X   Mr. X
    # 2 Mr. X   <empty>
    # 3 Mr. X   Mrs. X
    # 4 Mr. X   Mr. X
    #
    # The first part of the query selects row number 2 while the second will
    # select row 1 and 4; without repeating the conditions the second query
    # would also return row 3.
    #
    # When (and if) sqlite will support WITH clause this could be rediscussed.
    not_compiled_sql = """
    select p3t.id
    from p3_ticketroom p3t inner join conference_ticket ct
     on p3t.ticket_id = ct.id
    inner join conference_fare f
     on ct.fare_id=f.id
    where
      f.conference=%s
      and f.code in ('HR1', 'HR2', 'HR3', 'HR4', 'HB2', 'HB3', 'HB4')
      and (ltrim(ct.name) = '' or document = '') and p3t.unused=0

    union

    select p3t.id
    from p3_ticketroom p3t inner join conference_ticket ct
     on p3t.ticket_id = ct.id
    inner join auth_user u
     on ct.user_id=u.id
    inner join conference_fare f
     on ct.fare_id=f.id
    inner join (
        select ct.user_id, count(*) as x
        from p3_ticketroom p3t inner join conference_ticket ct
         on p3t.ticket_id = ct.id
        inner join auth_user u
         on ct.user_id=u.id
        inner join conference_fare f
         on ct.fare_id=f.id
        where
          f.conference=%s
          and f.code in ('HR1', 'HR2', 'HR3', 'HR4', 'HB2', 'HB3', 'HB4')
          and p3t.unused=0
          and (
            lower(ct.name) = lower(u.first_name || ' ' || u.last_name)
            or lower(ct.name) = lower(u.last_name || ' ' || u.first_name))
        group by ct.user_id
        having x>1) hot_items
      on ct.user_id = hot_items.user_id
    where
      f.conference=%s
      and f.code in ('HR1', 'HR2', 'HR3', 'HR4', 'HB2', 'HB3', 'HB4')
      and (
        lower(ct.name) = lower(u.first_name || ' ' || u.last_name)
        or lower(ct.name) = lower(u.last_name || ' ' || u.first_name))
    """
    from p3.utils import RawSubquery
    not_compiled = _tickets(conf)\
        .filter(p3_conference_room__id__in=RawSubquery(not_compiled_sql, [conf, conf, conf]))\
        .select_related(
            'user',
            'orderitem__order__user__user__attendeeprofile__p3_profile',
            'p3_conference_room')

    if code is None:
        output = {
            'columns': (
                ('total', 'Total'),
                ('note', 'Note'),
            ),
            'data': [
                {
                    'id': 'HR1',
                    'title': 'Single room',
                    'total': qs['HR1'].count(),
                },
                {
                    'id': 'HR2',
                    'title': 'Double room',
                    'total': qs['HR2'].count(),
                },
                {
                    'id': 'HR3',
                    'title': 'Tripe room',
                    'total': qs['HR3'].count(),
                },
                {
                    'id': 'HR4',
                    'title': 'Quadruple room',
                    'total': qs['HR4'].count(),
                },
                {
                    'id': 'HB2',
                    'title': 'Bed in double',
                    'total': qs['HB2'].count(),
                },
                {
                    'id': 'HB3',
                    'title': 'Bed in triple',
                    'total': qs['HB3'].count(),
                },
                {
                    'id': 'HB4',
                    'title': 'Bed in quadruple',
                    'total': qs['HB4'].count(),
                },
                {
                    'id': 'not-compiled',
                    'title': 'Tickets not compiled',
                    'total': not_compiled.count(),
                    'note': """
                        Also tickets assigned to the same person (after the first)"""
                },
            ]
        }
    else:
        def ticket_name(ticket):
            name = ticket.name.strip()
            if not name:
                name = 'buyed by <a href="%s">%s %s</a>' % (
                    reverse('admin:auth_user_change', args=(ticket.user_id,)),
                    ticket.user.first_name,
                    ticket.user.last_name)
            else:
                name = '<a href="%s">%s</a>' % (
                    reverse('admin:auth_user_change', args=(ticket.user_id,)),
                    name)
            return name

        if code == 'not-compiled' or code[1] == 'R':
            output = {
                'columns': (
                    ('name', 'Attendee name'),
                    ('email', 'Email'),
                    ('order', 'Order Number'),
                    ('checkin', 'Check in'),
                    ('checkout', 'Check out'),
                ),
                'data': [],
            }
            data = output['data']
            if code == 'not-compiled':
                query = not_compiled
            else:
                query = qs[code]
            for ticket in query:
                data.append({
                    'name': ticket_name(ticket),
                    'email': ticket.user.email,
                    'order': '<a href="%s">%s</a>' % (
                        reverse('admin:assopy_order_change', args=(ticket.orderitem.order_id,)),
                        ticket.orderitem.order.code),
                    'checkin': ticket.p3_conference_room.checkin,
                    'checkout': ticket.p3_conference_room.checkout,
                    'uid': ticket.user.id,
                })
        else:
            output = {
                'columns': (
                    ('name', 'Attendee name'),
                    ('email', 'Email'),
                    ('order', 'Order Number'),
                    ('checkin', 'Check in'),
                    ('checkout', 'Check out'),
                    ('interests', 'Interests'),
                ),
                'data': [],
            }
            data = output['data']
            for ticket in qs[code]:
                interests = ', '.join(
                    ticket.orderitem.order.user.user.attendeeprofile.p3_profile.interests.all().values_list('name', flat=True))
                data.append({
                    'name': ticket_name(ticket),
                    'email': ticket.user.email,
                    'order': '<a href="%s">%s</a>' % (
                        reverse('admin:assopy_order_change', args=(ticket.orderitem.order_id,)),
                        ticket.orderitem.order.code),
                    'checkin': ticket.p3_conference_room.checkin,
                    'checkout': ticket.p3_conference_room.checkout,
                    'interests': interests,
                    'uid': ticket.user.id,
                })

    return output

hotel_tickets.short_description = 'Hotel reservation'

def pp_tickets(conf, code=None):
    fcodes = cmodels.Fare.objects\
        .filter(conference=conf, ticket_type='partner')\
        .order_by('code')\
        .values_list('code', flat=True)
    qs = {}
    for fcode in fcodes:
        qs[fcode] = _tickets(conf, fare_code=fcode)
    all_attendees = User.objects.filter(id__in=_tickets(conf, ticket_type='partner').values('user'))
    if code is None:
        output = [{
            'id': 'all',
            'total': all_attendees.count(),
            'title': 'Tickets partner program',
        }]
        from conference.templatetags.conference import fare_blob
        titles = {}
        for f in cmodels.Fare.objects.filter(code__in=fcodes):
            titles[f.code] = '%s (%s)' % (f.name, fare_blob(f, 'date'))
        for fcode in fcodes:
            output.append({
                'id': fcode,
                'total': qs[fcode].count(),
                'title': fcode + ' - ' + titles[fcode],
            })
    else:
        output = {
            'columns': (
                ('name', 'Attendee name'),
                ('buyer', 'Buyer'),
                ('email', 'Email'),
            ),
            'data': [],
        }
        data = output['data']
        if code == 'all':
            for x in all_attendees:
                data.append({
                    'name': '',
                    'buyer': '<a href="%s">%s %s</a>' % (
                        reverse('admin:auth_user_change', args=(x.id,)),
                        x.first_name,
                        x.last_name),
                    'email': x.email,
                    'uid': x.id,
                })
        else:
            for x in qs[code]:
                data.append({
                    'name': x.name or ('%s %s' % (x.user.first_name, x.user.last_name)),
                    'buyer': '<a href="%s">%s %s</a>' % (
                        reverse('admin:auth_user_change', args=(x.user_id,)),
                        x.user.first_name,
                        x.user.last_name),
                    'email': x.user.email,
                    'uid': x.user_id,
                })
    return output
pp_tickets.short_description = 'Tickets Partner program'
