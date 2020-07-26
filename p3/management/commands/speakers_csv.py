import csv

from django.core.management.base import BaseCommand

from conference import models


class Command(BaseCommand):

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('conference')

    def handle(self, *args, **options):
        conference = models.Conference.objects.get(code=options['conference'])

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
        writer = csv.DictWriter(self.stdout, columns)
        writer.writerow(dict(list(zip(columns, columns))))

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
            writer.writerow(row)
