# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.core.mail import send_mail as real_send_mail

from assopy import settings

def send_email(force=False, *args, **kwargs):
    if force is False and not settings.SEND_EMAIL_TO:
        return
    if 'recipient_list' not in kwargs:
        kwargs['recipient_list'] = settings.SEND_EMAIL_TO
    if 'from_email' not in kwargs:
        kwargs['from_email'] = dsettings.DEFAULT_FROM_EMAIL
    real_send_mail(*args, **kwargs)

