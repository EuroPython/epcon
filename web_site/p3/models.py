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

from conference.models import Ticket, ConferenceTaggedItem, AttendeeProfile
from taggit.managers import TaggableManager

import logging
log = logging.getLogger('p3.models')

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
            # TODO: drop in favore di dataaccess.user_tickets
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
    badge_image = models.ImageField(
        null=True, blank=True,
        upload_to='p3/tickets/badge_image',
        help_text='''A custom badge image instead of the python logo. Don't use a very large image, 250x250 should be fine.''')
    assigned_to = models.EmailField(blank=True)

    objects = TicketConferenceManager()

    def profile(self):
        if self.assigned_to:
            return AttendeeProfile.objects.get(user__email=self.assigned_to)
        else:
            return AttendeeProfile.objects.get(user=self.ticket.user)

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

HOTELROOM_ROOM_TYPE = (
    ('t1', 'Single room'),
    ('t2', 'Double room'),
    ('t3', 'Triple room'),
    ('t4', 'Quadruple room'),
)
class HotelRoom(models.Model):
    conference = models.ForeignKey('conference.Conference')
    room_type = models.CharField(max_length=2, choices=HOTELROOM_ROOM_TYPE)
    quantity = models.PositiveIntegerField()
    amount = models.CharField(max_length=50, help_text='''
        Costo della camera per notte.
        <ul>
            <li>10x1,8x2,7x3 significa: 10 € per una notte, 8 a notte per due notti, 7 a notte per 3 notti.</li>
            <li>10 significa: 10 € a notte</li>
            <li>7,12x1,8x2 significa: 12 € per una notte, 8 a notte per due notti, 7 a notte per tutti gli altri periodi</li>
        </ul>
    ''')

    class Meta:
        unique_together = (('conference', 'room_type'),)

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
        """
        costo del singolo posto letto per `days` giorni
        """
        if days <= 0 or not self.amount:
            return 0
        rules = self._calc_rules()
        try:
            price = rules[days]
        except KeyError:
            price = rules.get(None, 0)
        return days * price

    def beds(self):
        """
        numero di posti letto in camera
        """
        return int(self.room_type[1])

class TicketRoomManager(models.Manager):
    def valid_tickets(self):
        # prima di tutto individuo i biglietti validi; sono quelli il cui
        # ordine è confermato o, nel caso di ordini con bonifico bancario, sono
        # avvenuti di "recente"...
        incomplete_limit = datetime.date.today() - datetime.timedelta(days=15)
        return TicketRoom.objects\
            .filter(ticket__fare__conference=dsettings.CONFERENCE_CONFERENCE)\
            .filter(
                Q(ticket__orderitem__order___complete=True)
                | Q(ticket__orderitem__order__method='bank', ticket__orderitem__order__created__gte=incomplete_limit)
            )

    def overall_status(self):
        periods = self.valid_tickets()\
            .values_list('checkin', 'checkout')\
            .distinct()
        output = {}
        for p in periods:
            output[tuple(p)] = self.beds_status(p)
        return output

    def beds_status(self, period):
        """
        Calcola la situazione dei posti letto nel periodo specificato; il
        valore di ritorno è un dict che associa al tipo stanza la quantità di
        camere disponibili e libere:
        {
            't2': {
                'available': X,
                'reserved': Y,
                'free': Z, # Z = X - Y
            }
        }
        """
        # estraggo solo su quelli che hanno almeno un giorno prenotato nel
        # periodo che mi interessa
        start, end = period
        tickets = self.valid_tickets()\
            .filter(
                Q(checkin__lte=start, checkout__gte=end)
                | Q(checkin__gt=start, checkin__lt=end)
                | Q(checkout__gt=start, checkout__lt=end)
            )

        tickets = tickets.select_related('room_type')

        status = defaultdict(lambda: { 'available': 0, 'free': 0, 'reserved': 0 })
        for t in tickets:
            status[t.room_type.room_type]['reserved'] += 1

        for hr in HotelRoom.objects.filter(conference=dsettings.CONFERENCE_CONFERENCE):
            s = status[hr.room_type]
            s['available'] = hr.quantity * hr.beds()
            s['free'] = s['available'] - s['reserved']
        return dict(status)

    def can_be_booked(self, items):
        """
        Dato un elenco di richieste:
            items = [
                (room_type, qty, period),
                ...
            ]

        restitusice true se possono essere tutte soddisfatte in blocco.
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
    ('B', 'room shared'),
    ('R', 'room not shared'),
)
class TicketRoom(models.Model):
    ticket = models.OneToOneField(Ticket, related_name='p3_conference_room')
    document = models.FileField(
        verbose_name='ID Document',
        upload_to=_ticket_sim_upload_to,
        storage=dsettings.SECURE_STORAGE,
        blank=True,
        help_text='Italian regulations require a document ID to book an hotel room. Any document is fine (EU driving license, personal ID card, etc).',
    )
    room_type = models.ForeignKey(HotelRoom)
    ticket_type = models.CharField(max_length=1, choices=TICKETROOM_TICKET_TYPE)
    checkin = models.DateField(db_index=True)
    checkout = models.DateField(db_index=True)
    unused = models.BooleanField(default=False)

    objects = TicketRoomManager()

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
    def by_tags(self, tags, ignore_case=False):
        if ignore_case:
            from conference.models import ConferenceTag
            names = []
            for t in tags:
                names.extend(ConferenceTag.objects\
                    .filter(name__iexact=t)\
                    .values_list('name', flat=True))
            tags = names
        return P3Profile.objects\
            .filter(interests__name__in=tags)\
            .distinct()

class P3Profile(models.Model):
    profile = models.OneToOneField('conference.AttendeeProfile', related_name='p3_profile', primary_key=True)
    tagline = models.CharField(max_length=60, blank=True, help_text='describe yourself in one line!')
    interests = TaggableManager(through=ConferenceTaggedItem)
    twitter = models.CharField(max_length=80, blank=True)
    image_gravatar = models.BooleanField(default=False)
    image_url = models.URLField(max_length=500, verify_exists=False, blank=False)
    country = models.CharField(max_length=2, blank=True, default='', db_index=True)

    spam_recruiting = models.BooleanField(default=False)
    spam_user_message = models.BooleanField(default=False)
    spam_sms = models.BooleanField(default=False)

    objects = P3ProfileManager()

    def profile_image_url(self, anonymous=True):
        from p3 import utils
        if self.profile.visibility != 'x':
            if self.image_gravatar:
                return utils.gravatar(self.profile.user.email)
            elif self.image_url:
                if anonymous:
                    return reverse('p3-profile-avatar', kwargs={'slug': self.profile.slug})
                else:
                    return self.image_url
            elif self.profile.image:
                return self.profile.image.url
        return dsettings.STATIC_URL + 'p5/i/headshot-default.jpg'

    def send_user_message(self, from_, subject, message):
        from conference.models import Conference, AttendeeLink
        if not self.spam_user_message:
            # esiste un link tra i due utenti, il messaggio è consentito
            # nonostante spam_user_message
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
                'Sender': 'info@pycon.it',
            }
        ).send()
        log.info('email from "%s" to "%s" sent', from_.email, self.profile.user.email)

import p3.listeners
