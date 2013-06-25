# -*- coding: UTF-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _

try:
    CONFERENCE = settings.CONFERENCE_CONFERENCE
except AttributeError:
    raise ImproperlyConfigured('Current conference not set (CONFERENCE_CONFERENCE)')

TEMPLATE_FOR_AJAX_REQUEST = getattr(settings, 'CONFERENCE_TEMPLATE_FOR_AJAX_REQUEST', True)

GOOGLE_MAPS = getattr(settings, 'CONFERENCE_GOOGLE_MAPS', None)

MIMETYPE_NAME_CONVERSION_DICT = getattr(settings, 'CONFERENCE_MIMETYPE_NAME_CONVERSION_DICT', {
        'application/zip': 'ZIP Archive',
        'application/pdf': 'PDF Document',
        'application/vnd.ms-powerpoint': 'PowerPoint',
        'application/vnd.oasis.opendocument.presentation': 'ODP Document',
    }
)

FORMS = {
    'PaperSubmission': 'conference.forms.SubmissionForm',
    'AdditionalPaperSubmission': 'conference.forms.TalkForm',
    'Profile': 'conference.forms.ProfileForm',
    'EventBooking': 'conference.forms.EventBookingForm',
}
FORMS.update(getattr(settings, 'CONFERENCE_FORMS', {}))

# url a cui rimandare un utente che prova ad accedere alla paper submission
# quando il cfp è chiuso. Se None viene ritornato un 404
CFP_CLOSED = getattr(settings, 'CONFERENCE_CFP_CLOSED', None)

VOTING_CLOSED = getattr(settings, 'CONFERENCE_VOTING_CLOSED', None)

VOTING_OPENED = getattr(settings, 'CONFERENCE_VOTING_OPENED', lambda conf, user: conf.voting())

# callable per verificare se l'utente passato può partecipare alla votazione
VOTING_ALLOWED = getattr(settings, 'CONFERENCE_VOTING_ALLOWED', lambda user: True)

VOTING_DISALLOWED = getattr(settings, 'CONFERENCE_VOTING_DISALLOWED', None)

SEND_EMAIL_TO = getattr(settings, 'CONFERENCE_SEND_EMAIL_TO', None)

STUFF_DIR = getattr(settings, 'CONFERENCE_STUFF_DIR', settings.MEDIA_ROOT)

STUFF_URL = getattr(settings, 'CONFERENCE_STUFF_URL', settings.MEDIA_URL)

TALKS_RANKING_FILE = getattr(settings, 'CONFERENCE_TALKS_RANKING_FILE', None)

LATEST_TWEETS_FILE = getattr(settings, 'CONFERENCE_LATEST_TWEETS_FILE', None)

VIDEO_DOWNLOAD_FALLBACK = getattr(settings, 'CONFERENCE_VIDEO_DOWNLOAD_FALLBACK', True)

def _CONFERENCE_TICKETS(conf, ticket_type=None, fare_code=None):
    from conference import models
    tickets = models.Ticket.objects\
        .filter(fare__conference=conf)
    if ticket_type:
        tickets = tickets.filter(fare__ticket_type=ticket_type)
    if fare_code:
        if fare_code.endswith('%'):
            tickets = tickets.filter(fare__code__startswith=fare_code[:-1])
        else:
            tickets = tickets.filter(fare__code=fare_code)
    return tickets

CONFERENCE_TICKETS = getattr(settings, 'CONFERENCE_TICKETS', _CONFERENCE_TICKETS)
# TICKET_BADGE_ENABLED abilita o meno la possibilità di generare badge tramite
# admin
TICKET_BADGE_ENABLED = getattr(settings, 'CONFERENCE_TICKET_BADGE_ENABLED', False)

# La generazione dei badge è un processo articolato in 3 fasi:
#
# Fase 1: L'elenco, o il QuerySet, dei biglietti di cui vogliamo i badge viene
# passato alla funzione TICKET_BADGE_PREPARE_FUNCTION; questa deve ritornare
# una lista dove ogni elemento è un "gruppo di biglietti". I biglietti possono
# essere raggruppati in qualsiasi modo (di solito per conferenza, nel caso che
# vengano passati biglietti appartenenti a più di una conferenza); un gruppo è
# un dict con due chiavi: "plugin", "tickets".
#
# "tickets" è una lista di biglietti che verrà codificata in json e passata
# come input a TICKED_BADGE_PROG; tale lista verrà passata allo script
# specificato tramite "plugin".
# "plugin" è il percorso assoluto allo script python con il plugin di
# configurazione da usare con il programma TICKED_BADGE_PROG.
#
# Fase 2: Il programma TICKED_BADGE_PROG viene invocato seguendo l'output di
# TICKET_BADGE_PREPARE_FUNCTION; l'output di TICKED_BADGE_PROG è un file tar
# contenente i TIFF delle pagine con i badge pronte per andare in stampa.
#
# Fase 3: Durante l'esecuzione di TICKED_BADGE_PROG viene eseguito il plugin di
# configurazione; questo plugin deve esporre due funzioni: "tickets" e
# "ticket". "tickets" viene invocata passando l'input del programma (generato
# da TICKET_BADGE_PREPARE_FUNCTION) e deve ritornare un dizionario che
# raggruppi i biglietti passati secondo un qualsiasi criterio. Le chiavi del
# dizionario sono arbitrarie, vengono utilizzate solo nella generazione dei
# nomi dei file tar; i valori d'altro canto devono essere a loro volta dei
# dizionari e contenenre tre chiavi: "image", "attendees", "max_width".
#
# "image" deve essere un'istanza di PIL.Image, "max_width" è la larghezza
# massima in pixel utilizzabile per scrivere del testo e "attendees" un elenco
# di partecipanti (un partecipante può essere qualsiasi cosa).
#
# "ticket" viene chiamata passando una copia dell'immagine ritornata da
# "tickets" e l'istanza di un singolo partecipante, deve ritornare l'Image del
# badge.
import os.path
import conference
TICKED_BADGE_PROG = getattr(settings, 'CONFERENCE_TICKED_BADGE_PROG',
    os.path.join(os.path.dirname(conference.__file__), 'utils', 'ticket_badge.py'))
TICKET_BADGE_PROG_ARGS = getattr(settings, 'CONFERENCE_TICKET_BADGE_PROG_ARGS', ['-n', '6'])
TICKET_BADGE_PROG_ARGS_ADMIN = getattr(settings, 'CONFERENCE_TICKET_BADGE_PROG_ARGS', ['-e', '0', '-p', 'A4', '-n', '2'])
TICKET_BADGE_PREPARE_FUNCTION = getattr(settings, 'CONFERENCE_TICKET_BADGE_PREPARE_FUNCTION', lambda tickets: [])

SCHEDULE_ATTENDEES = getattr(settings, 'CONFERENCE_SCHEDULE_ATTENDEES', lambda schedule, forecast=False: 0)

ADMIN_ATTENDEE_STATS = getattr(settings, 'CONFERENCE_ADMIN_ATTENDEE_STATS', ())

X_SENDFILE = getattr(settings, 'CONFERENCE_X_SENDFILE', None)

TALK_VIDEO_ACCESS = getattr(settings, 'CONFERENCE_TALK_VIDEO_ACCESS', lambda r, t: True)

TALK_DURATION = getattr(
    settings,
    'CONFERENCE_TALK_DURATION',
    (
        (5,   _('5 minutes')),
        (10,  _('10 minutes')),
        (15,  _('15 minutes')),
        (25,  _('25 minutes')),
        (30,  _('30 minutes')),
        (40,  _('40 minutes')),
        (45,  _('45 minutes')),
        (55,  _('55 minutes')),
        (60,  _('60 minutes')),
        (75,  _('75 minutes')),
        (90,  _('90 minutes')),
        (120, _('120 minutes')),
        (240, _('240 minutes')),
        (480, _('480 minutes')),
    )
)

# absolute path of a file used to log the email sent from the admin (tickets
# stats section); the log file is also used to show a list of "last recently
# sent email" in the admin page.
ADMIN_TICKETS_STATS_EMAIL_LOG = getattr(settings, 'CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOG', None)

ADMIN_TICKETS_STATS_EMAIL_LOAD_LIBRARY = getattr(settings, 'CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOAD_LIBRARY', ['conference'])

def _VIDEO_COVER_EVENTS(conference):
    from conference import dataaccess
    return [ x['id'] for x in dataaccess.events(conf=conference) ]

VIDEO_COVER_EVENTS = getattr(settings, 'CONFERENCE_VIDEO_COVER_EVENTS', _VIDEO_COVER_EVENTS)

def _VIDEO_COVER_IMAGE(conference, eid, type='front', thumb=False):
    return None

VIDEO_COVER_IMAGE = getattr(settings, 'CONFERENCE_VIDEO_COVER_IMAGE', _VIDEO_COVER_IMAGE)

_OEMBED_PROVIDERS = (
    ('https://www.youtube.com/oembed',
        ('https://www.youtube.com/*', 'http://www.youtube.com/*')),
    ('http://vimeo.com/api/oembed.json',
        ('http://vimeo.com/*', 'https://vimeo.com/*',
        'http://vimeo.com/groups/*/videos/*', 'https://vimeo.com/groups/*/videos/*')),
    ('http://lab.viddler.com/services/oembed/',
        ('http://*.viddler.com/*',))
)
OEMBED_PROVIDERS = getattr(settings, 'CONFERENCE_OEMBED_PROVIDERS', _OEMBED_PROVIDERS)

import oembed
OEMBED_CONSUMER = oembed.OEmbedConsumer()
for p, urls in OEMBED_PROVIDERS:
    endpoint = oembed.OEmbedEndpoint(p, urls)
    OEMBED_CONSUMER.addEndpoint(endpoint)

OEMBED_URL_FIX = (
    (r'https?://vimeopro.com.*/(\d+)$', r'https://vimeo.com/\1'),
)
