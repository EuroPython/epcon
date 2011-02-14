# -*- coding: UTF-8 -*-
from django.contrib.auth.backends import ModelBackend
from django.core.validators import email_re
from django.contrib.auth.models import User
from django.db import transaction

from assopy import models
from assopy import settings
from assopy.clients import genro

import logging

log = logging.getLogger('assopy.auth')

class _AssopyBackend(ModelBackend):
    @transaction.commit_on_success
    def linkUser(self, user):
        """
        collega l'utente assopy passato con il backend; crea l'utente remoto se
        necessario.
        """
        if user.assopy_id:
            return user
        name = unicode(user.user).encode('utf-8')
        if not user.user.is_active:
            log.info('cannot link a remote user to "%s": it\'s not active', name) 
            return

        log.info('a remote user is needed for "%s"', name)
        # il lookup con l'email può ritornare più di un id; non è un
        # problema dato che associo lo user con il backend solo quando ho
        # verificato l'email (e la verifica non è necessaria se si loggano
        # con janrain), quindi posso usare una qualsiasi delle identità
        # remote. Poi un giorno implementeremo il merge delle identità.
        rid = genro.users(email=user.user.email)['r0']
        if rid is not None:
            log.info('an existing match with the email "%s" is found: %s', user.user.email, rid)
            data = genro.user(rid)
            migrate = {
                'www': data['www'],
            }
        else:
            rid = genro.create_user(user.user.first_name, user.user.last_name, user.user.email)
            migrate = {}
            log.info('new remote user id: %s', rid)
        user.assopy_id = rid
        for k in ('www',):
            setattr(user, k, migrate.get(k, ''))
        user.save()
        return user

class IdBackend(_AssopyBackend):
    """
    backend utilizzato solo internamento per autenticare utenti dato il loro id
    (senza bisogno di password).
    """
    def authenticate(self, uid=None):
        try:
            user = User.objects.select_related('assopy_user').get(pk=uid, is_active=True)
            auser = user.assopy_user
            if auser is None:
                # questo utente esiste su django ma non ha un utente assopy
                # collegato; probabilmente è un admin inserito prima del
                # collegamento con il backend.
                auser = models.User(user=user)
                auser.save()
            self.linkUser(auser)
            return user
        except User.DoesNotExist:
            return None

class EmailBackend(_AssopyBackend):
    def authenticate(self, email=None, password=None):
        try:
            user = User.objects.select_related('assopy_user').get(email=email, is_active=True)
            if user.check_password(password):
                auser = user.assopy_user
                if auser is None:
                    # questo utente esiste su django ma non ha un utente assopy
                    # collegato; probabilmente è un admin inserito prima del
                    # collegamento con il backend.
                    auser = models.User(user=user)
                    auser.save()
                self.linkUser(auser)
                return user
        except User.MultipleObjectsReturned:
            return None
        except User.DoesNotExist:
            # nel db di django non c'è un utente con quella email, ma potrebbe
            # esserci un utente legacy nel backend di ASSOPY
            if not settings.SEARCH_MISSING_USERS_ON_BACKEND:
                return None
            rid = genro.users(email=email, password=password)['r0']
            if rid is not None:
                log.info('"%s" is a valid remote user; a local user is needed', email)
                u = models.User.objects.create_from_backend(rid, email, password=password, active=True)
                return u.user
            else:
                return None

class JanRainBackend(_AssopyBackend):
    def authenticate(self, identifier=None):
        try:
            i = models.UserIdentity.objects.select_related('user__user').get(identifier=identifier, user__user__is_active=True)
        except models.UserIdentity.DoesNotExist:
            return None
        else:
            self.linkUser(i.user)
            return i.user.user
