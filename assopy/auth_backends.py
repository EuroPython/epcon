# -*- coding: UTF-8 -*-
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import transaction

from assopy import models
from assopy import settings
if settings.GENRO_BACKEND:
    from assopy.clients import genro

import logging

log = logging.getLogger('assopy.auth')

class _AssopyBackend(ModelBackend):
    def linkUser(self, user):
        """
        collega l'utente assopy passato con il backend; crea l'utente remoto se
        necessario.
        """
        if not settings.GENRO_BACKEND:
            return user
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
            user.assopy_id = rid
            user.save()
            genro.user_remote2local(user)
        else:
            rid = genro.create_user(user.user.first_name, user.user.last_name, user.user.email)
            log.info('new remote user id: %s', rid)
            user.assopy_id = rid
            user.save()
        return user

    def get_user(self, user_id):
        # ridefinisco la get_user per assicurarmi che l'utente django e quello
        # assopy vengano recuperarti utilizzando una sola query. Da che
        # l'utilizzo tipo nei template è:
        #   {{ request.user.assopy_user.name }}
        # questa select_related mi permette di ridurre il numero di query da 3
        # a 1:
        #   request.user        -> 1 query
        #       .assopy_user    -> 1 query
        #       .name           -> 1 query (tra l'altro per recuperare
        #                          nuovamente l'utente django)
        try:
            return User.objects\
                .select_related('assopy_user')\
                .get(pk=user_id)
        except User.DoesNotExist:
            return None

class IdBackend(_AssopyBackend):
    """
    backend utilizzato solo internamente per autenticare utenti dato il loro id
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
                models.user_created.send(sender=auser, profile_complete=True)
            self.linkUser(auser)
            return user
        except User.DoesNotExist:
            return None

class EmailBackend(_AssopyBackend):
    def authenticate(self, email=None, password=None):
        try:
            user = User.objects.select_related('assopy_user').get(email__iexact=email, is_active=True)
            if user.check_password(password):
                auser = user.assopy_user
                if auser is None:
                    # questo utente esiste su django ma non ha un utente assopy
                    # collegato; probabilmente è un admin inserito prima del
                    # collegamento con il backend.
                    auser = models.User(user=user)
                    auser.save()
                    models.user_created.send(sender=auser, profile_complete=True)
                self.linkUser(auser)
                return user
        except User.MultipleObjectsReturned:
            return None
        except User.DoesNotExist:
            # nel db di django non c'è un utente con quella email, ma potrebbe
            # esserci un utente legacy nel backend di ASSOPY
            if not settings.GENRO_BACKEND or not settings.SEARCH_MISSING_USERS_ON_BACKEND:
                return None
            rid = genro.users(email=email, password=password)['r0']
            if rid is not None:
                log.info('"%s" is a valid remote user; a local user is needed', email)
                auser = models.User.objects.create_user(email, password=password, active=True, assopy_id=rid, send_mail=False)
                return auser.user
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
