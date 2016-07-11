# -*- coding: utf-8 -*-
""" Print a json file with the participants information for their badges."""

import json
import logging as log
from   optparse import make_option
from   collections import OrderedDict

from   django.core.management.base import BaseCommand, CommandError

from   assopy import models as assopy_models

from ...utils import (get_profile_company,
                      get_all_order_tickets)

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

        tkts = get_all_order_tickets(conference)
        if not tkts:
            raise IndexError('Could not find any tickets for '
                             'conference {}.'.format(conference))

        if options['ticket_id']:
            tkt_id = int(options['ticket_id'])
            tkts = [t for t in tkts if t.id == tkt_id]
            if not tkts:
                raise IndexError('Could not find any ticket with '
                                 'ticket_id {}.'.format(options['ticket_id']))

        dflt_profile = {'name':    '',
                        'surname': '',
                        'tagline': '',
                        'company': '',
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
        for t in tkts:
            p3_tkt = t.p3_conference
            subj   = dflt_profile.copy()

            try:
                profile = p3_tkt.profile()
            except:
                msg = 'Could not find a profile for ticket_id {}.'.format(t.id)
                if options['raise']:
                    #raise AttributeError(msg)
                    log.error(msg)
                    import ipdb
                    ipdb.set_trace()
                else:
                    log.error(msg)

            subj['company'] = get_profile_company(profile)
            subj['name'   ] = profile.user.first_name
            subj['surname'] = profile.user.last_name
            subj['tagline'] = p3_tkt.tagline
            subj['pypower'] = str(p3_tkt.python_experience)
            subj['tshirt']  = p3_tkt.shirt_size
            subj['email'  ] = profile.user.email
            subj['phone'  ] = profile.phone
            subj['compweb'] = profile.company_homepage
            subj['persweb'] = profile.personal_homepage
            subj['id']      = str(t.id)
            subj['frozen']  = str(t.frozen)

            subj = {k: v.encode('utf-8') for k, v in subj.items()}

            profiles.append(subj)

        print(json.dumps(profiles, indent=2, separators=(',', ': ')))
