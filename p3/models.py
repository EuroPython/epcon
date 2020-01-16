from django.conf import settings as dsettings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext as _
from assopy import utils as autils

import conference.gravatar
from conference.models import Ticket, ConferenceTaggedItem, AttendeeProfile
from taggit.managers import TaggableManager

import logging
log = logging.getLogger('p3.models')

# Configurable sub-communities
TALK_SUBCOMMUNITY = dsettings.CONFERENCE_TALK_SUBCOMMUNITY


class SpeakerConference(models.Model):
    speaker = models.OneToOneField('conference.Speaker', related_name='p3_speaker', on_delete=models.CASCADE)
    first_time = models.BooleanField(default=False)

# Configurable t-shirt sizes, diets, experience
TICKET_CONFERENCE_SHIRT_SIZES = dsettings.CONFERENCE_TICKET_CONFERENCE_SHIRT_SIZES
TICKET_CONFERENCE_DIETS = dsettings.CONFERENCE_TICKET_CONFERENCE_DIETS
TICKET_CONFERENCE_EXPERIENCES = dsettings.CONFERENCE_TICKET_CONFERENCE_EXPERIENCES


class TicketConferenceQuerySet(models.QuerySet):
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
        related_name='p3_conference',
        on_delete=models.CASCADE)

    name = models.CharField(
        max_length=255,
        help_text="What name should appear on the badge?",
        blank=True,
    )

    shirt_size = models.CharField(
        max_length=5,
        choices=TICKET_CONFERENCE_SHIRT_SIZES,
        null=True,
        default=None)
    python_experience = models.PositiveIntegerField(
        choices=TICKET_CONFERENCE_EXPERIENCES,
        null=True,
        default=0)
    diet = models.CharField(
        choices=TICKET_CONFERENCE_DIETS,
        max_length=10,
        null=True,
        default=None)
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
        help_text=_("Email of the attendee for whom this ticket was bought."))

    objects = TicketConferenceQuerySet.as_manager()

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
    profile = models.OneToOneField(
        'conference.AttendeeProfile', related_name='p3_profile', primary_key=True, on_delete=models.CASCADE)
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
        if self.image_gravatar:
            return conference.gravatar.gravatar(self.profile.user.email)
        elif self.image_url:
            return self.image_url
        elif self.profile.image:
            return self.profile.image.url
        return dsettings.STATIC_URL + dsettings.P3_ANONYMOUS_AVATAR

    def public_profile_image_url(self):
        """ Like `profile_image_url` but takes into account the visibility rules of the profile."""
        if self.profile.visibility != 'x':
            url = self.profile_image_url()
            if url == self.image_url:
                return reverse('p3-profile-avatar', kwargs={'slug': self.profile.slug})
            return url
        return dsettings.STATIC_URL + dsettings.P3_ANONYMOUS_AVATAR


#TODO: what is this import doing here?!
import p3.listeners
