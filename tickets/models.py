# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import ugettext as _
from conference.models import Conference, AttendeeProfile
from django.conf import settings
import datetime
import os


class FareManager(models.Manager):
	def get_query_set(self):
		return self._QuerySet(self.model)

	def __getattr__(self, name):
		return getattr(self.all(), name)

	class _QuerySet(QuerySet):
		def available(self, conference=None):
			today = datetime.date.today()
			q1 = models.Q(start_validity=None, end_validity=None)
			q2 = models.Q(start_validity__lte=today, end_validity__gte=today)
			qs = self.filter(q1 | q2)
			if conference:
				qs = qs.filter(conference=conference)
			return qs

FARE_TICKET_TYPES = (
	('conference', 'Conference ticket'),
	('partner', 'Partner Program'),
	('event', 'Event'),
	('other', 'Other'),
)

FARE_PAYMENT_TYPE = (
	('p', 'Payment'),
	('v', 'Voucher'),
	('d', 'Deposit'),
)

FARE_TYPES = (
	('c', 'Company'),
	('s', 'Student'),
	('p', 'Personal'),
)


class Fare(models.Model):
	conference = models.ForeignKey(Conference)
	code = models.CharField(max_length=10)
	name = models.CharField(max_length=100)
	description = models.TextField()
	price = models.DecimalField(max_digits=6, decimal_places=2)
	start_validity = models.DateField(null=True)
	end_validity = models.DateField(null=True)
	recipient_type = models.CharField(max_length=1, choices=FARE_TYPES, default='p')
	ticket_type = models.CharField(max_length=10, choices=FARE_TICKET_TYPES, default='conference', db_index=True)
	payment_type = models.CharField(max_length=1, choices=FARE_PAYMENT_TYPE, default='p')
	tickets_qty = models.IntegerField(
							help_text='No. of tickets available for this fare',
							null=True, blank=True, default=0)
	blob = models.TextField(blank=True)

	objects = FareManager()

	def __unicode__(self):
		return '%s - %s' % (self.code, self.conference)

	class Meta:
		unique_together = (('conference', 'code'),)

	def valid(self):
		today = datetime.date.today()
		validity = self.start_validity <= today <= self.end_validity
		return validity

	def calculated_price(self, qty=1, **kw):
		from conference.listeners import fare_price
		params = dict(kw)
		params['qty'] = qty
		calc = {
			'total': self.price * qty,
			'params': params,
		}
		fare_price.send(sender=self, calc=calc)
		return calc['total']

	def no_of_admissions(self):
		# number of tickets sold for each fare. (Relating to the tickets obj)
		tk = Ticket.objects.filter(fare=self).count()
		return tk

	def is_soldout(self):
		"""
		Return true if the difference between the ticket qty and the numer of
		admissions is equal to 0. I want to control if fare is still available
		or not.
		"""
		return True if self.tickets_qty-self.no_of_admissions() == 0 else False

	def create_tickets(self, user):
		"""
		Crea e ritorna i biglietti associati a questa tariffa.
		Normalmente ogni tariffa comporta un solo biglietto, ma questo
		comportamento è modificabile da un listener collegato al segnale
		fare_tickets.

		Le istanze ritornate da questo metodo hanno un attributo aggiuntivo
		`fare_description` (volatile) che riporta una descrizione della tariffa
		specifica per il singolo biglietto.
		"""
		from conference.listeners import fare_tickets
		params = {
			'user': user,
			'tickets': []
		}
		fare_tickets.send(sender=self, params=params)
		if not params['tickets']:
			t = Ticket(user=user, fare=self)
			t.fare_description = self.name
			t.save()
			params['tickets'].append(t)
		return params['tickets']


class TicketManager(models.Manager):
	def get_query_set(self):
		return self._QuerySet(self.model)

	def __getattr__(self, name):
		return getattr(self.all(), name)

	class _QuerySet(QuerySet):
		def conference(self, conference):
			return self.filter(fare__conference=conference)

TICKET_TYPE = (
	('standard', 'standard'),
	('staff', 'staff'),
)


class Ticket(models.Model):
	user = models.ForeignKey(
		'auth.User',
		help_text=_('holder of the ticket (who has buyed it?)'))
	name = models.CharField(
		max_length=60,
		blank=True,
		help_text=_('Real name of the attendee.<br />This is the person that will attend the conference.'))
	fare = models.ForeignKey(Fare)
	frozen = models.BooleanField(default=False)
	ticket_type = models.CharField(max_length=8, choices=TICKET_TYPE, default='standard')
	created = models.DateField(editable=False, auto_now_add=True)
	updated = models.DateTimeField(editable=False, auto_now=True)

	objects = TicketManager()

	def __unicode__(self):
		return 'Ticket "%s" (%s)' % (self.fare.name, self.fare.code)


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
	('omnivorous', _('Omnivorous')),
	('vegetarian', _('Vegetarian')),
	#('vegan', _('Vegan')),
	#('kosher', _('Kosher')),
)

TICKET_CONFERENCE_EXPERIENCES = (
	(0, _('0 stars')),
	(1, _('1 stars')),
	(2, _('2 stars')),
	(3, _('3 stars')),
	(4, _('4 stars')),
	(5, _('5 stars')),
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
			# TODO: drop in favor of dataaccess.user_tickets
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
	tagline = models.CharField(
		max_length=60,
		blank=True,
		help_text=_('a (funny?) tagline that will be displayed on the badge<br />Eg. CEO of FooBar Inc.; Student at MIT; Super Python fanboy'))
	days = models.TextField(
		verbose_name=_('Days of attendance'), blank=True)
	badge_image = models.ImageField(
		null=True, blank=True,
		upload_to='p3/tickets/badge_image',
		help_text=_('''A custom badge image instead of the python logo. Don't use a very large image, 250x250 should be fine.'''))
	assigned_to = models.EmailField(blank=True)

	objects = TicketConferenceManager()

	def profile(self):
		if self.assigned_to:
			return AttendeeProfile.objects.get(user__email=self.assigned_to)
		else:
			return AttendeeProfile.objects.get(user=self.ticket.user)


def _ticket_sim_upload_to(instance, filename):
	subdir = 'p3/personal_documents'
	# Adding the ticket id in the filename because a single user can
	# buy multiple sims and probably they're not all for the same person.
	fname = '%s-%s' % (instance.ticket.user.username, instance.ticket.id)
	fdir = os.path.join(settings.SECURE_MEDIA_ROOT, subdir)
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
		storage=settings.SECURE_STORAGE,
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