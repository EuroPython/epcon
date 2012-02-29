# -*- coding: UTF-8 -*-
import os
import os.path

from django.conf import settings as dsettings
from django.db import models
from django.db.models.query import QuerySet

from conference.models import Ticket, ConferenceTaggedItem
from taggit.managers import TaggableManager

class SpeakerConference(models.Model):
    speaker = models.OneToOneField('conference.Speaker', related_name='p3_speaker')
    first_time = models.BooleanField(default=False)

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
    # inserisco anche l'id del biglietto nel nome del file perché un utente può
    # acquistare più sim e probabilmente non sono tutte per lui.
    fname = '%s-%s' % (instance.ticket.user.username, instance.ticket.id)
    fdir = os.path.join(dsettings.SECURE_MEDIA_ROOT, subdir)
    for f in os.listdir(fdir):
        if os.path.splitext(f)[0] == fname:
            os.unlink(os.path.join(fdir, f))
            break
    return os.path.join(subdir, fname + os.path.splitext(filename)[1].lower())

TICKET_SIM_TYPE = (
    ('std', 'Standard SIM (USIM)'),
    ('micro', 'Micro SIM'),
)
TICKET_SIM_PLAN_TYPE = (
    ('std', 'Standard Plan'),
    ('bb', 'BlackBerry Plan'),
)
class TicketSIM(models.Model):
    ticket = models.OneToOneField(Ticket, related_name='p3_conference_sim')
    document = models.FileField(
        verbose_name='ID Document',
        upload_to=_ticket_sim_upload_to,
        storage=dsettings.SECURE_STORAGE,
        blank=True,
        help_text='Italian regulations require a document ID to activate a phone SIM. You can use the same ID for up to three SIMs. Any document is fine (EU driving license, personal ID card, etc).',
    )
    sim_type = models.CharField(
        max_length=5,
        choices=TICKET_SIM_TYPE,
        default='std',
        help_text='Select the SIM physical format. USIM is the sandard for most mobile phones; Micro SIM is notably used on iPad and iPhone 4.',
    )
    plan_type = models.CharField(
        max_length=3,
        choices=TICKET_SIM_PLAN_TYPE,
        default='std',
        help_text='Standard plan is fine for all mobiles except BlackBerry that require a special plan (even though rates and features are exactly the same).',
    )

class Donation(models.Model):
    user = models.ForeignKey('assopy.User')
    date = models.DateField()
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    message = models.TextField(blank=True)

    def __unicode__(self):
        return '%s donation of %s' % (self.user.name(), self.date)

class Sprint(models.Model):
    user = models.ForeignKey('assopy.User')
    conference = models.ForeignKey('conference.Conference')
    title = models.CharField(max_length=150)
    abstract = models.TextField(blank=True)

class SprintPresence(models.Model):
    sprint = models.ForeignKey(Sprint)
    user = models.ForeignKey('assopy.User')

class P3Profile(models.Model):
    profile = models.OneToOneField('conference.AttendeeProfile', related_name='p3_profile', primary_key=True)
    interests = TaggableManager(through=ConferenceTaggedItem)
    twitter = models.CharField(max_length=80, blank=True)
    image_gravatar = models.BooleanField(default=False)
    image_url = models.URLField(max_length=500, verify_exists=False, blank=False)

    spam_recruiting = models.BooleanField(default=False)
    spam_user_message = models.BooleanField(default=False)
    spam_sms = models.BooleanField(default=False)

import p3.listeners
