# -*- coding: utf-8 -*-
""" Print a json file with the participants information for their badges."""

import json
import logging as log
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from ...utils import (
    get_profile_company,
    get_all_order_tickets
)

### Helpers

###
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--status',
                    action='store',
                    dest='status',
                    default='all',
                    choices=['all', 'complete', 'incomplete'],
                    help='Status of the orders related with the tickets.',
                ),
        make_option('--nondups',
                    action='store_true',
                    dest='nondups',
                    default=False,
                    help='If enables will remove the tickets with '
                         'same owner/email.',
                ),
        make_option('--raise',
                    action='store_true',
                    dest='raise',
                    default=False,
                    help='If enabled will raise any error that it may find.',
                ),
        make_option('--ticket-id',
                    action='store',
                    dest='ticket_id',
                    help='Will output the profile of the given ticket only.',
                ),
    )

    def handle(self, *args, **options):
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference not specified')

        if options['status'] not in ('all', 'complete', 'incomplete'):
            raise CommandError('--status should be one of '
                               '(all, complete, incomplete)' )

        tickets = get_all_order_tickets(conference)
        if not tickets:
            raise IndexError('Could not find any tickets for '
                             'conference {}.'.format(conference))

        if options['ticket_id']:
            ticket_id = int(options['ticket_id'])
            tickets = [ticket for ticket in tickets if ticket.id == ticket_id]
            if not tickets:
                raise IndexError('Could not find any ticket with '
                                 'ticket_id {}.'.format(options['ticket_id']))

        dflt_profile = {'name':    '',
                        'surname': '',
                        'tagline': '',
                        'company': '',
                        'title':   '',
                        'pypower': '0',
                        'tshirt':  'l',
                        'email':   '',
                        'phone':   '',
                        'compweb': '',
                        'persweb': '',
                        'id'     : '',
                        'frozen' : False,
                        }

        profiles = [] #OrderedDict()
        for ticket in tickets:
            p3_tkt = ticket.p3_conference
            subj   = dflt_profile.copy()

            try:
                profile = p3_tkt.profile()
            except:
                msg = 'Could not find a profile for ticket_id {}.'.format(ticket.id)
                if options['raise']:
                    #raise AttributeError(msg)
                    log.error(msg)
                    import ipdb
                    ipdb.set_trace()
                else:
                    log.error(msg)

            title, company = get_profile_company(profile)
            subj['title'] = title.encode('utf-8')
            subj['company'] = company.encode('utf-8')
            subj['name'] = profile.user.first_name.encode('utf-8')
            subj['surname'] = profile.user.last_name.encode('utf-8')
            subj['tagline'] = p3_tkt.tagline.encode('utf-8')
            subj['pypower'] = p3_tkt.python_experience
            subj['tshirt'] = p3_tkt.shirt_size.encode('utf-8')
            subj['email'] = profile.user.email.encode('utf-8')
            subj['phone'] = profile.phone.encode('utf-8')
            subj['compweb'] = profile.company_homepage.encode('utf-8')
            subj['persweb'] = profile.personal_homepage.encode('utf-8')
            subj['id'] = ticket.id
            subj['frozen'] = ticket.frozen
            subj['fare_code'] = ticket.fare.code
            subj['recipient_type'] = ticket.fare.recipient_type
            subj['ticket_type'] = ticket.fare.ticket_type

            profiles.append(subj)

        print(json.dumps(profiles, indent=2, separators=(',', ': ')))
