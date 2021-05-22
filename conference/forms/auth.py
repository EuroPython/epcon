from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm


class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        """Given an email, return matching user(s) who should receive a reset.

        This allows subclasses to more easily customize the default policies
        that prevent inactive users and users with unusable passwords from
        resetting their password.
        """
        user_model = get_user_model()
        active_users = user_model._default_manager.filter(**{
            'email__iexact': email,
            'is_active': True,
        })
        d = (u for u in active_users)
        return d
