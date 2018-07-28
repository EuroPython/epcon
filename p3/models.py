# -*- coding: UTF-8 -*-
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

    def __getattr__(self, name):
        return getattr(self.all(), name)

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

if 0: # FIXME: remove hotels and sim

    ## TODO: remove SIM card acquisition options?
    def _ticket_sim_upload_to(instance, filename):
        subdir = 'p3/personal_documents'

        # Adding the ticket id in the filename because a single user can
        # buy multiple sims and probably they're not all for the same person.
        fname = '%s-%s' % (instance.ticket.user.username, instance.ticket.id)
        fdir = os.path.join(dsettings.SECURE_MEDIA_ROOT, subdir)
        for f in os.listdir(fdir):
            if os.path.splitext(f)[0] == fname:
                os.unlink(os.path.join(fdir, f))
                break
        fpath = os.path.join(subdir, fname + os.path.splitext(filename)[1].lower())
        # There's some strange interaction between django and python, and if
        # a non-unicode string containing non-ascii chars is used it's transformed
        # in unicode correctly, but later it's passed to os.stat that will
        # call str() on it. The solution is to return only an ascii string.
        if not isinstance(fpath, unicode):
            fpath = unicode(fpath, 'utf-8')
        return fpath.encode('ascii', 'ignore')

    TICKET_SIM_TYPE = (
        ('std', _('Standard SIM (USIM)')),
        ('micro', _('Micro SIM')),
        ('nano', _('Nano SIM')),
    )
    TICKET_SIM_PLAN_TYPE = (
        ('std', _('Standard Plan')),
        ('bb', _('BlackBerry Plan')),
    )


    class TicketSIM(models.Model):
        ticket = models.OneToOneField(Ticket, related_name='p3_conference_sim')
        document = models.FileField(
            verbose_name=_('ID Document'),
            upload_to=_ticket_sim_upload_to,
            storage=get_secure_storage(),
            blank=True,
            help_text=_('Italian regulations require a document ID to activate a phone SIM. You can use the same ID for up to three SIMs. Any document is fine (EU driving license, personal ID card, etc).'))
        sim_type = models.CharField(
            max_length=5,
            choices=TICKET_SIM_TYPE,
            default='std',
            help_text=_('Select the SIM physical format. USIM is the sandard for most mobile phones; Micro SIM is notably used on iPad and iPhone 4; Nano SIM is used for the last generation smartphone like the iPhone 5'))
        plan_type = models.CharField(
            max_length=3,
            choices=TICKET_SIM_PLAN_TYPE,
            default='std',
            help_text=_('Standard plan is fine for all mobiles except BlackBerry that require a special plan (even though rates and features are exactly the same).'))
        number = models.CharField(
            max_length=20, blank=True, help_text=_("Telephone number"))


    ## TODO: remove Hotel Room management?
    class HotelBooking(models.Model):
        """
        Hotel booking rules for a given conference.
        """
        conference = models.ForeignKey('conference.Conference')
        booking_start = models.DateField(help_text=_("first bookable day"))
        booking_end = models.DateField(help_text=_("last bookable day"))
        default_start = models.DateField(
            help_text=_("suggested first bookable day (used in the cart as the default start day)"))
        default_end = models.DateField(
            help_text=_("suggested last bookable day (used in the cart as the default last day)"))
        minimum_night = models.PositiveIntegerField(default=1)

        def __unicode__(self):
            return '{}: {}-{}'.format(self.conference_id, self.booking_start, self.booking_end)


    HOTELROOM_ROOM_TYPE = (
        ('t1', _('Single room')),
        ('t2', _('Double room')),
        ('t3', _('Triple room')),
        ('t4', _('Quadruple room')),
    )
    class HotelRoom(models.Model):
        booking = models.ForeignKey(HotelBooking)
        room_type = models.CharField(max_length=2, choices=HOTELROOM_ROOM_TYPE)
        quantity = models.PositiveIntegerField()
        amount = models.CharField(max_length=100, help_text="""
            Room cost per night.
            <ul>
                <li>10x1,8x2,7x3 means: 10.00€ for one night, 8.00€/night for 2 nights, 7.00€/night for 3 nights.</li>
                <li>10 means: 10.00€/night</li>
                <li>7,12x1,8x2 means: 12.00€ for one night, 8.00€/night for 2 nights, 7.00€/night for longer periods</li>
            </ul>
        """)

        class Meta:
            unique_together = (('booking', 'room_type'),)

        def __unicode__(self):
            return '%s: %s' % (self.conference, self.get_room_type_display())

        def clean(self):
            try:
                self._calc_rules()
            except (TypeError, ValueError):
                from django.core.exceptions import ValidationError
                raise ValidationError('Invalid "amount" value')

        def _calc_rules(self):
            rules = {}
            if self.amount:
                for rule in self.amount.split(','):
                    if 'x' in rule:
                        amount, days = rule.split('x')
                        amount = float(amount)
                        days = int(days)
                    else:
                        amount = float(rule)
                        days = None
                    rules[days] = amount
            return rules

        def price(self, days):
            """Cost of each bed for `days` days."""
            if days <= 0 or not self.amount:
                return 0
            rules = self._calc_rules()
            try:
                price = rules[days]
            except KeyError:
                price = rules.get(None, 0)
            return days * price

        def beds(self):
            """Number of beds in the room."""
            return int(self.room_type[1])


    class TicketRoomManager(models.Manager):
        def valid_tickets(self):
            # First of all valid tickets are selected; only the ones for which
            # the order has been confirmed or, in case of bank transfer payment,
            # happened "recently"...
            incomplete_limit = datetime.date.today() - datetime.timedelta(days=60)
            return TicketRoom.objects\
                .filter(ticket__fare__conference=dsettings.CONFERENCE_CONFERENCE)\
                .filter(
                    Q(ticket__orderitem__order___complete=True)
                    | Q(
                        ticket__orderitem__order__method='bank',
                        ticket__orderitem__order__created__gte=incomplete_limit))

        def reserved_days(self):
            qs = self.valid_tickets()\
                .values('checkin', 'checkout')\
                .distinct()
            days = set()
            inc = datetime.timedelta(days=1)
            for t in qs:
                start = t['checkin']
                while start <= t['checkout']:
                    days.add(start)
                    start += inc
            return sorted(days)

        def overall_status(self):
            qs = self.valid_tickets()\
                .values('checkin', 'checkout', 'room_type__room_type')
            inc = datetime.timedelta(days=1)

            rooms = HotelRoom.objects\
                .filter(booking__conference=dsettings.CONFERENCE_CONFERENCE)

            booking = HotelBooking.objects\
                .get(conference=dsettings.CONFERENCE_CONFERENCE)

            period = {}
            start = booking.booking_start
            while start <= booking.booking_end:
                period[start] = {}
                for hr in rooms:
                    period[start][hr.room_type] = {
                        'available': hr.quantity * hr.beds(),
                        'reserved': 0,
                        'free': 0,
                    }
                start += inc

            for t in qs:
                rt = t['room_type__room_type']
                start = t['checkin']
                while start < t['checkout']:
                    period[start][rt]['reserved'] += 1
                    start += inc

            for dstatus in period.values():
                for hr in rooms:
                    s = dstatus[hr.room_type]
                    s['free'] = s['available'] - s['reserved']
            return period

        def beds_status(self, period):
            """ Compute the situation of the beds in the specified period.
            The return value is a dict that associates the type of room to the
            quantity of rooms available and free.
            Example:
            {
                't2': {
                    'available': X,
                    'reserved': Y,
                    'free': Z, # Z = X - Y
                }
            }
            """
            start, end = period
            inc = datetime.timedelta(days=1)

            # the presence of a well defined period could suggest touse an ad-hoc
            # query (like it was done in previous implementation), it's important
            # however to pay attention to adjacent bookings, i.e. those bookings
            # that may share the same selected period because one is ending before
            # the other. For example:
            #
            # start = 2/7
            # end = 6/7
            #
            # tickets:
            #   1, 2/7 -> 8/7
            #   2, 30/6 -> 3/7
            #   3, 5/7 -> 10/7
            #
            # despite there are 3 tickets in the selected period the used beds
            # are only 2 because ticket #2 and #3 can share the same room.
            #
            # For this reason the `overall_status` is used as, even if being a
            # little slower, it handles correctly these cases.
            reservations = self.overall_status()
            output = reservations[start]

            start += inc
            while start <= end:
                day_status = reservations[start]
                for room_type, room_status in day_status.items():
                    if output[room_type]['free'] > room_status['free']:
                        output[room_type] = room_status
                start += inc
            return output

        def can_be_booked(self, items):
            """ Given a list of requirements:
                items = [
                    (room_type, qty, period),
                    ...
                ]

            return True if they can all be met collectively.
            """
            grouped = defaultdict(lambda: defaultdict(lambda: 0))
            for room, beds, period in items:
                grouped[tuple(period)][room] += beds
            for period, rooms in grouped.items():
                hstatus = self.beds_status(period)
                for room_type, beds in rooms.items():
                    if hstatus[room_type]['free'] < beds:
                        raise ValueError((period, room_type))
            return True

    TICKETROOM_TICKET_TYPE = (
        ('B', _('room shared')),
        ('R', _('room not shared')),
    )
    class TicketRoom(models.Model):
        ticket = models.OneToOneField(Ticket, related_name='p3_conference_room')
        document = models.FileField(
            verbose_name=_('ID Document'),
            upload_to=_ticket_sim_upload_to,
            storage=get_secure_storage(),
            blank=True,
            help_text=_('Italian regulations require a document ID to book an hotel room. '
                        'Any document is fine (EU driving license, personal ID card, etc).'))
        room_type = models.ForeignKey(HotelRoom)
        ticket_type = models.CharField(max_length=1, choices=TICKETROOM_TICKET_TYPE)
        checkin = models.DateField(db_index=True)
        checkout = models.DateField(db_index=True)
        unused = models.BooleanField(
            default=False,
            verbose_name=_("Bed place not needed"),
            help_text=_('Check if you don\'t use this bed place.'))

        objects = TicketRoomManager()

        def __unicode__(self):
            return '%s (%s) %s -> %s' % (self.room_type.get_room_type_display(),
                                         self.get_ticket_type_display(),
                                         self.checkin, self.checkout)


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
