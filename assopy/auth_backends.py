# -*- coding: UTF-8 -*-

# see: http://djangosnippets.org/snippets/74/#c195

from django.contrib.auth.backends import ModelBackend
from django.core.validators import email_re
from django.contrib.auth.models import User

class EmailBackend(ModelBackend):
    def authenticate(self, email=None, password=None):
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

