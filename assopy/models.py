# -*- coding: UTF-8 -*-

import re
import os
import os.path
import logging
from uuid import uuid4
from datetime import date, datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from django import dispatch
from django.conf import settings as dsettings
from django.contrib import auth
from django.contrib.admin.utils import quote
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.query import QuerySet
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from assopy import janrain
from assopy import settings
from assopy.utils import send_email
from common import django_urls
from conference.currencies import normalize_price
from conference.models import Ticket
from email_template import utils


log = logging.getLogger('assopy.models')

# if settings.CHECK_DB_SCHEMA:
#     check_database_schema()

def _cache(f):
    """
    cache dei poveri, memorizzo nell'istanza il risultato di una richiesta
    remota (la cache dura una richiesta)
    """
    def wrapper(self, *args, **kwargs):
        key = '_c' + f.__name__
        try:
            r = getattr(self, key)
        except AttributeError:
            r = f(self, *args, **kwargs)
            setattr(self, key, r)
        return r
    return wrapper

def _gravatar(email, size=80, default='identicon', rating='r'):
    # import code for encoding urls and generating md5 hashes
    import urllib, hashlib

    gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode({
        'default': default,
        'size': size,
        'rating': rating,
    })

    return gravatar_url

COUNTRY_VAT_COMPANY_VERIFY = (
    ('-', 'None'),
    ('v', 'VIES'),
)
class Country(models.Model):
    iso = models.CharField(_('ISO alpha-2'), max_length=2, primary_key=True)
    name = models.CharField(max_length=100)
    vat_company = models.BooleanField('VAT for company', default=False)
    vat_company_verify = models.CharField(max_length=1, choices=COUNTRY_VAT_COMPANY_VERIFY, default='-')
    vat_person = models.BooleanField('VAT for person', default=False)
    iso3 = models.CharField(_('ISO alpha-3'), max_length=3, null=True)
    numcode = models.PositiveSmallIntegerField(_('ISO numeric'), null=True)
    printable_name = models.CharField(_('Country name'), max_length=128)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Countries'

    def __unicode__(self):
        return self.name

class TokenManager(models.Manager):
    def create(self, ctype='', user=None, payload=''):
        if user is not None:
            Token.objects.filter(user=user, ctype=ctype).delete()
        t = Token()
        t.token = str(uuid4())
        t.ctype = ctype
        t.user = user
        t.payload = payload
        t.save()
        return t

    def retrieve(self, token, delete=True):
        try:
            t = Token.objects.get(token=token)
        except Token.DoesNotExist:
            return None
        if delete:
            t.delete()
        return t

class Token(models.Model, django_urls.UrlMixin):
    """
    modello che mantiene codici univoci, utilizzabili una sola volta, di
    diverso tipo per ogni utente.
    """
    token = models.CharField(max_length=36, primary_key=True)
    ctype = models.CharField(max_length=1)
    user = models.ForeignKey(auth.models.User, null=True)
    payload = models.TextField(blank='')
    created = models.DateTimeField(auto_now_add=True)

    objects = TokenManager()

    def get_url_path(self):
        return reverse('assopy-otc-token', kwargs={'token': self.token})

# Segnale emesso quando un nuovo utente viene creato. Il sender è il nuovo
# utente mentre profile_complete indica se tutti i dati su l'utente sono già
# stat forniti oppure ci si deve aspettare la creazione di una UserIdentity.
# `profile_complete` può essere usato come discriminante per capire se è stato
# creato tramite la form classica email+password (profile_complete=True) o in
# seguito ad un'identità fornita da janrain (profile_complete=False).
user_created = dispatch.Signal(providing_args=['profile_complete'])

# Segnale emesso quando una nuova identità viene aggiunta ad un utente (il
# sender).
user_identity_created = dispatch.Signal(providing_args=['identity'])


class UserManager(models.Manager):

    def create_user(self, email, first_name='', last_name='', password=None, token=False, active=False, assopy_id=None, send_mail=True):
        uname = janrain.suggest_username_from_email(email)
        duser = auth.models.User.objects.create_user(uname, email, password=password)
        duser.first_name = first_name
        duser.last_name = last_name
        duser.is_active = active
        duser.save()
        user = User(user=duser)
        if token:
            user.token = str(uuid4())
        if assopy_id is not None:
            user.assopy_id = assopy_id
        user.save()
        user_created.send(
            sender=user,
            profile_complete=(password is not None) or (token is not None)
        )
        log.info(
            'new local user "%s" created; for "%s %s" (%s)',
            duser.username, first_name, last_name, email,
        )

        if send_mail:
            utils.email(
                'verify-account',
                ctx={
                    'user': duser,
                    'token': Token.objects.create(ctype='v', user=duser),
                },
                to=[email]
            ).send()
        return user

def _fs_upload_to(subdir, attr=None):
    if attr is None:
        attr = lambda i: i.pk
    def wrapper(instance, filename):
        fpath = os.path.join('assopy', subdir, '%s%s' % (attr(instance), os.path.splitext(filename)[1].lower()))
        ipath = os.path.join(dsettings.MEDIA_ROOT, fpath)
        if os.path.exists(ipath):
            os.unlink(ipath)
        return fpath
    return wrapper

# segnale emesso quando assopy ha bisogno di conoscere i biglietti assegnati ad
# un certo utente (il sender).  questo segnale permette ad altre applicazioni
# di intervenire su questa scelta, se nessuno è in ascolto viene fatta una
# query guardando i Conference.Ticket
ticket_for_user = dispatch.Signal(providing_args=['tickets'])


class User(models.Model):
    """
    aka. AssopyUser; There are multiple models called 'User', this one, and the
    bultin django one from django.contrib.auth.models; This model is often
    referred to in other places as 'AssopyUser' for clarity.
    """
    user = models.OneToOneField("auth.User", related_name='assopy_user')
    token = models.CharField(max_length=36, unique=True, null=True, blank=True)
    assopy_id = models.CharField(max_length=22, null=True, unique=True)

    card_name = models.CharField(
        _('Card name'), max_length=200, blank=True,
        help_text=_('The name used for orders and invoices'))
    vat_number = models.CharField(
        _('Vat Number'), max_length=22, blank=True,
        help_text=_('Your VAT number if applicable'))
    cf_code = models.CharField(
        _('Fiscal Code'), max_length=16, blank=True,
        help_text=_('Needed only for Italian customers'))
    country = models.ForeignKey(Country, verbose_name=_('Country'), null=True, blank=True)
    address = models.CharField(
        _('Address and City'),
        max_length=150,
        blank=True,
        help_text=_('Insert the full address, including city and zip code. We will help you through google.'),)

    objects = UserManager()

    def __unicode__(self):
        name = self.card_name or self.name()
        return 'Assopy user: %s (%s)' % (name, self.id)

    def name(self):
        name = '%s %s' % (self.user.first_name, self.user.last_name)
        if not name.strip():
            return self.user.email
        else:
            return name

    def get_orders(self):
        """
        Temporary wrapper method for Issue #592, to easily disable old
        (pre-2018) orders/invoices, until #591 is fixed

        https://github.com/EuroPython/epcon/issues/592
        """
        return self.orders.filter(created__gte=date(2018, 1, 1))

    def tickets(self):
        tickets = []
        ticket_for_user.send(sender=self, tickets=tickets)
        if not tickets:
            tickets = Ticket.objects.conference(dsettings.CONFERENCE_CONFERENCE).filter(user=self.user)
        return tickets

    def invoices(self):
        return Invoice.objects.filter(order__in=self.orders)

class UserIdentityManager(models.Manager):
    def create_from_profile(self, user, profile):
        """
        crea una UserIdentity estraendo i dati dal profilo, risultato di una
        chiamata ad auth_info; l'identity sarà associata all'utente (assopy)
        passato.
        """
        identifier = UserIdentity(
            identifier=profile['identifier'],
            user=user,
            provider=profile['providerName'],
        )
        try:
            identifier.display_name = profile['name']['formatted']
        except KeyError:
            identifier.display_name = profile.get('displayName')
        identifier.gender = profile.get('gender')

        if 'birthday' in profile:
            birthday = profile.get('birthday', '').split('-')
            if birthday[0] == '0000':
                birthday[0] = '1900'
            identifier.birthday = date(*map(int, birthday))
        try:
            identifier.email = profile['verifiedEmail']
        except KeyError:
            identifier.email = profile.get('email')
        identifier.url = profile.get('url')
        identifier.photo = profile.get('photo')
        identifier.phoneNumber = profile.get('phoneNumber')
        try:
            identifier.address = profile['address']['formatted']
        except KeyError:
            pass

        identifier.save()
        user_identity_created.send(sender=user, identity=identifier)
        return identifier

class UserIdentity(models.Model):
    identifier = models.CharField(max_length=255, primary_key=True)
    user = models.ForeignKey(User, related_name='identities')
    provider = models.CharField(max_length=255)
    display_name = models.TextField(blank=True)
    gender = models.CharField(max_length=10, blank=True)
    birthday = models.DateField(null=True)
    email = models.EmailField(blank=True)
    url = models.URLField()
    photo = models.URLField()
    phoneNumber = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    objects = UserIdentityManager()

class UserOAuthInfo(models.Model):
    user = models.ForeignKey(User, related_name='oauth_infos')
    service = models.CharField(max_length=20)
    token = models.CharField(max_length=200)
    secret = models.CharField(max_length=200)

    def __unicode__(self):
        return u'{0} token for {1}'.format(self.service, self.user)

class Coupon(models.Model):
    conference = models.ForeignKey('conference.Conference')
    code = models.CharField(max_length=10)
    start_validity = models.DateField(null=True, blank=True)
    end_validity = models.DateField(null=True, blank=True)
    max_usage = models.PositiveIntegerField(default=0, help_text='numero di volte che questo coupon può essere usato')
    items_per_usage = models.PositiveIntegerField(default=0, help_text='numero di righe d\'ordine su cui questo coupon ha effetto')
    description = models.CharField(max_length=100, blank=True)
    value = models.CharField(max_length=8, help_text='importo, eg: 10, 15%, 8.5')

    user = models.ForeignKey(User, null=True, blank=True)
    fares = models.ManyToManyField('conference.Fare', blank=True)

    def __unicode__(self):
        return '%s (%s)' % (self.code, self.value)

    def clean(self):
        if re.search(r'[^\d\%\.]+', self.value):
            raise ValidationError('The value of the coupon contains illegal characters')

    def type(self):
        if self.value.endswith('%'):
            return 'perc'
        else:
            return 'val'

    def valid(self, user=None):
        if self.start_validity and self.end_validity:
            today = date.today()
            if today < self.start_validity or today > self.end_validity:
                return False

        if self.max_usage:
            if OrderItem.objects.filter(ticket=None, code=self.code).count() >= self.max_usage:
                return False

        if self.user_id:
            if not user:
                return False
            elif self.user_id != user.id:
                return False

        return True

    def applyToOrder(self, order):
        if not self.valid(order.user):
            raise ValueError('coupon not valid')

        fares = self.fares.all()
        apply_to = order.rows(include_discounts=False)
        if fares:
            apply_to = apply_to.filter(ticket__fare__in=fares)
        if self.items_per_usage:
            apply_to = apply_to.order_by('-ticket__fare__price')[:self.items_per_usage]

        total = sum(x.price for x in apply_to)
        discount = self._applyToTotal(total, order.total())
        if not discount:
            return None
        item = OrderItem(order=order, ticket=None, vat=apply_to[0].vat)
        item.code = self.code
        item.description = self.description
        item.price = discount
        return item

    def applyToRows(self, user, items):
        if not self.valid(user):
            raise ValueError('coupon not valid')

        rows = []
        for fare, params in items:
            c = dict(params)
            c['qty'] = 1
            for _ in range(params['qty']):
                rows.append((fare, c))

        apply_to = rows
        fares = set(self.fares.all().values_list('code', flat=True))
        if fares:
            apply_to = filter(lambda x: x[0].code in fares, apply_to)

        if self.items_per_usage:
            # il coupon è valido solo per un numero massimo di item, lo applico
            # partendo dal più costoso
            apply_to = sorted(apply_to, key=lambda x: x[0].calculated_price(**x[1]), reverse=True)
            apply_to = apply_to[:self.items_per_usage]

        total = Decimal(0)
        for fare, params in apply_to:
            total += Decimal('%.3f' % fare.calculated_price(**params))

        guard = Decimal(0)
        for fare, params in rows:
            guard += Decimal('%.3f' % fare.calculated_price(**params))

        return self._applyToTotal(total, guard)

    def _applyToTotal(self, total, guard):
        if self.type() == 'val':
            discount = Decimal(self.value)
        else:
            discount = total / 100 * Decimal(self.value[:-1])
        if discount > total:
            discount = total
        if discount > guard:
            discount = guard
        return -1 * discount

class OrderManager(models.Manager):
    def get_queryset(self):
        return self._QuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.all(), name)

    class _QuerySet(QuerySet):
        def use_coupons(self, *coupons):
            return self.filter(orderitem__ticket=None, orderitem__code__in=(c.code for c in coupons))

        def conference(self, conference):
            return self.filter(orderitem__ticket__fare__conference=conference).distinct()

        def usable(self, include_admin=False):
            """
            restituisce tutti gli ordini "usabili", cioè tutti gli ordini con
            metodo bonifico (a prescindere se risultano pagati o meno) e tutti
            gli ordini con metodo paypal (o cc) completati.
            """
            qs = self.filter(models.Q(method='bank')|models.Q(method__in=('cc', 'paypal'), _complete=True))
            if include_admin:
                qs = qs.filter(method='admin')
            return qs

        def total(self, apply_discounts=True):
            qs = OrderItem.objects.filter(order__in=self)
            if not apply_discounts:
                qs = qs.filter(price__gt=0)
            t = qs.aggregate(t=models.Sum('price'))['t']
            return t if t is not None else 0

    def create(self, user, payment, items, billing_notes='', coupons=None, country=None, address=None, vat_number='', cf_code='', remote=True):
        if coupons:
            for c in coupons:
                if not c.valid(user):
                    log.warn('Invalid coupon: %s', c.code)
                    raise ValueError(c)

        log.info('new order for "%s" via "%s": %d items', user.name(), payment, sum(x[1]['qty'] for x in items))

        o = Order()
        o.code = None
        o.method = payment
        o.user = user

        o.billing_notes = billing_notes

        o.card_name = user.card_name or user.name()
        o.vat_number = vat_number
        o.cf_code = cf_code
        o.country = country if country else user.country
        o.address = address if address else user.address

        o.save()
        vat_list = []
        for f, params in items:
            try:
                vat = f.vat_set.all()[0]
            except IndexError:
                raise

            vat_list.append(vat)
            cp = dict(params)
            del cp['qty']
            for _ in range(params['qty']):
                tickets = f.create_tickets(user.user)
                price = Decimal('%.3f' % f.calculated_price(qty=1, **cp))
                row_price = price / len(tickets)
                for ix, t in enumerate(tickets):
                    item = OrderItem(order=o, ticket=t, vat=vat)
                    item.code = f.code
                    if hasattr(t, 'fare_description'):
                        item.description = t.fare_description
                    else:
                        item.description = f.name
                        if len(tickets) > 1:
                            item.description += ' [%s/%s]' % (ix+1, len(tickets))
                    item.price = row_price
                    item.save()
        tickets_total = o.total()
        if coupons:
            # applico i coupon in due passi:
            #   1. applico i coupon a percentuale sempre rispetto al totale
            #       dell'ordine
            #   2. applico i coupon a valore sul totale risultante
            #
            # queste regole servono a preparare un ordine (e una fattura) che
            # risulti il più capibile possibile per l'utente.
            for t in ('perc', 'val'):
                for c in coupons:
                    if c.type() == t:
                        item = c.applyToOrder(o)
                        if item:
                            item.save()
                            log.debug(
                                'coupon "%s" applied, discount=%s, vat=%s',
                                item.code,
                                item.price,
                                item.vat
                            )
        log.info(
            'order "%s" and tickets created locally: '
            'tickets total=%s order total=%s',
            o.id,
            tickets_total,
            o.total()
        )
        o.code = settings.NEXT_ORDER_CODE(o)
        o.save()
        if o.total() == 0:
            o._complete = True
            o.save()
        order_created.send(sender=o, raw_items=items)
        return o


class Vat(models.Model):
    fares = models.ManyToManyField('conference.fare',
                                   through='VatFare',
                                   null=True, blank=True)
    value = models.DecimalField(max_digits=2, decimal_places=0)
    description = models.CharField(null=True, blank=True, max_length=125)
    invoice_notice = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return u"%s%% - %s" % (self.value, self.description or "")


class VatFare(models.Model):
    fare = models.ForeignKey('conference.fare')
    vat = models.ForeignKey(Vat)

    class Meta:
        unique_together =('fare', 'vat')

# segnale emesso quando un ordine, il sender, è stato correttamente registrato
# in locale e sul backend. `raw_items` è la lista degli item utilizzata per
# generare l'ordine; sebbene al momento dell'invio del segnale l'ordine sia già
# stato creato e associato a tutti gli OrderItem, in raw_items potrebbero
# essere presenti informazioni aggiuntive che altrimenti non sarebbe possibile
# recuperare.
order_created = dispatch.Signal(providing_args=['raw_items'])

# segnale emesso da un ordine quando un questo viene "completato".  Al momento
# l'unico meccanismo per accorgersi se un ordine è completo è pollare il
# backend attraverso il metodo Order.complete.
purchase_completed = dispatch.Signal(providing_args=[])

# Implemented order payment options
ORDER_PAYMENT = (
    ('cc', 'Credit Card'),
    ('paypal', 'PayPal'),
    ('bank', 'Bank'),
)

# Enabled order payment options
ENABLED_ORDER_PAYMENT = (
    ('cc', 'Credit Card'),
)

class Order(models.Model):
    code = models.CharField(max_length=20, null=True)
    assopy_id = models.CharField(max_length=22, null=True, unique=True, blank=True)
    user = models.ForeignKey(User, related_name='orders')
    created = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=6, choices=ORDER_PAYMENT)
    payment_url = models.TextField(blank=True)

    # _complete è una cache dello stato dell'ordine; quando è False il metodo
    # .complete deve interrogare il backend remoto per sapere lo stato
    # dell'ordine, quando è True significa che l'ordine è stato confermato.
    # Ovviamente questo non permette di cachare lo stato "non confermato", ma
    # gli ordine non confermati più vecchi di un carta data dovrebbero essere
    # eliminati.
    _complete = models.BooleanField(default=False)

    # note libere che l'acquirente può inserire in fattura
    billing_notes = models.TextField(blank=True)

    # Questi dati vengono copiati dallo User al fine di storicizzarli
    card_name = models.CharField(_('Card name'), max_length=200)
    vat_number = models.CharField(_('Vat Number'), max_length=22, blank=True)
    cf_code = models.CharField(_('Fiscal Code'), max_length=16, blank=True)
    # la country deve essere null perché un ordine può essere creato via admin
    # e in quel caso non è detto che si conosca
    country = models.ForeignKey(Country, verbose_name=_('Country'), null=True)
    address = models.CharField(_('Address'), max_length=150, blank=True)

    stripe_charge_id = models.CharField(_('Charge Stripe ID'), max_length=64, unique=True, null=True)

    payment_date = models.DateTimeField(
        help_text="Auto filled by the payments backend",
        blank=True,
        null=True,
    )

    objects = OrderManager()

    def __unicode__(self):
        msg = 'Order %d' % self.id
        if self.code:
            msg += ' #%s' % self.code
        return msg

    def vat_list(self):
        """
        Ritorna una lista di dizionari con import iva e import
        e numero di orderitems prezzi
        """
        vat_list = defaultdict(lambda:{'vat':None, 'orderItems':[], 'price':0})
        for i in self.orderitem_set.all():
            vat_list[i.vat]['vat'] = i.vat
            vat_list[i.vat]['orderItems'].append(i)
            vat_list[i.vat]['price'] += i.price
        return vat_list.values()

    def complete(self, update_cache=True, ignore_cache=False):
        if self._complete and not ignore_cache:
            return True

        invoices = [i.payment_date for i in self.invoices.all()]
        # un ordine per essere completo deve avere una fattura per ogni
        # iva; questa martellata mette una pezza al comportamento della
        # Invoice.objects.creates_from_order
        if len(invoices) < len(self.vat_list()):
            invoices.append(None)

        # un ordine risulta pagato se tutte le sue fatture riportano la data
        # del pagamento
        r = len(invoices) > 0 and all(invoices)
        if r and not self._complete:
            log.info('purchase of order "%s" completed', self.code)
            purchase_completed.send(sender=self)
        if r and update_cache:
            self._complete = r
            self.save()
        return r

    def confirm_order(self, payment_date):
        # NOTE(artcz)(2018-05-28)
        # This used to generate invoices, currently it just fills payment date,
        # and creates placeholder
        # To avoid ciruclar import
        from conference.invoicing import (
            create_invoices_for_order,
            FORCE_PLACEHOLDER
        )
        self.payment_date = payment_date
        self.save()
        create_invoices_for_order(self, force_placeholder=FORCE_PLACEHOLDER)

    def total(self, apply_discounts=True):
        if apply_discounts:
            t = self.orderitem_set.aggregate(t=models.Sum('price'))['t']
        else:
            t = self.orderitem_set.filter(price__gt=0).aggregate(t=models.Sum('price'))['t']
        return t if t is not None else 0

    def rows(self, include_discounts=True, vat=None):
        qs = self.orderitem_set
        if vat:
            qs = qs.filter(vat=vat)
        if include_discounts:
            return qs
        else:
            return qs.exclude(ticket=None)

    @classmethod
    def calculator(self, items, coupons=None, user=None):
        """
        calcola l'importo di un ordine non ancora effettuato tenendo conto di
        eventuali coupons.
        """
        # sono le stesse regole utilizzate dalla OrderManager.create
        totals = {
            'tickets': [],
            'coupons': {},
            'total': 0,
        }
        tickets_total = 0
        for fare, params in items:
            total = Decimal('%.3f' % fare.calculated_price(**params))
            totals['tickets'].append((fare, params, total))
            tickets_total += total

        total = tickets_total
        if coupons:
            for t in ('perc', 'val'):
                for c in coupons:
                    if c.type() == t:
                        result = c.applyToRows(user, items)
                        if result is not None:
                            totals['coupons'][c.code] = (result, c)
                            total += result
        totals['total'] = total
        return totals

    def delete(self, **kwargs):
        for item in self.orderitem_set.all():
            item.delete()
        super(Order, self).delete(**kwargs)



class OrderItem(models.Model):
    order = models.ForeignKey(Order)
    ticket = models.OneToOneField('conference.ticket', null=True, blank=True)
    code = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.CharField(max_length=100, blank=True)
    # aggiungo un campo per iva... poi potra essere un fk ad un altra tabella
    # o venire copiato da conference
    vat = models.ForeignKey(Vat)

    def invoice(self):
        """
        Ritorna, se esiste, la fattura collegata all'order_item
        """
        # Non gestisco il caso in cui `.get()` ritorni più di un elemento
        # perché lo considero un errore
        try:
            return Invoice.objects.get(order=self.order_id, vat=self.vat_id)
        except Invoice.DoesNotExist:
            return None

    def get_readonly_fields(self, request, obj=None):
	    # Make fields read-only if an invoice for the order already exists
        if obj and self.order.invoices.exclude(payment_date=None).exists():
            return self.readonly_fields + ('ticket', 'price', 'vat', 'code')
        return self.readonly_fields

    def delete(self, **kwargs):
        if self.ticket:
            self.ticket.delete()
        else:
            super(OrderItem, self).delete(**kwargs)

    def refund_type(self):
        """
            Restituisce il tipo di rimborso applicabile:

            - direct, rimbordo diretto
                Per i pagamenti fatti con paypal non più di 60gg fa
            - payment, rimborso con un nuovo pagamento
                Per tutti gli altri pagamenti
        """
        order = self.order
        if order.method in ('paypal', 'cc') and order.created > now() - timedelta(days=60):
            return 'direct'
        return 'payment'

def _order_feedback(sender, **kwargs):
    rows = [
        'Ordering person: "%s" (%s)' % (sender.user.name(), sender.user.user.email),
        'Card name: "%s"' % (sender.card_name,),
        'Payment method: "%s"' % (sender.method,),
        'Nationality: "%s"' % (sender.country.name if sender.country else '',),
        'Address: "%s"' % (sender.address,),
        'Billing notes:\n%s\n' % (sender.billing_notes,),
        'Billing summary:',
    ]
    for x in sender.orderitem_set.order_by('ticket__fare__code').select_related():
        rows.append('%-5s %-47s %6.2f' % (x.code, x.description, x.price))
    rows.append('-' * 60)
    rows.append('%54s%6.2f' % ('', sender.total()))
    send_email(
        subject='New order: %s, from "%s"' % (sender.code, sender.user.name(),),
        message='\n'.join(rows),
    )

order_created.connect(_order_feedback)


class InvoiceLog(models.Model):
    code =  models.CharField(max_length=20, unique=True)
    order = models.ForeignKey(Order, null=True)
    invoice = models.ForeignKey('Invoice', null=True)
    date = models.DateTimeField(auto_now_add=True)


class InvoiceManager(models.Manager):
    pass


class Invoice(models.Model):

    PLACEHOLDER_EXRATE_DATE = date(2000, 1, 1)

    order = models.ForeignKey(Order, related_name='invoices')
    code = models.CharField(max_length=20, null=True, unique=True)
    assopy_id = models.CharField(max_length=22, unique=True,
                                 null=True, blank=True)
    emit_date = models.DateField()
    payment_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    issuer = models.TextField()
    html = models.TextField()

    local_currency = models.CharField(max_length=3, default="EUR")
    vat_in_local_currency = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        # remove after testing
        default=Decimal("0"),
    )
    exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        # remove after testing
        default=Decimal("1"),
    )
    exchange_rate_date = models.DateField(default=PLACEHOLDER_EXRATE_DATE)

    # indica il tipo di regime iva associato alla fattura perche vengono
    # generate più fatture per ogni ordine contente orderitems con diverso
    # regime fiscale
    vat = models.ForeignKey(Vat)

    note = models.TextField(
        blank=True,
        help_text='''Testo libero da riportare in fattura; posto al termine delle righe d'ordine riporta di solito gli estremi di legge''')

    objects = InvoiceManager()

    def save(self, *args, **kwargs):
        from conference.invoicing import is_real_invoice_code
        super(Invoice, self).save(*args, **kwargs)
        log, create = InvoiceLog.objects.get_or_create(
            order=self.order,
            code=self.code,
            invoice=self
        )
        if create and is_real_invoice_code(self.code):
            self.order.complete(ignore_cache=True)

    def get_absolute_url(self):
        return self.get_pdf_url()

    def get_html_url(self):
        """Render invoice as html -- fallback in case PDF doesn't work"""
        return reverse("assopy-invoice-html", args=[
            quote(self.order.code), quote(self.code)
        ])

    def get_pdf_url(self):
        return reverse("assopy-invoice-pdf", args=[
            quote(self.order.code), quote(self.code)
        ])

    def get_admin_url(self):
        return reverse('admin:assopy_invoice_change', args=[self.id])

    def __unicode__(self):
        if self.code:
            return ' #%s' % self.code
        else:
            return 'Invoice id:%d' % self.id

    def get_invoice_filename(self):
        return 'EuroPython_Invoice_%s.pdf' % self.code.replace('/', '-')

    def invoice_items(self):
        return self.order.orderitem_set.filter(vat=self.vat) \
                                  .values('code','description') \
                                  .annotate(price=models.Sum('price'), count=models.Count('price')) \
                                  .order_by('-price')

    def vat_value(self):
        return self.price - self.net_price()

    def net_price(self):
        return normalize_price(self.price / (1 + self.vat.value / 100))

    @property
    def net_price_in_local_currency(self):
        """
        In order to make it more correct instead of computing value by
        multiplying self.net_price() by exchange_rate we're going to subtract
        vat value from converted gross price. That way net + vat will always
        add up to gross.
        """
        return self.price_in_local_currency - self.vat_in_local_currency

    @property
    def price_in_local_currency(self):
        return normalize_price(self.price * self.exchange_rate)


if 'paypal.standard.ipn' in dsettings.INSTALLED_APPS:
    from paypal.standard.ipn.signals import payment_was_successful as paypal_payment_was_successful
    def confirm_order(sender, **kwargs):
        ipn_obj = sender
        o = Order.objects.get(code=ipn_obj.custom)
        o.confirm_order(ipn_obj.payment_date)

    paypal_payment_was_successful.connect(confirm_order)

class CreditNote(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='credit_notes')
    code = models.CharField(max_length=20, unique=True)
    assopy_id =  models.CharField(max_length=22, null=True)
    emit_date = models.DateField()
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __unicode__(self):
        return ' #%s' % self.code

    def note_items(self):
        return self.refund.items.all()\
            .values('code','description') \
            .annotate(price=models.Sum('price'), count=models.Count('price')) \
            .order_by('-price')

    def vat_value(self):
        return self.price - self.net_price()

    def net_price(self):
        return self.price / (1 + self.invoice.vat.value / 100)

class RefundOrderItem(models.Model):
    orderitem = models.ForeignKey('assopy.OrderItem')
    refund = models.ForeignKey('assopy.Refund')

    class Meta:
        unique_together = (('orderitem', 'refund'),)

    def save(self, *args, **kwargs):
        if self.refund.status != 'pending':
            raise RuntimeError('Refund must be in "pending" status')
        out = super(RefundOrderItem, self).save(*args, **kwargs)
        log.info(
            'Froze a ticket (%d) according to the refund request of "%s" for the order "%s"',
            self.orderitem.ticket.id,
            self.orderitem.order.user.name(),
            self.orderitem.order.code)
        self.orderitem.ticket.frozen = True
        self.orderitem.ticket.save()
        return out

class RefundManager(models.Manager):
    def create_from_orderitem(self, orderitem, reason='', internal_note=''):
        invoice = orderitem.invoice()
        assert invoice
        assert invoice.payment_date
        qs = Refund.objects\
            .filter(status='pending', invoice=invoice)
        try:
            r = qs[0]
        except IndexError:
            r = Refund.objects.create(
                invoice=invoice, reason=reason, internal_note=internal_note)
        RefundOrderItem.objects.create(refund=r, orderitem=orderitem)

        items = RefundOrderItem.objects\
            .filter(refund=r)\
            .select_related('orderitem__ticket')
        refund_event.send(
            sender=r, old='', tickets=[ x.orderitem.ticket for x in items ]
        )

# TODO make that into Choices
REFUND_STATUS = (
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('refunded', 'Refunded'),
)
class Refund(models.Model):
    invoice = models.ForeignKey(Invoice, null=True)
    items = models.ManyToManyField(OrderItem, through=RefundOrderItem)
    created = models.DateTimeField(auto_now_add=True)
    done = models.DateTimeField(null=True)
    credit_note = models.OneToOneField(CreditNote, null=True, blank=True)
    status = models.CharField(max_length=8, choices=REFUND_STATUS, default='pending')
    reason = models.CharField(max_length=200, blank=True)
    internal_note = models.TextField(
        blank=True,
        help_text='For internal use (not shown to the user)',
    )
    reject_reason = models.TextField(
        blank=True,
        help_text='Included in the email sent to the user',
    )

    objects = RefundManager()

    def clean(self):
        if self.status == 'rejected':
            for item in self.items.all():
                if item.ticket is None:
                    from django.core.exceptions import ValidationError
                    raise ValidationError('Cannot reject a previously refunded request')

    def price(self):
        # XXX: questo codice non va bene, non tiene conto di eventuali coupon
        # che possono aver ridotto il prezzo del biglietto
        return sum(self.items.all().values_list('price', flat=True))

    def emit_credit_note(self, price=None, emit_date=None):
        """
        Emette la nota di credito per questo rimborso
        """
        if emit_date is None:
            emit_date = now()
        if price is None:
            price = self.price()
        log.info(
            'emit credit note for refund "%s"', self.id)
        c = CreditNote(
            invoice=self.invoice,
            emit_date=emit_date,
            price=price)
        c.code = settings.NEXT_CREDIT_CODE(c)
        c.save()
        self.credit_note = c
        self.save()
        credit_note_emitted.send(sender=c, refund=self)
        return c

    def save(self, *args, **kwargs):
        old = None
        if self.id:
            try:
                old = Refund.objects.values('status').get(id=self.id)['status']
            except Refund.DoesNotExist:
                pass
        if self.status in ('rejected', 'refunded') and self.status != old:
            self.done = datetime.now()
        if old and self.status != old:
            o = self.items.all()[0].order
            log.info(
                'Refund #%d, order "%s", "%s": status changed from "%s" to "%s"',
                self.id,
                o.code,
                o.user.name(),
                old,
                self.status)
        try:
            return super(Refund, self).save(*args, **kwargs)
        finally:
            tickets = []
            for item in self.items.all():
                t = item.ticket
                if not t:
                    continue
                tickets.append(t)
                if self.status == 'refunded':
                    log.info('Delete the ticket "%d" because it as been refuneded', t.id)
                    item.ticket = None
                    item.save()
                    t.delete()
                elif self.status == 'rejected':
                    log.info('Unfroze the ticket "%d" because the refund as been rejected', t.id)
                    t.frozen = False
                    t.save()
                else:
                    t.frozen = True
                    t.save()
            refund_event.send(sender=self, old=old, tickets=tickets)


refund_event = dispatch.Signal(providing_args=['old', 'tickets'])
credit_note_emitted = dispatch.Signal(providing_args=['refund'])

def on_credit_note_emitted(sender, **kw):
    refund = kw['refund']
    tpl = 'refund-credit-note'

    items = list(refund.items.all().select_related('order__user__user'))
    ctx = {
        'items': items,
        'name': items[0].order.user.name(),
        'refund': refund,
        'tickets': [ x.ticket for x in refund.items.all() ],
        'credit_note': sender,
    }
    utils.email(tpl, ctx, to=[items[0].order.user.user.email]).send()

credit_note_emitted.connect(on_credit_note_emitted)

def on_refund_changed(sender, **kw):
    if sender.status == kw['old']:
        return
    if not kw['tickets']:
        return
    tpl = 'refund-' + sender.status

    from django.http import Http404
    items = list(sender.items.all().select_related('order__user__user'))
    ctx = {
        'items': items,
        'name': items[0].order.user.name(),
        'refund': sender,
        'tickets': kw['tickets'],
        'credit_note': sender.credit_note,
    }
    try:
        utils.email(tpl, ctx, to=[items[0].order.user.user.email]).send()
    except Http404:
        pass
    uid = items[0].order.user.user_id
    order = items[0].order
    mail_items = '\n'.join([ u' * %s - € %s' % (x.description, x.price) for x in items ])
    if sender.status == 'pending':
        message = '''
User: %s (%s)
Reason: %s
Order: %s
Items:
%s

Internal Notes:
%s

Manage link: %s
        ''' % (
            ctx['name'],
            dsettings.DEFAULT_URL_PREFIX + reverse('admin:auth_user_change', args=(uid,)),
            sender.reason,
            order.code,
            mail_items,
            sender.internal_note,
            dsettings.DEFAULT_URL_PREFIX + reverse('admin:assopy_refund_change', args=(sender.id,)),
        )
        send_email(
            subject='Refund request from %s' % ctx['name'],
            message=message,
            recipient_list=settings.REFUND_EMAIL_ADDRESS['approve'],
        )
    elif sender.status == 'approved':
        message = '''
User: %s (%s)
Order: %s
Items:
%s
Payment method: %s

Manage link: %s
        ''' % (
            ctx['name'],
            dsettings.DEFAULT_URL_PREFIX + reverse('admin:auth_user_change', args=(uid,)),
            order.code,
            mail_items,
            order.method,
            dsettings.DEFAULT_URL_PREFIX + reverse('admin:assopy_refund_change', args=(sender.id,)),
        )
        emails = settings.REFUND_EMAIL_ADDRESS['execute']
        send_email(
            subject='Refund for %s approved' % ctx['name'],
            message=message,
            recipient_list=emails.get(order.method, emails[None]),
        )
    elif sender.status == 'refunded':
        sender.emit_credit_note()
refund_event.connect(on_refund_changed)
