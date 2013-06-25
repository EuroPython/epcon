# -*- coding: UTF-8 -*-
import sys
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from conference import models
from conference import settings
from conference import utils

class Command(BaseCommand):
    """
    """
    option_list = BaseCommand.option_list + (
        make_option('--type',
            action='store',
            dest='type',
            default='conference',
            help='Filter the tickets by type',
        ),
        make_option('--fare',
            action='store',
            dest='fare',
            default=None,
            help='Filter the tickets by fare code',
        ),
        make_option('--names',
            action='store',
            dest='names',
            default=None,
            help='Select tickets by badge name',
        ),
        make_option('--ids',
            action='store',
            dest='ids',
            default=None,
            help='Select tickets by ids',
        ),
        make_option('--input-data',
            action='store',
            dest='input_data',
            default=None,
            help='Save the data used to generate the badegs in the given file',
        ),
    )
    def handle(self, *args, **options):
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference code is missing')

        cmdargs = settings.TICKET_BADGE_PROG_ARGS
        tickets = settings.CONFERENCE_TICKETS(
            conference, ticket_type=options['type'], fare_code=options['fare'])
        if options['names']:
            q = Q()
            for n in options['names'].split(','):
                q |= Q(name__icontains=n)
            tickets = tickets.filter(q)
            cmdargs.extend(['-e', '0', '-p', 'A4', '-n', '4'])
        if options['ids']:
            tickets = tickets.filter(id__in=options['ids'].split(','))
            cmdargs.extend(['-e', '0', '-p', 'A4', '-n', '4'])
        files = utils.render_badge(tickets, cmdargs=cmdargs)
        f, input_data = files[0]
        if options['input_data']:
            file(options['input_data'], 'w').write(input_data)
        f.seek(0)
        while True:
            data = f.read(16*1024)
            if not data:
                break
            sys.stdout.write(data)

