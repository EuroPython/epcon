__author__ = 'oier'

# -*- coding: UTF-8 -*-

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

        attendees = TicketConference.objects.all()
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

        for t in attendees:
            #profile = models.AttendeeProfile.objects.get(user=s.user)
            profile = t.profile()
            if profile.job_title and profile.company:
                affiliation = profile.job_title + " @ " + profile.company
            elif profile.job_title:
                affiliation = profile.job_title
            elif profile.company:
                affiliation = profile.company
            else:
                affiliation = ""
            #tickets = TicketConference.objects.available(s.user, conference).filter(fare__ticket_type='conference')
            row = {
                COL_NAME: profile.user.first_name,
		        COL_SURNAME: profile.user.last_name,
 		        COL_TAG: t.tagline,
                COL_AFILIATION: affiliation,
                COL_EXP: t.python_experience,
                COL_SHIRT: t.shirt_size,
                COL_EMAIL: profile.user.email,
                COL_PHONE: profile.phone,
                COL_COMWEB: profile.company_homepage,
                COL_PERWEB: profile.personal_homepage
            }
            writer.writerow(utf8(row))
