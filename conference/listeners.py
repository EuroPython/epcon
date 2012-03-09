# -*- coding: UTF-8 -*-
from conference.utils import send_email
from conference.models import Talk

from django.dispatch import Signal
from django.db.models.signals import post_save

import logging

log = logging.getLogger('conference')

# emesso quando uno speaker (il sender) presenta un nuovo paper
new_paper_submission = Signal(providing_args=['talk'])

def _new_paper_email(sender, **kw):
    """
    Invia una mail agli organizzatori con i dettagli sul paper presentato.
    """
    tlk = kw['talk']
    subject = '[new paper] "%s %s" - %s' % (sender.user.first_name, sender.user.last_name, tlk.title)
    body = '''
Title: %(title)s
Duration: %(duration)s
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
    send_email(
        subject=subject,
        message=body,
    )

new_paper_submission.connect(_new_paper_email)

# emesso quando una tariffa deve calcolare il proprio prezzo; il sender è
# un'istanza di Fare mentre calc è un dict contenente due chiavi:
#   total -> inizializzato con fare.price * qty può essere modificato da un
#   listener
#   params -> parametri inseriti dall'utente (come la quantità)
fare_price = Signal(providing_args=['calc'])

# emesso quando una tariffa deve creare uno o più biglietti per un determinato
# utente. Il `sender` è l'istanza di `Fare` mentre `params` è un dict con due
# chiavi:
#   user -> l'utente per il quale deve essere creato il biglietto
#   tickets -> una lista in cui inserire i biglietti creati
#
# Se nessun listener modifica `params['tickets']` l'implementazione di default
# crea un solo `Ticket` per l'utente.
fare_tickets = Signal(providing_args=['params'])

def on_talk_saved(sender, **kw):
    """
    Si assicura che il profilo di uno speaker con talk 'accepted' sia visibile.
    """
    o = kw['instance']
    if o.status == 'accepted':
        from conference import models
        profiles = models.AttendeeProfile.objects\
            .filter(user__in=models.TalkSpeaker.objects.filter(talk=o).values('speaker__user'))
        for p in profiles:
            if p.visibility != 'p':
                log.info('Set "%s"\'s profile to be visible because his talk "%s" has been accepted', '%s %s' % (p.user.first_name, p.user.last_name), o.title)
                p.visibility = 'p'
                p.save()

post_save.connect(on_talk_saved, sender=Talk)
