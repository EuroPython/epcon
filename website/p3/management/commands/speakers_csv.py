# -*- coding: UTF-8 -*-
import haystack

from django.core.management.base import BaseCommand, CommandError

from conference import models
from p3.models import TicketConference

import csv
import sys

class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):
        try:
            conference = models.Conference.objects.get(code=args[0])
        except IndexError:
            raise CommandError('conference missing')

        speakers = set()
        talks = models.Talk.objects.accepted(conference.code)
        for t in talks:
            speakers |= set(t.get_all_speakers())

        columns = (
            'name', 'email',
            'conference_ticket', 'orders',
            'discounts',
        )
        writer = csv.DictWriter(sys.stdout, columns)
        writer.writerow(dict(zip(columns, columns)))
        def utf8(d):
            d = dict(d)
            for k, v in d.items():
                try:
                    d[k] = v.encode('utf-8')
                except:
                    pass
            return d
        for s in sorted(speakers, key=lambda x: x.user.assopy_user.name()):
            tickets = TicketConference.objects.available(s.user, conference).filter(fare__ticket_type='conference')
            row = {
                'name': s.user.assopy_user.name(),
                'email': s.user.email,
                'conference_ticket': tickets.filter(orderitem__order___complete=True).count(),
                'orders': ' '.join(set(t.orderitem.order.code for t in tickets)),
                'discounts': ' '.join(set(row.code for t in tickets for row in t.orderitem.order.orderitem_set.all() if row.price < 0)),
            }
            writer.writerow(utf8(row))
