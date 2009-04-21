# -*- coding: UTF-8 -*-
URL = 'http://booking.bettersoftware.it/conference/getinfo.py/empty_attendees'

SUBJECT = "[Better Software 2009] dati mancanti per il tuo badge di ingresso"

BODY = u"""Ciao,

questa mail è inviata automaticamente dal nostro gestionale a tutti gli
utenti che hanno acquistato un biglietto per Better Software 2009.

Ci risulta che uno o più biglietti associati al tuo account "%(username)s" non
sono stati ancora compilati con i dati personali del partecipante.

E' molto importante che compili il biglietto inserendo il nome e cognome
della persona che parteciperà e i giorni di presenza in conferenza. 

Puoi farlo entrando direttamente sul gestionale della conferenza usando
il tuo username "%(username)s":
http://www.bettersoftware.it/2009/booking/

e andando nella sezione acquisti cliccate sul biglietto ancora da
compilare.

Grazie!
Better Software team
"""

SERVER = 'trinity.trilan'
REPLYTO = 'info@bettersoftware.it'
FROM = 'francesco@bettersoftware.it'

