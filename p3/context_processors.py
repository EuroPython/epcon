# -*- coding: UTF-8 -*-
from datetime import date
from conference import assopy
from django.utils.translation import ugettext_lazy as _

def highlight(request):
    """
    Aggiunge il messaggio da mostrare in tutte le pagine
    """
    deadline = date(year = 2009, month = 5, day = 8)
    t = deadline - date.today()

    if t.days > 1:
        msg = _("Mancano *%(days)d giorni* all'inizio della conferenza.")
        msg = msg % {'days': t.days}
    elif t.days == 1:
        msg = _("La conferenza inizia *domani*!")
    elif t.days in (0, -1, -2):
        return _("La conferenza è in fase di svolgimento!")
    else:
        return { 'HIGHLIGHT': None }
        
    if msg:
        msg = msg.replace('*', '<strong>', 1).replace('*', '</strong>')
    else:
        msg = ''

    attendee = assopy.attendeeCount()
    if attendee > 0:
        m2 = _("Ci sono ancora *%(seat)d* posti disponibili")
        m2 = m2 % {'seat': 420 - attendee} 
        m2 = m2.replace('*', '<strong>', 1).replace('*', '</strong>')
        msg += ' ' + m2
    if msg:
        msg = '<a href="/pycon3/registrazione/">' + msg + '</a>'
    return { 'HIGHLIGHT': msg }
