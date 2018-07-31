# -*- coding: UTF-8 -*-
from collections import defaultdict
from conference.models import Ticket, Speaker, Talk
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import Q, Count
from p3 import models
from conference import models as cmodels


def _create_option(id, title, total_qs, **kwargs):
    output = {
        'id': id,
        'title': title,
        'total': total_qs.count(),
    }
    output.update(kwargs)
    return output


def _tickets(conf, ticket_type=None, fare_code=None, only_complete=True):
    # TODO: check why it needs frozen=False NEEDSDOCUMENTATION
    qs = Ticket.objects\
        .filter(fare__conference=conf, frozen=False)

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


def _tickets_with_unique_email(conf, ticket_type='conference'):
    assigned_tickets = _assigned_tickets(conf, ticket_type)
    email_ids = dict(
        (ticket.p3_conference.assigned_to, ticket.id)
        for ticket in assigned_tickets)
    # MAL 2018-07-31: This is a hack: since most emails will be
    # unique, the id__in filter does not overflow. Doing the reverse
    # will cause a SQL error due to too many SQL variables.
    all_ids = set(ticket.id
                  for ticket in assigned_tickets)
    ids = set(email_ids.values())
    duplicate_email_ids = all_ids - ids
    return assigned_tickets.filter(
        ~Q(id__in=duplicate_email_ids))

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
            ('total_nc', '<span title="Estimate with unassigned tickets and incomplete '
                                      'bank orders">Estimate with NA/NC</span>'),
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
    if 0: # FIXME: remove hotels and sim
        sim_tickets = _tickets(conf, fare_code='SIM%')\
            .filter(Q(p3_conference_sim=None)|Q(name='')|Q(p3_conference_sim__document=''))\
            .select_related('p3_conference_sim')
    voupe03 = _tickets(conf, fare_code='VOUPE03')
    from p3.utils import spam_recruiter_by_conf
    spam_recruiting = spam_recruiter_by_conf(conf)
    if code is None:
        # FIXME: remove hotel and sim (sim_tickets has been removed
        # from the parameters of ticket_status_no_code function
        output = ticket_status_no_code(conf,
                                       multiple_assignments,
                                       orphan_tickets,
                                       spam_recruiting,
                                       voupe03)
    else:
        if code in ('ticket_sold', 'assigned_tickets',
                    'unassigned_tickets', 'multiple_assignments',
                    'tickets_with_unique_email'):
            output = ticket_status_for_un_assigned_sold_tickets(code,
                                                                conf,
                                                                multiple_assignments)

        elif code in ('orphan_tickets',):
            output = ticket_status_for_orphant_tickets(code, orphan_tickets)

        elif code in ('voupe03_tickets',):
            output = ticket_status_for_voupe03_tickets(code, voupe03)

        elif code == 'spam_recruiting':
            output = ticket_status_for_spam_recruiting(spam_recruiting)

        if 0:
            # elif code in ('sim_tickets',):
            #     output = ticket_status_for_sim_tickets(code, sim_tickets)
            pass

    return output


def ticket_status_for_un_assigned_sold_tickets(code, conf, multiple_assignments):
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
    elif code == 'tickets_with_unique_email':
        qs = _tickets_with_unique_email(conf)
    elif code == 'assigned_tickets':
        qs = _assigned_tickets(conf)
    elif code == 'unassigned_tickets':
        qs = _unassigned_tickets(conf)
    elif code == 'multiple_assignments':
        qs = _tickets(conf, 'conference') \
            .filter(p3_conference__assigned_to__in=multiple_assignments \
                    .values('p3_conference__assigned_to'))
    else:
        raise ValueError('Unsupported stats code: %r' % code)
    qs = qs.select_related('p3_conference', 'user')
    assignees = dict([
        (u.email, u) for u in User.objects \
            .filter(email__in=qs \
                    .exclude(p3_conference__assigned_to='') \
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
    return output


def ticket_status_for_orphant_tickets(code, orphan_tickets):
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
    return output


def ticket_status_for_spam_recruiting(spam_recruiting):
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


def ticket_status_for_voupe03_tickets(code, voupe03):
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
    return output


if 0: # FIXME: remove hotels and sim
    def ticket_status_for_sim_tickets(code, sim_tickets):
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
        return output


def ticket_status_no_code(conf, multiple_assignments, orphan_tickets, spam_recruiting, voupe03):
    return [
        _create_option('ticket_sold', 'Sold tickets', _tickets(conf, 'conference')),
        _create_option('tickets_with_unique_email', 'Sold tickets with unique email', _tickets_with_unique_email(conf, 'conference')),
        _create_option('assigned_tickets', 'Assigned tickets', _assigned_tickets(conf)),
        _create_option('unassigned_tickets', 'Unassigned tickets', _unassigned_tickets(conf)),
        # _create_option('sim_tickets', 'Tickets with SIM card orders', sim_tickets),  # FIXME: remove hotels and sim
        _create_option('voupe03_tickets', 'Social event tickets (VOUPE03)', voupe03),
        _create_option('spam_recruiting', 'Recruiting emails (opt-in)', spam_recruiting),
        _create_option('multiple_assignments', 'Tickets assigned to the same person', multiple_assignments),
        _create_option('orphan_tickets', 'Assigned tickets without user record (orphaned)', orphan_tickets)
    ]


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
                _create_option('no_ticket', 'Without ticket', spk_noticket, note=''),
                _create_option('no_data', 'Without avatar or biography', spk_nodata, note='Account with gravatar are not included'),
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
            _create_option('all_speakers', 'All speakers', all_spks),
            _create_option('accepted_speakers', 'Speakers with accepted talks', accepted_spks),
            _create_option('speakers_not_scheduled', 'Speakers with unscheduled accepted talks', not_scheduled),
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
        conf_events = dict([(x['id'], x) for x in events(conf=settings.CONFERENCE_CONFERENCE)])
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
        output = [
            _create_option('all', 'Tickets partner program', all_attendees)
        ]
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
