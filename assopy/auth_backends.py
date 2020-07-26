from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

from assopy.models import AssopyUser, user_created

import logging

log = logging.getLogger('assopy.auth')


class AssopyBackend(ModelBackend):
    def linkUser(self, user):
        """
        collega l'utente assopy passato con il backend; crea l'utente remoto se
        necessario.
        """
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


class IdBackend(AssopyBackend):
    """
    backend utilizzato solo internamente per autenticare utenti dato il loro id
    (senza bisogno di password).
    """
    def authenticate(self, request, uid=None):
        try:
            user = User.objects.select_related('assopy_user').get(
                pk=uid, is_active=True
            )
            assopy_user = user.assopy_user
            if assopy_user is None:
                # questo utente esiste su django ma non ha un utente assopy
                # collegato; probabilmente è un admin inserito prima del
                # collegamento con il backend.
                assopy_user = AssopyUser(user=user)
                assopy_user.save()
                user_created.send(sender=assopy_user, profile_complete=True)
            self.linkUser(assopy_user)
            return user
        except User.DoesNotExist:
            return None


class EmailBackend(AssopyBackend):
    def authenticate(self, request, email=None, password=None, username=None):
        try:
            email = email or username
            user = User.objects.select_related('assopy_user').get(
                email__iexact=email,
                is_active=True
            )
            if user.check_password(password):
                assopy_user = user.assopy_user
                if assopy_user is None:
                    # questo utente esiste su django ma non ha un utente assopy
                    # collegato; probabilmente è un admin inserito prima del
                    # collegamento con il backend.
                    assopy_user = AssopyUser(user=user)
                    assopy_user.save()
                    user_created.send(sender=assopy_user,
                                      profile_complete=True)
                self.linkUser(assopy_user)
                return user
        except User.MultipleObjectsReturned:
            return None
        except User.DoesNotExist:
            # nel db di django non c'è un utente con quella email, ma potrebbe
            # esserci un utente legacy nel backend di ASSOPY
            return None
