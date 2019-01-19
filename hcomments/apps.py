
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_email_to_subscribers(sender, **kwargs):
    subscripted = models.ThreadSubscription.objects.subscriptions(kwargs['instance'].content_object)
    for u in [x for x in subscripted if x.email]:
        ctx = {
            'comment': kwargs['instance'],
            'object': kwargs['instance'].content_object,
            'user': u,
        }
        subject = 'New comment on a subscribed page'
        body = render_to_string('hcomments/thread_email.txt', ctx)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [u.email])
