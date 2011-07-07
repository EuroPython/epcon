# -*- coding: UTF-8 -*-
import haystack

from django.core.management.base import BaseCommand, CommandError
from conference import models

from collections import defaultdict
from optparse import make_option

class Command(BaseCommand):
    """
    """
    option_list = BaseCommand.option_list + (
        make_option('--by-ticket',
            action='store_true',
            dest='by_ticket',
            default=False,
            help='list by ticket instead of person',
        ),
        make_option('--no-staff',
            action='store_true',
            dest='no_staff',
            default=False,
            help='exclude staff tickets',
        ),
    )
    def handle(self, *args, **options):
        qs = models.Ticket.objects\
                    .filter(orderitem__order___complete=True)\
                    .exclude(fare__ticket_type='partner')\
                    .select_related('user', 'fare', 'p3_conference')
        if options['no_staff']:
            qs = qs.exclude(ticket_type='staff')

        buyers = defaultdict(list)
        names = defaultdict(list)
        non_conference_tickets = defaultdict(list)
        conference_tickets = []
        alien_tickets = []
        for t in qs.filter(fare__ticket_type='conference'):
            name = t.name or '%s %s' % (t.user.first_name, t.user.last_name)
            data = {
                'name': name,
                'ticket': t,
                'additional': [],
            }
            conference_tickets.append(data)
            buyers[t.user_id].append(data)
            names[name].append(data)

        for t in qs.exclude(fare__ticket_type='conference'):
            if t.name:
                if t.name in names:
                    founds = names[t.name]
                    if len(founds) == 1:
                        ix = 0
                        maybe = False
                    else:
                        maybe = True
                        for ix, tdata in enumerate(founds):
                            if tdata['ticket'].user_id == t.user_id:
                                maybe = False
                                break
                        else:
                            ix = 0
                    founds[ix]['additional'].append({
                        'ticket': t,
                        'maybe': maybe,
                    })
                    non_conference_tickets[t.fare].append({
                        'ticket': t,
                        'maybe': maybe,
                        'conference': founds[ix],
                    })
                    continue
            if t.user_id in buyers:
                buyers[t.user_id][0]['additional'].append({
                    'ticket': t,
                    'maybe': False,
                })
                non_conference_tickets[t.fare].append({
                    'ticket': t,
                    'maybe': False,
                    'conference': buyers[t.user_id][0],
                })
                continue
            name = t.name or '%s %s' % (t.user.first_name, t.user.last_name)
            alien_tickets.append({
                'name': name,
                'ticket': t,
            })
            non_conference_tickets[t.fare].append({
                'ticket': t,
                'maybe': False,
                'conference': None,
            })

        conference_tickets.sort(key=lambda x: x['name'].upper())
        alien_tickets.sort(key=lambda x: x['name'].upper())

        if not options['by_ticket']:
            letter = None
            for t in conference_tickets:
                row = [
                    t['name'].encode('utf-8'),
                    'STAFF' if t['ticket'].ticket_type == 'staff' else t['ticket'].fare.name,
                    t['ticket'].p3_conference.days if t['ticket'].p3_conference and t['ticket'].fare.code[2] == 'D' else '',
                ]
                if row[0][0].upper() != letter:
                    letter = row[0][0].upper()
                    print '\n\n'
                    print '\t\t\t', letter
                    print '-' * 80
                    print '\n\n'
                print '\t'.join(map(str, row))
                for linked in t['additional']:
                    row = [
                        '%s%s' % ('(*) ' if linked['maybe'] else '', linked['ticket'].name.encode('utf-8')),
                        linked['ticket'].fare.code,
                        linked['ticket'].fare.name,
                    ]
                    print '\t', '\t'.join(map(str, row))
            
            if alien_tickets:
                print '\n\n'
                print '\t\t\t', 'ALIEN'
                print '-' * 80
                print '\n\n'
                for t in alien_tickets:
                    row = [
                        t['name'].encode('utf-8'),
                        'STAFF' if t['ticket'].ticket_type == 'staff' else t['ticket'].fare.name,
                        t['ticket'].p3_conference.days if t['ticket'].p3_conference and t['ticket'].fare.code[2] == 'D' else '',
                    ]
                    print '\t'.join(map(str, row))
        else:
            for fare, items in non_conference_tickets.items():
                print '\n\n'
                print '\t\t\t', fare.code, fare.name.encode('utf-8')
                print '-' * 80
                print '\n\n'
                def k(x):
                    t = x['ticket']
                    return t.name or '%s %s' % (t.user.first_name, t.user.last_name)
                for t in sorted(items, key=k):
                    if t['maybe']:
                        print '(*)',
                    print k(t).encode('utf-8'), '->', 
                    if t['conference']:
                        print t['conference']['name'].encode('utf-8')
                    else:
                        print ''
