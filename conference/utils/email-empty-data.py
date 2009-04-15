#!/usr/bin/env python
# -*- coding: UTF-8 -*-

URL = 'http://assopy.pycon.it/conference/getinfo.py/empty_attendees'

SUBJECT = "[PyCon Tre] dati mancanti"

BODY = u"""Ciao,

questa e-mail è stata inviata automaticamente da AssoPy perché
hai acquistato almeno un biglietto per PyCon Tre.

Ci risulta che uno o più biglietti associati al tuo account "%(username)s"
sono stati regolarmente acquistati, ma non sono stati ancora compilati.

E' molto importante che compili il biglietto inserendo il nome e cognome 
della persona che parteciperà e i giorni di presenza. Puoi farlo 
entrando in AssoPy usando il tuo username "%(username)s":
http://www.pycon.it/pycon3/assopy/
"""

SIGN = "Grazie!\nGli organizzatori di PyCon"

SERVER = 'localhost'
REPLYTO = 'gestionale@pycon.it'
FROM = 'gestionale@pycon.it'

import urllib2
import textwrap
import simplejson
import smtplib
from datetime import datetime

data = simplejson.loads(urllib2.urlopen(URL).read())

now = datetime.now()

envelope = """\
From: %(from)s
To: %%s
Subject: %(subject)s
Reply-To: %(reply)s 
Date: %(date)s

%%s
""" % { 'from': FROM, 'subject': SUBJECT, 'reply': REPLYTO, 'date': now.strftime('%a, %d %b %Y %H:%M:%S %z') }

server = smtplib.SMTP(SERVER)
try:
    for email, username in data:
        body = BODY % { 'email': email, 'username': username }
        paragraphs = map(lambda p: textwrap.wrap(p, width=72), body.split('\n\n'))
        paragraphs = map(lambda l: '\n'.join(l), paragraphs)
        body = '\n\n'.join(paragraphs) + '\n\n' + SIGN

        envelope = envelope % (email, body.encode('utf-8'))
        server.sendemail(FROM, [ 'dvd@develer.com' ], envelope)
        break
finally:
    server.quit()
