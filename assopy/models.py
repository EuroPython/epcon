# -*- coding: UTF-8 -*-
from assopy import django_urls
from assopy import janrain
from assopy.clients import genro, vies
from assopy.utils import send_email
from conference.models import Fare, Ticket, Speaker

from django import dispatch
from django import template
from django.conf import settings as dsettings
from django.contrib import auth
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import connection
from django.db import models
from django.db import transaction
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

import re
import os
import os.path
import logging
from uuid import uuid4
from datetime import date, datetime
from decimal import Decimal

log = logging.getLogger('assopy.models')

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

class UserManager(models.Manager):
    @transaction.commit_on_success
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
        log.info(
            'new local user "%s" created; for "%s %s" (%s)',
            duser.username, first_name, last_name, email,
        )
        if assopy_id is not None:
            genro.user_remote2local(user)
        if send_mail:
            ctx = {
                'user': duser,
                'token': Token.objects.create(ctype='v', user=duser),
            }
            body = template.loader.render_to_string('assopy/email/verify_user.txt', ctx)
            mail.send_mail('Verify your account', body, 'info@pycon.it', [ email ])
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

USER_ACCOUNT_TYPE = (
    ('p', 'Private'),
    ('c', 'Company'),
)
class User(models.Model):
    user = models.OneToOneField("auth.User", related_name='assopy_user')
    token = models.CharField(max_length=36, unique=True, null=True, blank=True)
    assopy_id = models.CharField(max_length=22, null=True, unique=True)
    photo = models.ImageField(_('Photo'), null=True, blank=True, upload_to=_fs_upload_to('users', attr=lambda i: i.user.username))
    twitter = models.CharField(_('Twitter'), max_length=20, blank=True)
    skype = models.CharField(_('Skype'), max_length=20, blank=True)
    jabber = models.EmailField(_('Jabber'), blank=True)
    www = models.URLField(_('Www'), verify_exists=False, blank=True)
    phone = models.CharField(
        _('Phone'), 
        max_length=30, blank=True,
        help_text=_('Enter a phone number where we can contact you in case of administrative issues.<br />Use the international format, eg: +39-055-123456'),
    )
    birthday = models.DateField(_('Birthday'), null=True, blank=True)
    card_name = models.CharField(_('Card name'), max_length=200, blank=True)
    account_type = models.CharField(_('Account type'), max_length=1, choices=USER_ACCOUNT_TYPE, default='p')
    vat_number = models.CharField(_('Vat Number'), max_length=22, blank=True)
    tin_number = models.CharField(_('Tax Identification Number'), max_length=16, blank=True)
    country = models.ForeignKey(Country, verbose_name=_('Country'), null=True, blank=True)
    zip_code = models.CharField(_('Zip Code'), max_length=5, blank=True)
    address = models.CharField(
        _('Address and City'),
        max_length=150,
        blank=True,
        help_text=_('Insert the full address, including city and zip code. We will help you through google.'),)
    city = models.CharField(_('City'), max_length=40, blank=True)
    state = models.CharField(_('State'), max_length=2, blank=True)

    objects = UserManager()

    def __unicode__(self):
        return 'Assopy user: %s' % self.name()

    def photo_url(self):
        if self.photo:
            return self.photo.url
        try:
            return self.identities.exclude(photo='')[0].photo
        except IndexError:
            return _gravatar(self.user.email)

    def name(self):
        name = '%s %s' % (self.user.first_name, self.user.last_name)
        if not name.strip():
            return self.user.email
        else:
            return name

    def clean_fields(self, *args, **kwargs):
        super(User, self).clean_fields(*args, **kwargs)
        # check del vat_number. Al posso verificare solo i codici europei
        # tramite vies
        if self.account_type == 'c' and self.vat_number:
            if self.country.vat_company_verify == 'v':
                if not vies.check_vat(self.country.pk, self.vat_number):
                    raise ValidationError({'vat_number': [_('According to VIES, this is not a valid vat number')]})
            
    def save(self, *args, **kwargs):
        super(User, self).save(*args, **kwargs)
        if self.assopy_id:
            genro.user_local2remote(self)

    def tickets(self):
        tickets = []
        ticket_for_user.send(sender=self, tickets=tickets)
        if not tickets:
            tickets = Ticket.objects.conference(dsettings.CONFERENCE_CONFERENCE).filter(user=self.user)
        return tickets

    def invoices(self):
        if self.orders.count() == 0:
            return []
        output = []
        data = genro.user_invoices(self.assopy_id)
        r = 0
        while True:
            i = data['r_%d' % r]
            if not i:
                break
            r += 1
            try:
                o = Order.objects.get(assopy_id=i['order_id'])
            except Order.DoesNotExist:
                continue
            output.append({
                'id': i['id'],
                'invoice': i['number'],
                'order': o,
            })
        return output

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
        return identifier

class UserIdentity(models.Model):
    identifier = models.CharField(max_length=255, primary_key=True)
    user = models.ForeignKey(User, related_name='identities')
    provider = models.CharField(max_length=255)
    display_name = models.TextField(blank=True)
    gender = models.CharField(max_length=10, blank=True)
    birthday = models.DateField(null=True)
    email = models.EmailField(blank=True)
    url = models.URLField(verify_exists=False)
    photo = models.URLField(verify_exists=False)
    phoneNumber = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    objects = UserIdentityManager()

class UserOAuthInfo(models.Model):
    user = models.ForeignKey(User, related_name='oauth_infos')
    service = models.CharField(max_length=20)
    token = models.CharField(max_length=200)
    secret = models.CharField(max_length=200)

class Coupon(models.Model):
    conference = models.ForeignKey('conference.Conference')
    code = models.CharField(max_length=10)
    start_validity = models.DateField(null=True, blank=True)
    end_validity = models.DateField(null=True, blank=True)
    max_usage = models.PositiveIntegerField(default=0)
    description = models.CharField(max_length=100, blank=True)
    value = models.CharField(max_length=6, help_text='importo, eg: 10, 15%, 8.5')

    def __unicode__(self):
        return '%s (%s)' % (self.code, self.value)

    def clean(self):
        if re.search(r'[^\d\%]+', self.value):
            raise ValidationError('il valore del coupon contiene un carattere non valido')

    def type(self):
        if self.value.endswith('%'):
            return 'perc'
        else:
            return 'val'

    def valid(self):
        if self.start_validity and self.end_validity:
            today = date.today()
            if today < self.start_validity or today > self.end_validity:
                return False

        if self.max_usage:
            if OrderItem.objects.exclude(ticket=None).filter(code=self.code).count() >= self.max_usage:
                return False
        return True

    def apply(self, total, guard=None):
        if self.type() == 'val':
            v = Decimal(self.value)
        else:
            v = total / 100 * Decimal(self.value[:-1]) 
        if guard is not None:
            if v > guard:
                v = guard
        return v

class OrderManager(models.Manager):
    @transaction.commit_on_success
    def create(self, user, payment, items, billing_notes='', coupons=None, remote=True):
        if coupons:
            for c in coupons:
                if not c.valid():
                    log.warn('Invalid coupon: %s', c.code)
                    raise ValueError(c)

        log.info('new order for "%s" via "%s": %d items', user.name(), payment, sum(x[1] for x in items))
        o = Order()
        o.code = None
        o.method = payment
        o.user = user

        o.billing_notes = billing_notes

        o.card_name = user.card_name or user.name()
        o.vat_number = user.vat_number
        o.tin_number = user.tin_number
        o.country = user.country
        o.zip_code = user.zip_code
        o.address = user.address
        o.city = user.city
        o.state = user.state

        o.save()
        for f, q in items:
            for _ in range(q):
                a = Ticket(user=user.user, fare=f)
                a.save()
                item = OrderItem(order=o, ticket=a)
                item.code = f.code
                item.description = f.name
                item.price = f.price
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
            for c in coupons:
                if c.type() == 'perc':
                    item = OrderItem(order=o, ticket=None)
                    item.code = c.code
                    item.description = c.description
                    item.price = -1 * c.apply(tickets_total, o.total())
                    item.save()
                    log.debug('coupon "%s" applied, discount=%s', item.code, item.price)
            for c in coupons:
                if c.type() == 'val':
                    item = OrderItem(order=o, ticket=None)
                    item.code = c.code
                    item.description = c.description
                    item.price = -1 * c.apply(o.total(), o.total())
                    item.save()
                    log.debug('coupon "%s" applied, discount=%s', item.code, item.price)
        log.info('order "%s" and tickets created locally: tickets total=%s order total=%s', o.id, tickets_total, o.total())
        if remote:
            genro.create_order(
                o,
                return_url=dsettings.DEFAULT_URL_PREFIX + reverse('assopy-paypal-feedback-ok', kwargs={'code': '%(code)s'})
            )
            log.info('order "%s" created remotly -> #%s', o.id, o.code)
        if o.total() == 0:
            o._complete = True
            o.save()
        order_created.send(sender=o)
        return o

# segnale emesso quando un ordine, il sender, è stato correttamente registrato
# in locale e sul backend.
order_created = dispatch.Signal(providing_args=[])

# segnale emesso da un ordine quando un questo viene "completato".  Al momento
# l'unico meccanismo per accorgersi se un ordine è completo è pollare il
# backend attraverso il metodo Order.complete.
purchase_completed = dispatch.Signal(providing_args=[])

ORDER_PAYMENT = (
    ('paypal', 'PayPal'),
    ('cc', 'Credit Card'),
    ('bank', 'Bank'),
)
class Order(models.Model):
    code = models.CharField(max_length=9, null=True)
    assopy_id = models.CharField(max_length=22, null=True, unique=True)
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
    tin_number = models.CharField(_('Tax Identification Number'), max_length=16, blank=True)
    country = models.ForeignKey(Country, verbose_name=_('Country'))
    zip_code = models.CharField(_('Zip Code'), max_length=5, blank=True)
    address = models.CharField(_('Address'), max_length=150, blank=True)
    city = models.CharField(_('City'), max_length=40, blank=True)
    state = models.CharField(_('State'), max_length=2, blank=True)

    objects = OrderManager()

    def billable(self):
        """
        Regola per verificare se un ordine è fatturabile:

        Se la nazione è l'ITALIA serve VAT e TIN
        Se la nazione sono gli USA serve VAT e TIN
        Se la nazione è EUROPEA basta il VAT ma deve passare il controllo VIES
        Altrimenti basta il VAT
        """
        if self.country_id == 'IT':
            return self.vat_number and self.tin_number
        elif self.country_id == 'US':
            return self.vat_number and self.tin_number
        elif self.country.vat_company_verify:
            if self.country.vat_company_verify == 'v':
                return vies.check_vat(self.country_id, self.vat_number)
            else:
                raise RuntimeError('unknown verification method')
        else:
            return bool(self.vat_number)
    
    def vat_rate(self):
        """
        Regola per determinare l'aliquota iva:

        Se la nazione è l'ITALIA l'aliquota è il 20%
        Se l'ordine è fatturabile l'aliquota è lo 0%
        Altrimenti l'aliquota è il 20%
        """
        # contr'ordine, per quest'anno, 2011, l'IVA, per le conferenze, è
        # sempre il 20% indipendentemente da tutto
        return 20.0
        #if self.country_id == 'IT':
        #    return 20.0
        #elif self.billable():
        #    return 0.0
        #else:
        #    return 20.0

    def invoices(self):
        output = []
        if self.assopy_id:
            data = genro.order(self.assopy_id)
            ix = 0
            while True:
                invoice = data['invoices.i%d' % ix]
                if not invoice:
                    break
                output.append((invoice['id'], invoice['number'], invoice['invoice_date'], invoice['payment_date']))
                ix += 1
        return output
        
    def complete(self, update_cache=True, ignore_cache=False):
        if self._complete and not ignore_cache:
            return True
        if not self.assopy_id:
            # non ha senso chiamare .complete su un ordine non associato al
            # backend
            return False
        # un ordine risulta pagato se tutte le sue fatture riportano la data
        # del pagamento
        invoices = [ i[3] for i in self.invoices() ]
        r = len(invoices) > 0 and all(invoices)
        if r and not self._complete:
            log.info('purchase of order "%s" completed', self.code)
            purchase_completed.send(sender=self)
        if r and update_cache:
            self._complete = r
            self.save()
        return r

    def deductible(self):
        """
        Ritorna True/False a seconda che l'ordine sia deducibile o meno
        """
        # considero non deducibile un ordine che contiene almeno un biglietto
        # per la conferenza destinato a privati/studenti
        qs = Fare.objects\
            .filter(id__in=self.orderitem_set.exclude(ticket=None).values('ticket__fare'))\
            .values_list('recipient_type', 'ticket_type')
        deductible = True
        for r, t in qs:
            if t == 'conference' and r != 'c':
                deductible = False
                break
        return deductible

    def total(self, apply_discounts=True):
        if apply_discounts:
            t = self.orderitem_set.aggregate(t=models.Sum('price'))['t']
        else:
            t = self.orderitem_set.filter(price__gt=0).aggregate(t=models.Sum('price'))['t']
        return t if t is not None else 0

    @classmethod
    def calculator(self, items, coupons=None):
        """
        calcola l'importo di un ordine non ancora effettuato tenendo conto di
        eventuali coupons.
        """
        # sono le stesse regole utilizzate dalla OrderManager.create
        totals = {
            'tickets': {},
            'coupons': {},
            'total': 0,
        }
        tickets_total = 0
        for f, q in items:
            totals['tickets'][f.code] = (f.price * q, q, f)
            tickets_total += f.price * q

        total = tickets_total
        if coupons:
            for c in coupons:
                if c.type() == 'perc':
                    v = -1 * c.apply(tickets_total, total)
                    totals['coupons'][c.code] = (v, c)
                    total += v

            for c in coupons:
                if c.type() == 'val':
                    v = -1 * c.apply(total, total)
                    totals['coupons'][c.code] = (v, c)
                    total += v

        totals['total'] = total
        return totals

class OrderItem(models.Model):
    order = models.ForeignKey(Order)
    ticket = models.OneToOneField('conference.ticket', null=True)
    code = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.CharField(max_length=100, blank=True)

def _order_feedback(sender, **kwargs):
    rows = [
        'Utente: "%s" (%s)' % (sender.user.name(), sender.user.user.email),
        'Ragione sociale: "%s"' % (sender.card_name,),
        'Metodo di pagamento: "%s"' % (sender.method,),
        'Nazione: "%s"' % (sender.country.name,),
        'Indirizzo: "%s"' % (sender.address,),
        'Note di fatturazione:\n%s\n' % (sender.billing_notes,),
        'Biglietti acquistati:',
    ]
    for x in sender.orderitem_set.order_by('ticket__fare__code').select_related():
        rows.append('%-5s %-47s %6.2f' % (x.code, x.description, x.price))
    rows.append('-' * 60)
    rows.append('%54s%6.2f' % ('', sender.total()))
    send_email(
        subject='New order: %s, from "%s %s"' % (sender.code, sender.user.user.first_name, sender.user.user.last_name,),
        message='\n'.join(rows),
    )

order_created.connect(_order_feedback)
