# -*- coding: utf-8 -*-
import datetime
import os
import os.path
from collections import defaultdict

from django.conf import settings as dsettings
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils.translation import ugettext as _
from assopy import utils as autils

from conference.models import (Ticket,
                               ConferenceTaggedItem,
                               AttendeeProfile)
from taggit.managers import TaggableManager
from .helpers import get_secure_storage

import logging
log = logging.getLogger('p3.models')

# Configurable sub-communities
TALK_SUBCOMMUNITY = dsettings.CONFERENCE_TALK_SUBCOMMUNITY


class P3Talk(models.Model):
    """
    Estensione del talk di conference per l'utilizzo da parte di P3
    """
    talk = models.OneToOneField('conference.Talk',
                                related_name='p3_talk',
                                primary_key=True)
    sub_community = models.CharField(max_length=20,
                                     choices=TALK_SUBCOMMUNITY,
                                     default='')


class SpeakerConference(models.Model):
    speaker = models.OneToOneField('conference.Speaker', related_name='p3_speaker')
    first_time = models.BooleanField(default=False)

# Configurable t-shirt sizes, diets, experience
TICKET_CONFERENCE_SHIRT_SIZES = dsettings.CONFERENCE_TICKET_CONFERENCE_SHIRT_SIZES
TICKET_CONFERENCE_DIETS = dsettings.CONFERENCE_TICKET_CONFERENCE_DIETS
TICKET_CONFERENCE_EXPERIENCES = dsettings.CONFERENCE_TICKET_CONFERENCE_EXPERIENCES


class TicketConferenceManager(models.Manager):
    def get_queryset(self):
        return self._QuerySet(self.model)

    # def __getattr__(self, name):
    #     return getattr(self.all(), name)

    class _QuerySet(QuerySet):
        def available(self, user, conference=None):
            """
            restituisce il qs con i biglietti disponibili per l'utente;
            disponibili significa comprati dall'utente o assegnati a lui.
            """
            # TODO: drop in favor of dataaccess.user_tickets
            q1 = user.ticket_set.all()
            if conference:
                q1 = q1.conference(conference)

            q2 = Ticket.objects.filter(p3_conference__assigned_to=user.email)
            if conference:
                q2 = q2.filter(fare__conference=conference)

            return q1 | q2


class TicketConference(models.Model):
    ticket = models.OneToOneField(
        Ticket,
        related_name='p3_conference')
    shirt_size = models.CharField(
        max_length=5,
        choices=TICKET_CONFERENCE_SHIRT_SIZES,
        default='l')
    python_experience = models.PositiveIntegerField(
        choices=TICKET_CONFERENCE_EXPERIENCES,
        null=True,
        default=0)
    diet = models.CharField(
        choices=TICKET_CONFERENCE_DIETS,
        max_length=10,
        default='omnivorous')
    tagline = models.CharField(
        max_length=60,
        blank=True,
        help_text=_('a (funny?) tagline that will be displayed on the badge<br />'
                    'Eg. CEO of FooBar Inc.; Super Python fanboy; Simple is better than complex.'))
    days = models.TextField(
        verbose_name=_('Days of attendance'),
        blank=True)
    badge_image = models.ImageField(
        null=True,
        blank=True,
        upload_to='p3/tickets/badge_image',
        help_text=_("A custom badge image instead of the python logo."
                    "Don't use a very large image, 250x250 should be fine."))
    assigned_to = models.EmailField(
        blank=True,
        help_text=_("EMail of the attendee for whom this ticket was bought."))

    objects = TicketConferenceManager()

    def __str__(self):
        return "for ticket: %s" % self.ticket

    def profile(self):
        if self.assigned_to:
            # Ticket assigned to someone else
            user = autils.get_user_account_from_email(self.assigned_to)
        else:
            # Ticket assigned to the buyer
            user = self.ticket.user
        return AttendeeProfile.objects.get(user=user)


class P3ProfileManager(models.Manager):
    def by_tags(self, tags, ignore_case=True, conf=dsettings.CONFERENCE_CONFERENCE):
        if ignore_case:
            from conference.models import ConferenceTag
            names = []
            for t in tags:
                names.extend(ConferenceTag.objects\
                    .filter(name__iexact=t)\
                    .values_list('name', flat=True))
            tags = names
        from p3 import dataaccess
        return P3Profile.objects\
            .filter(interests__name__in=tags)\
            .filter(profile__user__in=dataaccess.conference_users(conf))\
            .distinct()


class P3Profile(models.Model):
    profile = models.OneToOneField('conference.AttendeeProfile', related_name='p3_profile', primary_key=True)
    tagline = models.CharField(
        max_length=60, blank=True, help_text=_('describe yourself in one line!'))
    interests = TaggableManager(through=ConferenceTaggedItem)
    twitter = models.CharField(max_length=80, blank=True)
    image_gravatar = models.BooleanField(default=False)
    image_url = models.URLField(max_length=500, blank=False)
    country = models.CharField(max_length=2, blank=True, default='', db_index=True)

    spam_recruiting = models.BooleanField(default=False)
    spam_user_message = models.BooleanField(default=False)
    spam_sms = models.BooleanField(default=False)

    objects = P3ProfileManager()

    def profile_image_url(self):
        """Return the url of the image that the user has associated with his profile."""
        from p3 import utils
        if self.image_gravatar:
            return utils.gravatar(self.profile.user.email)
        elif self.image_url:
            return self.image_url
        elif self.profile.image:
            return self.profile.image.url
        return dsettings.STATIC_URL + dsettings.P3_ANONYMOUS_AVATAR

    def public_profile_image_url(self):
        """ Like `profile_image_url` but takes into account the visibility rules of the profile."""
        # import pdb; pdb.set_trace()
        if self.profile.visibility != 'x':
            url = self.profile_image_url()
            if url == self.image_url:
                return reverse('p3-profile-avatar', kwargs={'slug': self.profile.slug})
            return url
        return dsettings.STATIC_URL + dsettings.P3_ANONYMOUS_AVATAR


    def send_user_message(self, from_, subject, message):
        from conference.models import Conference, AttendeeLink
        if not self.spam_user_message:
            # If there's a link between the two users the message is allowed
            # despite spam_user_message
            try:
                AttendeeLink.objects.getLink(from_.id, self.profile_id)
            except AttendeeLink.DoesNotExist:
                raise ValueError("This user does not want to receive a message")
        if not from_.email:
            raise ValueError("Sender without an email address")
        if not self.profile.user.email:
            raise ValueError("Recipient without an email address")

        from p3.dataaccess import all_user_tickets
        conf = Conference.objects.current()

        tickets = [
            tid
            for tid, ftype, _, complete in all_user_tickets(from_.id, conf.code)
            if ftype == 'conference' and complete
        ]
        if not tickets:
            raise ValueError("User without a valid ticket")

        if not conf.conference_end  or datetime.date.today() > conf.conference_end:
            raise ValueError("conference %s is ended" % conf.code)

        from django.core.mail import EmailMessage
        EmailMessage(
            subject=subject, body=message + dsettings.P3_USER_MESSAGE_FOOTER,
            from_email=from_.email,
            to=[self.profile.user.email],
            headers={
                'Sender': 'info@europython.eu',
            }
        ).send()
        log.info('email from "%s" to "%s" sent', from_.email, self.profile.user.email)


#TODO: what is this import doing here?!
import p3.listeners
