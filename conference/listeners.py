# -*- coding: UTF-8 -*-
from conference.models import Talk, Event, TalkSpeaker

from django.dispatch import Signal
from django.db.models.signals import post_save
from conference import settings

import logging

log = logging.getLogger('conference')

# Signal when a speaker will sent a new talk
new_paper_submission = Signal(providing_args=['talk'])

def _new_paper_email(sender, **kw):
    """
    Send an email to the organizers with details on the paper presented.
    """
    recipients = settings.TALK_SUBMISSION_NOTIFICATION_EMAIL
    if not recipients:
        # Nothing to do
        return
    tlk = kw['talk']
    subject = '[new paper] "%s %s" - %s' % (sender.user.first_name, sender.user.last_name, tlk.title)
    body = '''
Title: %(title)s
Duration: %(duration)s (includes Q&A)
Language: %(language)s
Type: %(type)s

Abstract: %(abstract)s

Tags: %(tags)s
''' % {
    'title': tlk.title,
    'duration': tlk.duration,
    'language': tlk.language,
    'abstract': getattr(tlk.getAbstract(), 'body', ''),
    'type': tlk.get_type_display(),
    'tags': [ x.name for x in tlk.tags.all() ],
    }
    from conference.utils import send_email
    send_email(
        recipient_list=recipients,
        subject=subject,
        message=body,
    )

new_paper_submission.connect(_new_paper_email)

# Issued when a charge has to calculate its price;
# price * qty
fare_price = Signal(providing_args=['calc'])

# Issued when a charge must create one or more tickets for a particular user.
# The `sender` is the instance of `Fare` while params is a dict with two keys.
#   user -> the user for whom the ticket has to be created
#   tickets -> a list in which to place the created tickets
#
# if no listeners change `params['tickets']`, the default implementation
# creates a single `Ticket` user.
fare_tickets = Signal(providing_args=['params'])

def on_talk_saved(sender, **kw):
    """
    Check that the profile of a speaker with a accepted talk is visible
    """
    if sender is Talk:
        o = kw['instance']
    elif sender is TalkSpeaker:
        o = kw['instance'].talk
    else:
        o = kw['instance'].talk
    if o and o.status == 'accepted':
        from conference import models
        profiles = models.AttendeeProfile.objects\
            .filter(user__in=models.TalkSpeaker.objects\
                .filter(talk=o)\
                .values('speaker__user'))\
            .exclude(visibility='p')
        for p in profiles:
            log.info('Set "%s"\'s profile to be visible because his talk "%s" has been accepted', '%s %s' % (p.user.first_name, p.user.last_name), o.title)
            p.visibility = 'p'
            p.save()

post_save.connect(on_talk_saved, sender=Talk)
post_save.connect(on_talk_saved, sender=TalkSpeaker)
# Also I draw the event because there is a custom acion in the admin that
# sets all the talks present in the schedule as accepted.
post_save.connect(on_talk_saved, sender=Event)
