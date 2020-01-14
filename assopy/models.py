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
from django.contrib.auth import get_user_model
from django.contrib.admin.utils import quote
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices

from assopy.utils import send_email
from conference.currencies import normalize_price
from conference.models import Ticket, Fare
from conference.users import generate_random_username


log = logging.getLogger('assopy.models')


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

    def __str__(self):
        return self.name


class Token(models.Model):
    """
    Model used to hold temporary Tokens. In the past it used to handle more
    token types, currently it's only used for email verification when creating
    new account
    """

    TYPES = Choices(
        ("v", "EMAIL_VERIFICATION", "New signup email verification"),
        ("j", "j", "UNKOWN - probably related to Janrain"),
    )
    token = models.CharField(max_length=36, primary_key=True)
    ctype = models.CharField(max_length=1, choices=TYPES)
    user = models.ForeignKey(
        get_user_model(), null=True, on_delete=models.CASCADE
    )
    payload = models.TextField(blank="")
    created = models.DateTimeField(auto_now_add=True)


# Segnale emesso quando un nuovo utente viene creato. Il sender è il nuovo
# utente mentre profile_complete indica se tutti i dati su l'utente sono già
# stat forniti oppure ci si deve aspettare la creazione di una UserIdentity.
# `profile_complete` può essere usato come discriminante per capire se è stato
# creato tramite la form classica email+password (profile_complete=True) o in
# seguito ad un'identità fornita da janrain (profile_complete=False).
user_created = dispatch.Signal(providing_args=['profile_complete'])


class AssopyUserManager(models.Manager):
    def _create_user(
        self,
        email,
        password,
        username=None,
        first_name="",
        last_name="",
        token=False,
        active=False,
        assopy_id=None,
        is_admin=False,
    ):
        if not username:
            username = generate_random_username()

        if is_admin:
            duser = get_user_model().objects.create_superuser(
                username, email, password=password
            )
        else:
            duser = get_user_model().objects.create_user(
                username, email, password=password
            )

        duser.first_name = first_name
        duser.last_name = last_name
        duser.is_active = active
        duser.save()
        user = AssopyUser(user=duser)

        if token:
            user.token = str(uuid4())
        if assopy_id is not None:
            user.assopy_id = assopy_id
        user.save()

        user_created.send(
            sender=user,
            profile_complete=(password is not None) or (token is not None),
        )

        return user

    def create_user(
        self,
        email,
        password=None,
        first_name="",
        last_name="",
        token=False,
        active=False,
        assopy_id=None,
    ):
        assopy_user = self._create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            token=token,
            active=active,
            assopy_id=assopy_id,
        )

        log.info(
            'new local user "%s" created; for "%s %s" (%s)',
            assopy_user.user.username,
            first_name,
            last_name,
            email,
        )
        return assopy_user

    def create_superuser(
        self,
        username,
        email,
        password,
        first_name="",
        last_name=""
    ):
        assopy_user = self._create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            username=username,
            token=False,
            active=True,
            assopy_id=None,
            is_admin=True,
        )

        log.info(
            'new admin user "%s" created for "%s %s" (%s)',
            assopy_user.user.username,
            first_name,
            last_name,
            email,
        )

        return assopy_user



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


class AssopyUser(models.Model):
    """
    The name is meant to differentiate it from the bultin django User model
     from django.contrib.auth.models; they have a one-to-one relation to each other.
    """
    user = models.OneToOneField(get_user_model(), related_name='assopy_user', on_delete=models.CASCADE)
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
    country = models.ForeignKey(Country, verbose_name=_('Country'), null=True, blank=True, on_delete=models.CASCADE)
    address = models.CharField(
        _('Address and City'),
        max_length=150,
        blank=True,
        help_text=_('Insert the full address, including city and zip code. We will help you through google.'),)

    objects = AssopyUserManager()

    def __str__(self):
        name = self.card_name or self.name()
        return 'Assopy user: %s (%s)' % (name, self.id)

    def name(self):
        # NOTE(artcz)
        # This is a very ugly fix. We should merge those fields and move to a
        # single unified 'full_name' field, but that's too much migration for
        # now. New signup flow uses single first-name field for both, this hack
        # is here to fix display in numerous places where we have old accounts
        # that have value for last_name in the database already.
        if self.user.first_name.endswith(self.user.last_name):
            name = self.user.first_name
        else:
            name = '%s %s' % (self.user.first_name, self.user.last_name)

        if not name.strip():
            return self.user.email

        return name.strip()

    def name_tuple(self):
        first_name, last_name = self.user.first_name, self.user.last_name
        if first_name.endswith(" " + last_name) and last_name:
            # handle name merged into first_name
            return first_name[:-(len(last_name) + 1)], last_name
        return first_name, last_name

    def get_orders(self):
        """
        Temporary wrapper method for Issue #592, to easily disable old
        (pre-2018) orders/invoices, until #591 is fixed

        https://github.com/EuroPython/epcon/issues/592
        """
        return self.orders.filter(created__gte=timezone.make_aware(datetime(2018, 1, 1)))

    def tickets(self):
        tickets = []
        ticket_for_user.send(sender=self, tickets=tickets)
        if not tickets:
            tickets = Ticket.objects.conference(dsettings.CONFERENCE_CONFERENCE).filter(user=self.user)
        return tickets

    def invoices(self):
        return Invoice.objects.filter(order__in=self.orders)


class Coupon(models.Model):
    conference = models.ForeignKey('conference.Conference', on_delete=models.CASCADE)
    code = models.CharField(max_length=10)
    start_validity = models.DateField(null=True, blank=True)
    end_validity = models.DateField(null=True, blank=True)
    max_usage = models.PositiveIntegerField(default=0, help_text='numero di volte che questo coupon può essere usato')
    items_per_usage = models.PositiveIntegerField(default=0, help_text='numero di righe d\'ordine su cui questo coupon ha effetto')
    description = models.CharField(max_length=100, blank=True)
    value = models.CharField(max_length=8, help_text='importo, eg: 10, 15%, 8.5')

    user = models.ForeignKey(AssopyUser, null=True, blank=True, on_delete=models.CASCADE)
    fares = models.ManyToManyField(Fare, blank=True)

    def __str__(self):
        return '%s (%s)' % (self.code, self.value)

    def clean(self):
        if re.search(r'[^\d\%\.]+', self.value):
            raise ValidationError('The value of the coupon contains illegal characters')

    def type(self):
        if self.value.endswith('%'):
            return 'perc'
        else:
            return 'val'

    def discount_multiplier(self):
        """
        Converts 20% to 0.8
        """
        assert self.value.endswith('%')
        discount = Decimal(self.value[:-1]) / Decimal(100)
        return discount

    def valid(self, user=None):
        if self.start_validity and self.end_validity:
            today = timezone.now().date()
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
            apply_to = [x for x in apply_to if x[0].code in fares]

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


class OrderQuerySet(models.QuerySet):
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
        qs = self.filter(Q(method='bank') | Q(method__in=('cc', 'paypal'), _complete=True))
        if include_admin:
            qs = qs.filter(method='admin')
        return qs

    def total(self, apply_discounts=True):
        qs = OrderItem.objects.filter(order__in=self)
        if not apply_discounts:
            qs = qs.filter(price__gt=0)
        t = qs.aggregate(t=models.Sum('price'))['t']
        return t if t is not None else 0

    # TODO: deprecate this .create in favor of conference/orders:create_order
    def create(self, user, payment, items, billing_notes='', coupons=None, country=None, address=None, vat_number='', cf_code=''):

        # FIXME/TODO(artcz)(2018-08-20)
        # Temporary import to avoid ciruclar. To get a smaller PR I want to
        # import just the next_order_code. Target here is to replace this
        # create() function with proper implementation in conference/orders.py,
        # similar to how conference/invoicing.py works.
        from conference.orders import next_order_code_for_year

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

        # TODO: replace this timezone.now().year with proper date that can be
        # passed as an argument
        o.code = next_order_code_for_year(timezone.now().year)
        o.save()
        if o.total() == 0:
            o._complete = True
            o.save()
        order_created.send(sender=o, raw_items=items)
        return o


class Vat(models.Model):
    fares = models.ManyToManyField(Fare,
                                   through='VatFare',
                                   null=True, blank=True)
    value = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(null=True, blank=True, max_length=125)
    invoice_notice = models.TextField(null=True, blank=True)

    def __str__(self):
        return "%s%% - %s" % (self.value, self.description or "")


class VatFare(models.Model):
    fare = models.ForeignKey(Fare, on_delete=models.CASCADE)
    vat = models.ForeignKey(Vat, on_delete=models.CASCADE)

    class Meta:
        unique_together =('fare', 'vat')


# segnale emesso quando un ordine, il sender, è stato correttamente registrato
# in locale e sul backend. `raw_items` è la lista degli item utilizzata per
# generare l'ordine; sebbene al momento dell'invio del segnale l'ordine sia già
# stato creato e associato a tutti gli OrderItem, in raw_items potrebbero
# essere presenti informazioni aggiuntive che altrimenti non sarebbe possibile
# recuperare.
order_created = dispatch.Signal(providing_args=['raw_items'])


# Implemented order payment options
ORDER_PAYMENT = (
    ('cc', 'Credit Card'),
    ('paypal', 'PayPal (deprecated)'),
    ('bank', 'Bank'),
)

# This is new for 2019; We can track order type for improved handling of forms
# in the cart.
ORDER_TYPE = Choices(
    ("company", "Company"),
    ("student", "Student"),
    ("personal", "Personal"),
    # Other is for social events, sim cards, etc.
    ("other", "Other"),
)


class Order(models.Model):
    # TODO(artcz) This should have unique=True as well once we backfill data
    # for previous orders.
    uuid = models.CharField(max_length=100, blank=True, default='')
    code = models.CharField(max_length=20, null=True)
    assopy_id = models.CharField(max_length=22, null=True, unique=True, blank=True)
    user = models.ForeignKey(AssopyUser, related_name='orders', on_delete=models.CASCADE)
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
    billing_notes = models.TextField(
        verbose_name="Additional billing notes",
        help_text=(
            "Notes that you want to put on the invoice. "
            "Additional email address, employee name, things required by your "
            "internal accounting department, etc."
        ),
        blank=True
    )

    # Questi dati vengono copiati dallo User al fine di storicizzarli
    card_name = models.CharField(_('Card name'), max_length=200)
    vat_number = models.CharField(_('Vat Number'), max_length=22, blank=True)
    cf_code = models.CharField(_('Fiscal Code'), max_length=16, blank=True)
    # la country deve essere null perché un ordine può essere creato via admin
    # e in quel caso non è detto che si conosca
    country = models.ForeignKey(Country, verbose_name=_('Country'), null=True, on_delete=models.CASCADE)
    address = models.CharField(_('Address'), max_length=150, blank=True)

    stripe_charge_id = models.CharField(_('Charge Stripe ID'), max_length=64, unique=True, null=True)

    payment_date = models.DateTimeField(
        help_text="Auto filled by the payments backend",
        blank=True,
        null=True,
    )

    order_type = models.CharField(
        choices=ORDER_TYPE,
        max_length=20,
        blank=True,
    )

    objects = OrderQuerySet.as_manager()

    def __str__(self):
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
        return list(vat_list.values())

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
        if r and update_cache:
            self._complete = r
            self.save()
        return r

    def confirm_order(self, payment_date):
        # NOTE(artcz)(2018-05-28)
        # This used to generate invoices, currently it just fills payment date,
        # and creates placeholder
        # To avoid ciruclar import
        from conference.invoicing import create_invoices_for_order
        self.payment_date = payment_date
        self.save()
        create_invoices_for_order(self)

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

    def is_complete(self):
        """Wrapper on _complete that can be used in templates"""
        return self._complete

    def total_vat_amount(self):
        return normalize_price(sum(item.raw_vat_value() for item in self.orderitem_set.all()))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    ticket = models.OneToOneField('conference.ticket', null=True, blank=True, on_delete=models.CASCADE)
    code = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.CharField(max_length=100, blank=True)
    # aggiungo un campo per iva... poi potra essere un fk ad un altra tabella
    # o venire copiato da conference
    vat = models.ForeignKey(Vat, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.code} {self.description} -- {self.price}'

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

    def net_price(self):
        """This is ugly workaround because we use gross prices for Fares"""
        # TODO(umgelurgel): We should move the rounding away from the model
        # and into the templates - otherwise, workarounds are needed to
        # support aggregation.
        return normalize_price(self.price / (1 + self.vat.value / 100))

    def vat_value(self):
        # TODO(umgelurgel): Same as in net_price - we should remove the rounding
        # logic from the model.
        return normalize_price(self.raw_vat_value())

    def raw_vat_value(self):
        """
        Used when aggregating - leaving the rounding to the calling context;
        otherwise, this leads to accumulation of rounding errors.
        """
        return (self.price * self.vat.value  / 100) / (1 + self.vat.value / 100)

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
    order = models.ForeignKey(Order, null=True, on_delete=models.CASCADE)
    invoice = models.ForeignKey('Invoice', null=True, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)


class Invoice(models.Model):

    PLACEHOLDER_EXRATE_DATE = date(2000, 1, 1)

    order = models.ForeignKey(Order, related_name='invoices', on_delete=models.CASCADE)
    code = models.CharField(max_length=20, null=True, unique=True)
    assopy_id = models.CharField(max_length=22, unique=True,
                                 null=True, blank=True)
    emit_date = models.DateField()
    payment_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    issuer = models.TextField()
    # TODO: backfill that with customer data for previous invoices
    customer = models.TextField()
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
    vat = models.ForeignKey(Vat, on_delete=models.CASCADE)

    note = models.TextField(
        blank=True,
        help_text='''Testo libero da riportare in fattura; posto al termine delle righe d'ordine riporta di solito gli estremi di legge''')

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

    def __str__(self):
        if self.code:
            return ' #%s' % self.code
        else:
            return 'Invoice id:%d' % self.id

    def get_invoice_filename(self):
        return 'EuroPython_Invoice_%s.pdf' % self.code.replace('/', '-')

    def invoice_items(self):
        return self.order.orderitem_set.filter(vat=self.vat) \
                                  .values('code','description') \
                                  .annotate(count=models.Count('price'),
                                            price=models.Sum('price')) \
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
