from conference.models import Talk, Event, TalkSpeaker, AttendeeProfile, ConferenceManager, Conference

from django.dispatch import Signal
from django.db.models.signals import post_save

import logging

log = logging.getLogger('conference')


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
        profiles = AttendeeProfile.objects.filter(
            user__in=TalkSpeaker.objects.filter(talk=o).values('speaker__user')
        ).exclude(visibility='p')
        for p in profiles:
            log.info(
                'Set "%s"\'s profile to be visible because their talk "%s" has been accepted',
                '{} {}'.format(p.user.first_name, p.user.last_name), o.title
            )
            p.visibility = 'p'
            p.save()


post_save.connect(on_talk_saved, sender=Talk)
post_save.connect(on_talk_saved, sender=TalkSpeaker)
# Also I draw the event because there is a custom acion in the admin that
# sets all the talks present in the schedule as accepted.
post_save.connect(on_talk_saved, sender=Event)

post_save.connect(ConferenceManager.clear_cache, sender=Conference)
