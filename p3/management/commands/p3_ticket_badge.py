# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from conference import models
from conference import utils

class Command(BaseCommand):
    """
    """
    option_list = BaseCommand.option_list + (
        make_option('--names',
            action='store',
            dest='names',
            default=None,
            help='Select tickets by badge name',
        ),
    )
    def handle(self, *args, **options):
        try:
            conference, output = args
        except IndexError:
            raise CommandError('conference code is missing')

        cmdargs = []
        bank_limit = datetime.now() - timedelta(days=30)
        tickets = models.Ticket.objects\
            .filter(fare__conference=conference, fare__ticket_type='conference')\
            .filter(
                Q(orderitem__order___complete=True)
                | Q(orderitem__order__method='bank', orderitem__order__created__gte=bank_limit))\
            .select_related('orderitem__order')
        if options['names']:
            q = Q()
            for n in options['names'].split(','):
                q |= Q(name__icontains=n)
            tickets = tickets.filter(q)
            cmdargs.extend(['-e', '0', '-p', 'A4', '-n', '4'])
        files = utils.render_badge(tickets, cmdargs=cmdargs)
        files[0].seek(0)
        with file(output, 'w') as f:
            while True:
                chunk = files[0].read(16*1024)
                if not chunk:
                    break
                f.write(chunk)

        with file(output + '.check', 'w') as f:
            for t in tickets:
                if not t.orderitem.order._complete:
                    f.write('Ticket: %s(%d) - Order: %s\n' % (t.name.encode('utf-8'), t.id, t.orderitem.order.code.encode('utf-8')))
