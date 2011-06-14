# -*- coding: UTF-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

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

CFP_CLOSED = getattr(settings, 'CONFERENCE_CFP_CLOSED', None)

VOTING_CLOSED = getattr(settings, 'CONFERENCE_VOTING_CLOSED', None)

# callable per verificare se l'utente passato può partecipare alla votazione
VOTING_ALLOWED = getattr(settings, 'CONFERENCE_VOTING_ALLOWED', lambda user: True)

VOTING_DISALLOWED = getattr(settings, 'CONFERENCE_VOTING_DISALLOWED', None)

SEND_EMAIL_TO = getattr(settings, 'CONFERENCE_SEND_EMAIL_TO', None)

STUFF_DIR = getattr(settings, 'CONFERENCE_STUFF_DIR', settings.MEDIA_ROOT)

STUFF_URL = getattr(settings, 'CONFERENCE_STUFF_URL', settings.MEDIA_URL)

TALKS_RANKING_FILE = getattr(settings, 'CONFERENCE_TALKS_RANKING_FILE', None)

LATEST_TWEETS_FILE = getattr(settings, 'CONFERENCE_LATEST_TWEETS_FILE', None)

VIDEO_DOWNLOAD_FALLBACK = getattr(settings, 'CONFERENCE_VIDEO_DOWNLOAD_FALLBACK', True)

TICKET_BADGE_ENABLED = getattr(settings, 'CONFERENCE_TICKET_BADGE_ENABLED', False)

TICKET_BADGE_PREPARE_FUNCTION = getattr(settings, 'CONFERENCE_TICKET_BADGE_PREPARE_FUNCTION', lambda tickets: [])

import os.path
import conference

TICKED_BADGE_PROG = getattr(settings, 'CONFERENCE_TICKED_BADGE_PROG', os.path.join(os.path.dirname(conference.__file__), 'utils', 'ticket_badge.py'))

SCHEDULE_ATTENDEES = getattr(settings, 'CONFERENCE_SCHEDULE_ATTENDEES', lambda schedule, forecast=False: 0)

ADMIN_STATS = getattr(settings, 'CONFERENCE_ADMIN_STATS', lambda conference, stat=None: [])
