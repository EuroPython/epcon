# -*- coding: UTF-8 -*-
import sys
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from conference import models
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
    )
    def handle(self, *args, **options):
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference code is missing')

        cmdargs = []
        tickets = models.Ticket.objects.filter(fare__conference=conference, fare__ticket_type=options['type'])
        if options['fare']:
            tickets = tickets.filter(fare__code__startswith=options['fare'])
        if options['names']:
            names = options['names'].split(',')
            q = Q()
            for n in options['names'].split(','):
                q |= Q(name__icontains=n)
            tickets = tickets.filter(q)
            cmdargs.extend(['-e', '0'])
        files = utils.render_badge(tickets, cmdargs=cmdargs)
        f = files[0]
        f.seek(0)
        while True:
            data = f.read(16*1024)
            if not data:
                break
            sys.stdout.write(data)

