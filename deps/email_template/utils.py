# -*- coding: UTF-8 -*-
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404
from email_template import models

def email(code, ctx, mark_safestring=True, **kw):
    e = get_object_or_404(models.Email, code = code)
    subject, body = e.render(ctx, mark_safestring=mark_safestring)
    email = EmailMessage()
    email.subject = subject
    email.body = body
    if e.from_email and 'from_email' not in kw:
        kw['from_email'] = e.from_email
    for key, value in kw.items():
        setattr(email, key, value)
    if e.bcc:
        email.bcc += [ x.strip() for x in e.bcc.split(',') ]
    if e.cc:
        email.cc += [ x.strip() for x in e.cc.split(',') ]
    return email
