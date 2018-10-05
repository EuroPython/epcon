
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from hcomments import models


def send_email_to_subscribers(sender, **kwargs):
    subscripted = models.ThreadSubscription.objects.subscriptions(kwargs['instance'].content_object)
    for u in filter(lambda x: x.email, subscripted):
        ctx = {
            'comment': kwargs['instance'],
            'object': kwargs['instance'].content_object,
            'user': u,
        }
        subject = 'New comment on a subscribed page'
        body = render_to_string('hcomments/thread_email.txt', ctx)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [u.email])
