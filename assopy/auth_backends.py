# -*- coding: UTF-8 -*-
from django.contrib.auth.backends import ModelBackend
from django.core.validators import email_re
from django.contrib.auth.models import User

from assopy import models
from assopy.clients import genro

import logging

log = logging.getLogger('assopy.auth')

class _AssopyBackend(ModelBackend):
    def linkUser(self, user):
        """
        collega l'utente assopy passato con il backend; crea l'utente remoto se
        necessario.
        """
        name = unicode(user.user).encode('utf-8')
        if not user.verified:
            log.info('cannot link a remote user to "%s": it\'s not verified', name) 
            return
        if user.assopy_id:
            return user

        log.info('a remote user is needed for "%s"', name)
        # il lookup con l'email può ritornare più di un id; non è un
        # problema dato che associo lo user con il backend solo quando ho
        # verificato l'email (e la verifica non è necessaria se si loggano
        # con janrain), quindi posso usare una qualsiasi delle identità
        # remote. Poi un giorno implementeremo il merge delle identità.
        rid = genro.users(email=user.user.email)['r0']
        if rid is not None:
            log.info('an existing match with the email "%s" is found: %s', user.user.email, rid)
        else:
            rid = genro.create_user(user.user.first_name, user.user.last_name, user.user.email)
            log.info('new remote user id: %s', rid)
        user.assopy_id = rid
        user.save()
        return user

class EmailBackend(_AssopyBackend):
    def authenticate(self, email=None, password=None):
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                self.linkUser(user.assopy_user)
                return user
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None

class JanRainBackend(_AssopyBackend):
    def authenticate(self, identifier=None):
        try:
            i = models.UserIdentity.objects.select_related('user__user').get(identifier=identifier)
        except models.UserIdentity.DoesNotExist:
            return None
        else:
            self.linkUser(i.user)
            return i.user.user
