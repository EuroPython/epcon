# -*- coding: UTF-8 -*-
import os
import os.path

from django.conf import settings as dsettings
from django.db import models
from django.db.models.query import QuerySet

from conference.models import Ticket

TICKET_CONFERENCE_SHIRT_SIZES = (
    ('fs', 'S (female)'),
    ('fm', 'M (female)'),
    ('fl', 'L (female)'),
    ('fxl', 'XL (female)'),
    ('fxxl', 'XXL (female)'),
    ('s', 'S (male)'),
    ('m', 'M (male)'),
    ('l', 'L (male)'),
    ('xl', 'XL (male)'),
    ('xxl', 'XXL (male)'),
)
TICKET_CONFERENCE_DIETS = (
    ('omnivorous', 'Omnivorous'),
    ('vegetarian', 'Vegetarian'),
    #('vegan', 'Vegan'),
    #('kosher', 'Kosher'),
)
TICKET_CONFERENCE_EXPERIENCES = (
    (0, '0'),
    (1, '1'),
    (2, '2'),
    (3, '3'),
    (4, '4'),
    (5, '5'),
)
class TicketConferenceManager(models.Manager):
    def get_query_set(self):
        return self._QuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.all(), name)

    class _QuerySet(QuerySet):
        def available(self, user, conference=None):
            """
            restituisce il qs con i biglietti disponibili per l'utente;
            disponibili significa comprati dall'utente o assegnati a lui.
            """
            q1 = user.ticket_set.all()
            if conference:
                q1 = q1.conference(conference)

            q2 = Ticket.objects.filter(p3_conference__assigned_to=user.email)
            if conference:
                q2 = q2.filter(fare__conference=conference)

            return q1 | q2
    
class TicketConference(models.Model):
    ticket = models.OneToOneField(Ticket, related_name='p3_conference')
    shirt_size = models.CharField(max_length=4, choices=TICKET_CONFERENCE_SHIRT_SIZES, default='l')
    python_experience = models.PositiveIntegerField(choices=TICKET_CONFERENCE_EXPERIENCES, default=0)
    diet = models.CharField(max_length=10, choices=TICKET_CONFERENCE_DIETS, default='omnivorous')
    tagline = models.CharField(max_length=60, blank=True, help_text='a (funny?) tagline that will be displayed on the badge<br />Eg. CEO of FooBar Inc.; Student at MIT; Super Python fanboy')
    days = models.TextField(verbose_name='Days of attendance', blank=True)
    assigned_to = models.EmailField(blank=True)

    objects = TicketConferenceManager()

def _ticket_sim_upload_to(instance, filename):
    subdir = 'p3/personal_documents'
    fname = instance.ticket.user.username
    fdir = os.path.join(dsettings.MEDIA_ROOT, subdir)
    for f in os.listdir(fdir):
        if os.path.splitext(f)[0] == fname:
            os.unlink(os.path.join(fdir, f))
            break
    return os.path.join(subdir, fname + os.path.splitext(filename)[1])

TICKET_SIM_TYPE = (
    ('std', 'SIM Standard'),
    ('micro', 'Micro SIM'),
)
TICKET_SIM_PLAN_TYPE = (
    ('std', 'Standard'),
    ('bb', 'BlackBerry'),
)
class TicketSIM(models.Model):
    ticket = models.OneToOneField(Ticket, related_name='p3_conference_sim')
    document = models.FileField(verbose_name='ID Document', upload_to=_ticket_sim_upload_to, blank=True, help_text='')
    sim_type = models.CharField(max_length=5, choices=TICKET_SIM_TYPE, default='std')
    plan_type = models.CharField(max_length=3, choices=TICKET_SIM_PLAN_TYPE, default='std')

class Donation(models.Model):
    user = models.ForeignKey('assopy.User')
    date = models.DateField()
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    message = models.TextField(blank=True)

    def __unicode__(self):
        return '%s donation of %s' % (self.user.name(), self.date)

import p3.listeners
