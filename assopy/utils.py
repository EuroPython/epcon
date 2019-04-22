
from django.conf import settings as dsettings
from django.contrib import auth


from assopy import settings

def get_user_account_from_email(email, default='raise', active_only=True):

    """ Return the user record for the user with the given email
        address.

        Only active user records are taken into account, if
        active_only is true (default).

        Note: The system expects the email addresses to be unique
        among active user records. If there are multiple active user
        records with the same email address, a MultipleObjectsReturned
        exception is raised.

        If the user record does not exist (or exists but is not active
        and active_only is set), a DoesNotExist exception is raised if
        default is set to 'raise' (default). Otherwise, default is
        returned.

    """
    email = email.strip()
    try:
        return auth.models.User.objects.get(email__iexact=email,
                                            is_active=active_only)
    except auth.models.User.DoesNotExist:
        # User does not exist
        if default == 'raise':
            raise
        else:
            return default
    except auth.models.User.MultipleObjectsReturned:
        # The system expects to only have one user record per email,
        # so let's reraise the error to have it fixed in the database.
        raise auth.models.User.MultipleObjectsReturned(
            'Found multiple records for user with email %r' % email)

def send_email(force=False, *args, **kwargs):
    if force is False and not settings.SEND_EMAIL_TO:
        return
    if 'recipient_list' not in kwargs:
        kwargs['recipient_list'] = settings.SEND_EMAIL_TO
    if 'from_email' not in kwargs:
        kwargs['from_email'] = dsettings.DEFAULT_FROM_EMAIL
    from django.core.mail import send_mail as real_send_mail
    real_send_mail(*args, **kwargs)

def dotted_import(path):
    from importlib import import_module
    from django.core.exceptions import ImproperlyConfigured
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]

    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured('Error importing %s: "%s"' % (path, e))

    try:
        o = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define "%s"' % (module, attr))

    return o
