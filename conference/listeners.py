# -*- coding: UTF-8 -*-
from conference.utils import send_email

from django.dispatch import Signal

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

Abstract: %(abstract)s

Tags: %(tags)s
''' % {
    'title': tlk.title,
    'duration': tlk.duration,
    'language': tlk.language,
    'abstract': tlk.getAbstract(),
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
