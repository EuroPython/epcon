import mptt

from django.apps import AppConfig
from django.db.models.signals import post_save
from django.core.mail import send_mail
from django_comments.models import Comment

import models


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
        send_mail(subject, body, dsettings.DEFAULT_FROM_EMAIL, [u.email])


class HCommentsConfig(AppConfig):
    name = 'hcomments'
    verbose_name = "HComments"

    def ready(self):
        post_save.connect(send_email_to_subscribers, sender=Comment)
        post_save.connect(send_email_to_subscribers, sender=models.HComment)

        mptt.register(models.HComment)
