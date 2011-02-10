# -*- coding: UTF-8 -*-
from assopy.clients import genro
from conference.models import Speaker

from django.contrib import auth
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

class User(models.Model):
    user = models.OneToOneField("auth.User", related_name='assopy_user')
    assopy_id = models.CharField(max_length=22, blank=True, unique=True)
    verified = models.BooleanField(default=False)
    photo = models.ImageField(null=True, upload_to='assopy/users')

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
        return dict(genro.user(self.assopy_id))

    def setBilling(self, **kwargs):
        data = self.billing()
        data.update(kwargs)
        genro.setUser(self.assopy_id, data)

    @_cache
    def profile(self):
        billing = self.billing()
        data = {
            'photo': self.photo_url(),
            'name': self.name(),
            'www': billing['www'],
        }
        return data

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
