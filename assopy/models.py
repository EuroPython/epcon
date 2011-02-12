# -*- coding: UTF-8 -*-
from assopy import django_urls
from assopy import janrain
from assopy.clients import genro
from conference.models import Attendee, Speaker

from django import template
from django.contrib import auth
from django.core import mail
from django.core.urlresolvers import reverse
from django.db import connection
from django.db import models
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

import logging
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

class TokenManager(models.Manager):
    def create(self, user, ctype=''):
        from uuid import uuid4
        Token.objects.filter(user=user, ctype=ctype).delete()
        t = Token()
        t.token = str(uuid4())
        t.ctype = ctype
        t.user = user
        t.save()
        return t

    def _get_token(self, token):
        try:
            return Token.objects.get(token=token)
        except Token.DoesNotExist:
            return None

    def check(self, token):
        t = self._get_token(token)
        if t is not None:
            return t.user, t.ctype
        else:
            return None, None

    def validate(self, token):
        t = self._get_token(token)
        if t is not None:
            t.delete()
            return t.user, t.ctype
        else:
            return None, None

class Token(models.Model, django_urls.UrlMixin):
    """
    modello che mantiene codici univoci, utilizzabili una sola volta, di
    diverso tipo per ogni utente.
    """
    token = models.CharField(max_length=36, primary_key=True)
    ctype = models.CharField(max_length=1)
    user = models.ForeignKey(auth.models.User, unique=True)
    created = models.DateTimeField(auto_now_add=True)

    objects = TokenManager()

    def get_url_path(self):
        return reverse('assopy-otc-token', kwargs={'token': self.token})       

class UserManager(models.Manager):
    @transaction.commit_on_success
    def create_from_backend(self, rid, email, password=None, verified=False):
        info = genro.user(rid)
        user = auth.models.User.objects.create_user('_' + info['user.username'], email, password)
        user.first_name = info['user.firstname']
        user.last_name = info['user.lastname']
        user.save()

        u = User(user=user)
        u.assopy_id = rid
        u.verified = verified
        u.save()
        log.debug('new local user created "%s"', user)
        return u

    @transaction.commit_on_success
    def create_user(self, email, first_name='', last_name='', password=None, verified=False, send_mail=True):
        uname = janrain.suggest_username_from_email(email)
        duser = auth.models.User.objects.create_user(uname, email, password=password)
        duser.first_name = first_name
        duser.last_name = last_name
        duser.save()
        user = User(user=duser, verified=verified)
        user.save()
        log.info(
            'new local user "%s" created; for "%s %s" (%s)',
            duser.username, first_name, last_name, email,
        )
        if send_mail:
            ctx = {
                'user': duser,
                'token': Token.objects.create(duser),
            }
            body = template.loader.render_to_string('assopy/email/verify_user.txt', ctx)
            mail.send_mail('Verify your account', body, 'info@pycon.it', [ email ])
        return user

class User(models.Model):
    user = models.OneToOneField("auth.User", related_name='assopy_user')
    assopy_id = models.CharField(max_length=22, blank=True, unique=True)
    verified = models.BooleanField(default=False)
    photo = models.ImageField(null=True, upload_to='assopy/users')
    twitter = models.CharField(max_length=20, blank=True)
    www = models.URLField(verify_exists=False, blank=True)

    objects = UserManager()

    def photo_url(self):
        if self.photo:
            return self.photo.url
        try:
            return self.useridentity_set.exclude(photo='')[0]
        except IndexError:
            return _gravatar(self.user.email)

    @_cache
    def billing(self):
        d = dict(genro.user(self.assopy_id))
        if d.pop('is_company'):
            d['account_type'] = 'company'
        else:
            d['account_type'] = 'private'
        return d

    def setBilling(self, **kwargs):
        data = self.billing()
        data.update(kwargs)
        if data.pop('account_type') == 'company':
            data['is_company'] = True
        else:
            data['is_company'] = False
        genro.setUser(self.assopy_id, data)

    def name(self):
        if self.assopy_id:
            u = self.billing()
            return '%s %s' % (u['firstname'], u['lastname'])
        else:
            return '%s %s' % (self.user.first_name, self.user.last_name)

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
    user = models.ForeignKey(User)
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

class Country(models.Model):
    iso = models.CharField(_('ISO alpha-2'), max_length=2, primary_key=True)
    name = models.CharField(max_length=100) 
    vat_company = models.BooleanField('VAT for company', default=False)
    vat_person = models.BooleanField('VAT for person', default=False)
    iso3 = models.CharField(_('ISO alpha-3'), max_length=3, null=True)
    numcode = models.PositiveSmallIntegerField(_('ISO numeric'), null=True)
    printable_name = models.CharField(_('Country name'), max_length=128)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Countries'

    def __unicode__(self):
        return self.name

class OrderManager(models.Manager):
    @transaction.commit_manually
    def create(self, user, payment, items):
        log.info('new order for "%s" via "%s": %d items', user, payment, sum(x[1] for x in items))
        y = date.today().year
        cursor = connection.cursor()
        # qui ho bisogno di impedire che altre connessioni possano leggere il
        # db fino a quando non ho creato l'ordine
        cursor.execute('BEGIN EXCLUSIVE TRANSACTION')
        try:
            try:
                last = self.filter(code__startswith=str(y)).order_by('-created').values('code')[0]
            except IndexError:
                last_code = 0
            else:
                last_code = int(last['code'][4:])
            o = Order()
            o.code = '%s%s' % (y, str(last_code+1).zfill(4))
            o.user = user
            o.save()
            for t, q in items:
                item = OrderItem(order=o, ticket=t, quantity=q)
                item.save()
        except:
            transaction.rollback()
            raise
        else:
            transaction.commit()
        log.info('local order created: %s', o.code)
        for t, q in items:
            for _ in range(q):
                a = Attendee(user=user, ticket=t)
                a.save()
        transaction.commit()
        log.info('local attendees created for order: %s', o.code)
        return o

class Order(models.Model):
    code = models.CharField(max_length=8, primary_key=True)
    assopy_id = models.CharField(max_length=22, null=True, unique=True)
    user = models.ForeignKey('auth.User')
    created = models.DateTimeField(auto_now_add=True)

    objects = OrderManager()

    def complete(self):
        return True

class OrderItem(models.Model):
    order = models.ForeignKey(Order)
    ticket = models.ForeignKey('conference.ticket')
    quantity = models.PositiveIntegerField()
