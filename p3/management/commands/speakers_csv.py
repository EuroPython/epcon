# -*- coding: UTF-8 -*-

from django.core.management.base import BaseCommand, CommandError

from conference import models

import csv
import sys

class Command(BaseCommand):
    """
    """

    args = '<conference>'

    def handle(self, *args, **options):
        try:
            conference = models.Conference.objects.get(code=args[0])
        except IndexError:
            raise CommandError('conference missing')

        speakers = set()
        talks = models.Talk.objects.accepted(conference.code)
        for t in talks:
            speakers |= set(t.get_all_speakers())

        # mandated by Guidebook
        COL_NAME = "Name"
        COL_TITLE = "Sub-Title (i.e. Location, Table/Booth, or Title/Sponsorship Level)"
        COL_BIO = "Description (Optional)"

        columns = (
            #'name', 'tagline', 'bio', #'email',
            #'conference_ticket', 'orders',
            #'discounts',
            COL_NAME, COL_TITLE, COL_BIO,
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
            profile = models.AttendeeProfile.objects.get(user=s.user)
            if profile.job_title and profile.company:
                tagline = profile.job_title + " @ " + profile.company
            elif profile.job_title:
                tagline = profile.job_title
            elif profile.company:
                tagline = profile.company
            else:
                tagline = ""
            #tickets = TicketConference.objects.available(s.user, conference).filter(fare__ticket_type='conference')
            row = {
                COL_NAME: s.user.assopy_user.name(),
		COL_BIO: getattr(profile.getBio(),'body',''),
 		COL_TITLE: tagline,
                #'email': s.user.email,
                #'conference_ticket': tickets.filter(orderitem__order___complete=True).count(),
                #'orders': ' '.join(set(t.orderitem.order.code for t in tickets)),
                #'discounts': ' '.join(set(row.code for t in tickets for row in t.orderitem.order.orderitem_set.all() if row.price < 0)),
            }
            writer.writerow(utf8(row))
