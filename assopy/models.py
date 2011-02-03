# -*- coding: UTF-8 -*-
from assopy.clients import genro
from conference.models import Speaker

from django.contrib import auth
from django.db import models
from django.db import transaction

import logging
from datetime import date, datetime

log = logging.getLogger('assopy.models')

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

    #speaker = models.OneToOneField('conference.speaker', null=True)

    objects = UserManager()

    def photo_url(self):
        if self.photo:
            return self.photo.url
        try:
            return self.useridentity_set.exclude(photo='')[0]
        except IndexError:
            return None

    def billing(self):
        u = genro.user(self.assopy_id)
        return {
            'firstname': u.user.firstname,
            'lastname': u.user.lastname,
            'registration_date': datetime.strptime(u.user.registration_date.text, '%Y-%m-%d').date(),
            'email': u.user.email,
            'www': u.card.www,
            'phone': u.card.phone,
            'card_name': u.card.card_name,
            'is_company': u.card.is_company,
            'vat_number': u.card.vat_number,
            'tin_number': u.card.tin_number,
            'address': u.card.address,
            'city': u.card.city,
            'state': u.card.state,
            'zip': u.card.zip,
            'country': u.card.country,
        }

    def name(self):
        if self.assopy_id:
            u = genro.user(self.assopy_id)
            return '%s %s' % (u['user.firstname'], u['user.lastname'])
        else:
            return '%s %s' % (self.user.first_name, self.user.last_name)

    def setSpeakerProfile(self):
        if not self.speaker:
            speaker = Speaker()
            speaker.name= self.name()
            speaker.slug = slugify(speaker.name)
            speaker.save()
            self.speaker = speaker
            self.save()
        return self.speaker

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
