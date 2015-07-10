__author__ = 'oier'

# -*- coding: UTF-8 -*-

from django.core.management.base import BaseCommand, CommandError

from conference import models
from p3.models import TicketConference
from   assopy       import models as assopy_models

import csv
import sys


def get_all_order_tickets():
    orders          = assopy_models.Order.objects.filter(_complete=True)
    order_tkts      = [ordi.ticket for order in orders for ordi in order.orderitem_set.all() if ordi.ticket is not None]
    conf_order_tkts = [ot for ot in order_tkts if ot.fare.code.startswith('T')]
    return conf_order_tkts

class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):

        if not args[1] in ['all', 'complete', 'incomplete']:
            raise CommandError('third args should be between (all, complete, incomplete)' )

        try:
            conference = models.Conference.objects.get(code=args[0])
        except IndexError:
            raise CommandError('conference missing')

        #con_tickets = models.Ticket.objects.all()

        con_tickets = get_all_order_tickets()

        p3_tickets = TicketConference.objects.all()

        con_ids = [ t.id for t in con_tickets ]
        p3_ids  = [ t.ticket_id for t in p3_tickets ]

        #GET ALL attendees
        #talks = models.Talk.objects.accepted(conference.code)
        #for t in talks:
        #     |= set(t.get_all_speakers())

        COL_NAME = "Name"
        COL_SURNAME = "Surname"
        COL_TAG = "Tagline"
        COL_AFILIATION = "Affiliation"
        COL_EXP = "Python experience"
        COL_SHIRT = "T-shirt"
        COL_EMAIL = "Email"
        COL_PHONE = "Phone"
        COL_COMWEB = "Company homepage"
        COL_PERWEB = "Personal homepage"

        columns = (
            COL_NAME, COL_SURNAME, COL_TAG, COL_AFILIATION, COL_EXP, COL_SHIRT, COL_EMAIL, COL_PHONE,  COL_COMWEB, COL_PERWEB
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


        #for s in sorted(attendees, key=lambda x: x.user.assopy_user.name()):

        for t in con_tickets:
            #profile = models.AttendeeProfile.objects.get(user=s.user)

            temp = TicketConference.objects.filter(ticket_id=t.id)

            tc = None

            if temp:
                for temp_tc in p3_tickets:
                    if temp_tc.ticket_id == t.id:
                        tc = temp_tc
                        break

            if tc != None:
                if (args[1] == 'incomplete'):
                    continue
            else:
                if (args[1] == 'complete'):
                    continue

            #default values:
            name = ""
            surname = ""
            affiliation = ""

            email = ""
            phone = ""
            comp = ""
            per = ""
            tagline = ""
            p_exp = 0
            shirt = "l"

            try:
                profile = tc.profile()

                if profile.job_title and profile.company:
                    affiliation = profile.job_title + " @ " + profile.company
                elif profile.job_title:
                    affiliation = profile.job_title
                elif profile.company:
                    affiliation = profile.company
                else:
                    affiliation = ""

                name = profile.user.first_name
                surname = profile.user.last_name

                tagline = tc.tagline
                email = profile.user.email
                phone = profile.phone
                comp = profile.company_homepage
                per = profile.personal_homepage
                p_exp = tc.python_experience
                shirt = tc.shirt_size

            #except models.AttendeeProfile.DoesNotExist:
            except:
                affiliation = ""

                if t.name:
                    name = t.name
                    surname = ""
                #this is assigning ticker owner/buyer name:
                elif t.user.first_name and t.user.last_name:
                    name = t.user.first_name
                    surname = t.user.last_name
                elif t.user.first_name:
                    name = t.user.first_name
                elif t.user.email:
                    name = t.user.email
                    surname = ""
                else:
                    name = ""
                    surname = ""



            #tickets = TicketConference.objects.available(s.user, conference).filter(fare__ticket_type='conference')

            row = {
                COL_NAME: name,
		        COL_SURNAME: surname,
 		        COL_TAG: tagline,
                COL_AFILIATION: affiliation,
                COL_EXP: p_exp,
                COL_SHIRT: shirt,
                COL_EMAIL: email,
                COL_PHONE: phone,
                COL_COMWEB: comp,
                COL_PERWEB: per
            }
            writer.writerow(utf8(row))
