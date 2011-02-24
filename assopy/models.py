# -*- coding: UTF-8 -*-
from assopy import django_urls
from assopy import janrain
from assopy.clients import genro, vies
from conference.models import Ticket, Speaker

from django import template
from django.conf import settings as dsettings
from django.contrib import auth
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import connection
from django.db import models
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

import os
import os.path
import logging
from uuid import uuid4
from datetime import date, datetime

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

USER_ACCOUNT_TYPE = (
    ('p', 'Private'),
    ('c', 'Company'),
)
class User(models.Model):
    user = models.OneToOneField("auth.User", related_name='assopy_user')
    token = models.CharField(max_length=36, unique=True, null=True)
    assopy_id = models.CharField(max_length=22, null=True, unique=True)
    photo = models.ImageField(null=True, blank=True, upload_to=_fs_upload_to('users', attr=lambda i: i.user.username))
    twitter = models.CharField(max_length=20, blank=True)
    skype = models.CharField(max_length=20, blank=True)
    jabber = models.EmailField(blank=True)
    www = models.URLField(verify_exists=False, blank=True)
    phone = models.CharField(
        max_length=30, blank=True,
        help_text=_('Enter a phone number where we can contact you in case of administrative issues.<br />Use the international format, eg: +39-055-123456'),
    )
    birthday = models.DateField(null=True, blank=True)
    card_name = models.CharField(max_length=200, blank=True)
    account_type = models.CharField(max_length=1, choices=USER_ACCOUNT_TYPE, default='p')
    vat_number = models.CharField(max_length=22, blank=True)
    cf_number = models.CharField(max_length=16, blank=True)
    country = models.ForeignKey(Country, null=True, blank=True)
    zip_code = models.CharField(max_length=5, blank=True)
    address = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=40, blank=True)
    provincia = models.CharField(max_length=2, blank=True)

    objects = UserManager()

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

class OrderManager(models.Manager):
    @transaction.commit_on_success
    def create(self, user, payment, items):
        log.info('new order for "%s" via "%s": %d items', user, payment, sum(x[1] for x in items))
        o = Order()
        o.code = None
        o.method = payment
        o.user = user
        o.save()
        for f, q in items:
            for _ in range(q):
                a = Ticket(user=user.user, fare=f)
                a.save()
                item = OrderItem(order=o, ticket=a)
                item.save()
        log.info('order "%s" and tickets created locally', o.id)
        return o

ORDER_PAYMENT = (
    ('paypal', 'PayPal'),
    ('bank', 'Bank'),
)
class Order(models.Model):
    code = models.CharField(max_length=8, null=True)
    assopy_id = models.CharField(max_length=22, null=True, unique=True)
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=6, choices=ORDER_PAYMENT)

    objects = OrderManager()

    def complete(self):
        return True

    def total(self):
        return self.orderitem_set.aggregate(t=models.Sum('ticket__fare__price'))['t']

class OrderItem(models.Model):
    order = models.ForeignKey(Order)
    ticket = models.OneToOneField('conference.ticket')
