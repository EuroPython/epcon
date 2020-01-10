
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

FORMS = {
    'EventBooking': 'conference.forms.EventBookingForm',
}
FORMS.update(getattr(settings, 'CONFERENCE_FORMS', {}))

import os
# FIXME: This part is hardcoded, why ?
#MAX_TICKETS =  os.environ.get("MAX_TICKETS")
# (artcz) Setting to 6 because that was/is the value in the javascript for the
# cart.
MAX_TICKETS = 6

VOTING_OPENED = getattr(settings, 'CONFERENCE_VOTING_OPENED', lambda conf, user: conf.voting())

# Callable to check whether the user passed may vote
VOTING_ALLOWED = getattr(settings, 'CONFERENCE_VOTING_ALLOWED', lambda user: True)

VOTING_DISALLOWED = getattr(settings, 'CONFERENCE_VOTING_DISALLOWED', None)

# List of emails to send notification to
SEND_EMAIL_TO = getattr(settings, 'CONFERENCE_SEND_EMAIL_TO', None)

STUFF_DIR = getattr(settings, 'CONFERENCE_STUFF_DIR', settings.MEDIA_ROOT)

STUFF_URL = getattr(settings, 'CONFERENCE_STUFF_URL', settings.MEDIA_URL)

TALKS_RANKING_FILE = getattr(settings, 'CONFERENCE_TALKS_RANKING_FILE', None)

VIDEO_DOWNLOAD_FALLBACK = getattr(settings, 'CONFERENCE_VIDEO_DOWNLOAD_FALLBACK', True)

DEFAULT_VOTING_TALK_TYPES = (
    ('all', 'All'),
    ('s', 'Talks'),
    ('t', 'Trainings'),
    ('p', 'Poster'),
)

TALK_TYPES_TO_BE_VOTED = getattr(settings, 'CONFERENCE_VOTING_TALK_TYPES',
                                 DEFAULT_VOTING_TALK_TYPES)


CONFERENCE_TICKETS = settings.CONFERENCE_TICKETS
# TICKET_BADGE_ENABLED enable or disable the ability to generate badge by admin
TICKET_BADGE_ENABLED = getattr(settings, 'CONFERENCE_TICKET_BADGE_ENABLED', False)

# The generation of the badges is a process in 3 steps:

# Step 1: The list, or the QuerySet, the tickets that we want, they are passed
# to the TICKET_BADGE_PREPARE_FUNCTION function; This must return a list
# where each eleemnt is a "group tickets". Tickets can be grouped in any way
# (usually for the conference, in the case that they are passed tickets belonging
# to more than one conference);
# It's a group of dict with 2 keys, 'plugin' and 'tickets'
#
# "tickets" is a list of tickets that will be encoded in JSON and passed as input
# to TICKET_BADGE_PROG; this list will be passed to the script specified via "plugin".
# "plugin is the absolute path to the python script with plugin configuration for use
# with the TICKED_BADGE_PROG program.
#
# Step 2: The TICKET_BADGE_PROG program will be invoked following the output of
# TICKET_BADGE_PREPARE_FUNCTION; the output of TICKET_BADGE_PROG is a tar file
# containing the TIFF pages with badges ready to go to press.
#
# Step 3: While running TICKET_BADGE_PROG runs the configuration plugin;
# this plugin must expose two functions: "tickets" and "Ticket".
# "Ticket" is invoked through the program input (generated by TICKET_BADGE_PREPARE_FUNCTION)
# and must return a dictionaary groups the tickets gone according to any criterion.
# The keys of dictionary are arbitrary, are only used in the generation of names
# of the tar file; on the other hand the values must be in turn of three keys dictionaries
# and containers, "image", "attendees", "max_width"
#
# "image" must be an instance of PIL.Image, "max_width" is the width maximum
# in pixels used to write text and "attendees" list of participants (one participant can be anything).
#
# "ticket" is called passing a copy of the image returned by "tickets" and the instance
# of a single participant, it must return the image of badge.

SCHEDULE_ATTENDEES = getattr(settings, 'CONFERENCE_SCHEDULE_ATTENDEES', lambda schedule, forecast=False: 0)

X_SENDFILE = getattr(settings, 'CONFERENCE_X_SENDFILE', None)

TALK_VIDEO_ACCESS = getattr(settings, 'CONFERENCE_TALK_VIDEO_ACCESS', lambda r, t: True)

TALK_SUBMISSION_LANGUAGES = getattr(
    settings,
    'CONFERENCE_TALK_SUBMISSION_LANGUAGES',
    settings.LANGUAGES) 

# Voting talk types (only the first letter of TALK_TYPE)
DEFAULT_VOTING_TALK_TYPES = (
    ('t', 'Talks'),
    ('r', 'Trainings'),
    #('p', 'Poster'),
    #('n', 'Panel'),
    #('h', 'Help desk'),
)

# List of emails to send talk submission email notifications to
TALK_SUBMISSION_NOTIFICATION_EMAIL = getattr(
    settings,
    'CONFERENCE_TALK_SUBMISSION_NOTIFICATION_EMAIL',
    None)

TALK_TYPES_TO_BE_VOTED = getattr(settings, 'CONFERENCE_VOTING_TALK_TYPES', DEFAULT_VOTING_TALK_TYPES)

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
