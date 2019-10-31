""" Print a json file with the participants information for their badges."""

import json

from django.core.management.base import BaseCommand, CommandError
from conference import models

from ...utils import (
    get_profile_company,
    get_all_order_tickets
)


class Command(BaseCommand):

    def add_arguments(self, parser):

        # Positional arguments
        parser.add_argument('conference')

        # Named (optional) arguments
        parser.add_argument(
            '--status',
            action='store',
            dest='status',
            default='all',
            choices=['all', 'complete', 'incomplete'],
            help='Status of the orders related with the tickets.',
        )
        parser.add_argument(
            '--nondups',
            action='store_true',
            dest='nondups',
            default=False,
            help='If enables will remove the tickets with '
                 'same owner/email.',
        )
        parser.add_argument(
            '--raise',
            action='store_true',
            dest='raise',
            default=False,
            help='If enabled will raise any error that it may find.',
        )
        parser.add_argument(
            '--ticket-id',
            action='store',
            dest='ticket_id',
            help='Will output the profile of the given ticket only.',
        )

    def handle(self, *args, **options):
        conference = models.Conference.objects.get(code=options['conference'])

        if options['status'] not in ('all', 'complete', 'incomplete'):
            raise CommandError('--status should be one of '
                               '(all, complete, incomplete)' )

        tickets = get_all_order_tickets(conference.code)
        if not tickets:
            raise IndexError('Could not find any tickets for '
                             'conference {}.'.format(conference.code))

        if options['ticket_id']:
            ticket_id = int(options['ticket_id'])
            tickets = [ticket for ticket in tickets if ticket.id == ticket_id]
            if not tickets:
                raise IndexError('Could not find any ticket with '
                                 'ticket_id {}.'.format(options['ticket_id']))

        dflt_profile = {
            'name':    '',
            'surname': '',
            'tagline': '',
            'company': '',
            'title':   '',
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
            subj = dflt_profile.copy()
            try:
                profile = p3_tkt.profile()
            except:
                msg = 'Could not find a profile for ticket_id {}.'.format(ticket.id)
                self.stdout.write(msg)

            title, company = get_profile_company(profile)
            subj['title'] = title
            subj['company'] = company
            subj['name'] = profile.user.first_name
            subj['surname'] = profile.user.last_name
            subj['tagline'] = p3_tkt.tagline
            subj['tshirt'] = p3_tkt.shirt_size
            subj['email'] = profile.user.email
            subj['phone'] = profile.phone
            subj['compweb'] = profile.company_homepage
            subj['persweb'] = profile.personal_homepage
            subj['id'] = ticket.id
            subj['frozen'] = ticket.frozen
            subj['fare_code'] = ticket.fare.code
            subj['recipient_type'] = ticket.fare.recipient_type
            subj['ticket_type'] = ticket.fare.ticket_type

            profiles.append(subj)

        self.stdout.write(json.dumps(profiles, indent=2, separators=(',', ': ')))
