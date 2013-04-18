# -*- coding: UTF-8 -*-
# Django settings for pycon project.
import os
import os.path
import sys

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('dvd', 'dvd@gnx.it'),
    ('c8e', 'carlo.miron@gmail.com'),
)

MANAGERS = ADMINS

PROJECT_DIR = os.environ.get('PROJECT_DIR', os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(PROJECT_DIR, 'data'))
OTHER_STUFF = os.environ.get('OTHER_STUFF', os.path.join(PROJECT_DIR, 'documents'))

sys.path.insert(0, os.path.join(PROJECT_DIR, 'deps'))

SITE_DATA_ROOT = DATA_DIR + '/site'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': SITE_DATA_ROOT + '/p3.db',
    }
}

SERVER_EMAIL = 'wtf@python.it'
DEFAULT_FROM_EMAIL = 'info@pycon.it'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Rome'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

ugettext = lambda s: s
LANGUAGES = (
#    ('it', ugettext('Italiano')),
    ('en', ugettext('English')),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = DATA_DIR + '/media_public'
SECURE_MEDIA_ROOT = DATA_DIR + '/media_private'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'
SECURE_MEDIA_URL = '/p3/secure_media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = DATA_DIR + '/static/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

from django.conf import global_settings
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'conference.context_processors.current_url',
    'conference.context_processors.stuff',
    'pages.context_processors.media',
    'p3.context_processors.countdown',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    'assopy.middleware.DebugInfo',
    'pingback.middleware.PingbackMiddleware',
)

ROOT_URLCONF = 'pycon.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'pycon.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'filebrowser',
    # attenzione l'ordine tra p3/assopy/admin è importante per risolvere
    # correttamente i templates
    'p3',
    'assopy',

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.markup',
    'django.contrib.redirects',
    'django.contrib.comments',

    'tagging',
    'taggit',
    'authority',
    'pages',
    'mptt',
    'conference',
    'microblog',
    'hcomments',
    'django_xmlrpc',
    'pingback',
    'rosetta',
    'south',
    'templatesadmin',
    'email_template',
    'develer_tools',
    'paypal.standard.ipn',

    'recaptcha_works',
    'django_crontab',
)

RECAPTCHA_OPTIONS = {
    'theme': 'clean',
    'lang': 'en',
    'tabindex': 0,
    #'custom_translations': {},
    #'custom_theme_widget': None
}

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level':'DEBUG',
            'class':'logging.StreamHandler',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

AUTHENTICATION_BACKENDS = (
    'assopy.auth_backends.IdBackend',
    'assopy.auth_backends.EmailBackend',
    'assopy.auth_backends.JanRainBackend',
    'django.contrib.auth.backends.ModelBackend',
)

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'
FILEBROWSER_URL_FILEBROWSER_MEDIA = '/static/filebrowser/'

PAGE_USE_SITE_ID = False
DEFAULT_PAGE_TEMPLATE = 'cms/content.html'
PAGE_TEMPLATES = (
    #('cms/index.html', 'homepage'),
    #('cms/index-simple.html', 'homepage (semplificata)'),
    ('cms/p5_homepage.html', 'Homepage'),
    ('cms/content.html', 'Content page'),
    ('cms/content-1col.html', 'Content page, single column'),
    ('cms/p5_home_splash.html', 'Homepage, coming soon'),
    #('cms/content-assopy.html', 'assopy page (una colonna)'),
)
PAGE_UNIQUE_SLUG_REQUIRED = False
PAGE_TAGGING = True
PAGE_LANGUAGES = (
    ('en-us', ugettext('English')),
)
PAGE_DEFAULT_LANGUAGE = 'en-us'
PAGE_LANGUAGE_MAPPING = lambda lang: 'en-us'


PAGE_REAL_TIME_SEARCH = False

PAGE_USE_STRICT_URL = True

MICROBLOG_LINK = 'http://www.europython.eu'
MICROBLOG_TITLE = 'Europython blog'
MICROBLOG_DESCRIPTION = 'latest news from europython'
MICROBLOG_DEFAULT_LANGUAGE = 'en'
MICROBLOG_POST_LIST_PAGINATION = True
MICROBLOG_POST_PER_PAGE = 10
MICROBLOG_MODERATION_TYPE = 'akismet'
MICROBLOG_AKISMET_KEY = '56c34997206c'
MICROBLOG_EMAIL_RECIPIENTS = ['europython@python.org', 'europython-improve@python.org', 'pycon-organization@googlegroups.com']
MICROBLOG_EMAIL_INTEGRATION = True

MICROBLOG_TWITTER_USERNAME = 'europython'
MICROBLOG_TWITTER_POST_URL_MANGLER = 'microblog.utils.bitly_url'
MICROBLOG_TWITTER_INTEGRATION = False

def MICROBLOG_POST_FILTER(posts, user):
    if user and user.is_staff:
        return posts
    else:
        return filter(lambda x: x.is_published(), posts)

SESSION_COOKIE_NAME = 'ep_sessionid'

CONFERENCE_OLARK_KEY = '1751-12112149-10-1389'
CONFERENCE_GOOGLE_MAPS = {
    # chiave info@pycon.it per http://localhost
    # 'key': 'ABQIAAAAaqki7uO3Z2gFXuaDbZ-9BBT2yXp_ZAY8_ufC3CFXhHIE1NvwkxSCRpOQNQwH5i15toJmp6eLWzSKPg',
    # chiave info@pycon.it per http://pycon.it
    'key': 'ABQIAAAAaqki7uO3Z2gFXuaDbZ-9BBT8rJViP5Kd0PVV0lwN5R_47a678xQFxoY_vNcqiT-2xRPjGe6Ua3A5oQ',
    'country': 'it',
}

CONFERENCE_CONFERENCE = 'ep2013'
CONFERENCE_SEND_EMAIL_TO = [ 'pycon-organization@googlegroups.com', ]
CONFERENCE_VOTING_DISALLOWED = 'https://ep2013.europython.eu/voting-disallowed'

CONFERENCE_FORMS = {
    'PaperSubmission': 'p3.forms.P3SubmissionForm',
    'AdditionalPaperSubmission': 'p3.forms.P3SubmissionAdditionalForm',
    'Profile': 'p3.forms.P3ProfileForm',
    'EventBooking': 'p3.forms.P3EventBookingForm',
}

CONFERENCE_LATEST_TWEETS_FILE = SITE_DATA_ROOT + '/latest_tweets.txt'
CONFERENCE_TALKS_RANKING_FILE = SITE_DATA_ROOT + '/rankings.txt'
CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOG = SITE_DATA_ROOT + '/admin_ticket_emails.txt'
CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOAD_LIBRARY = ['p3', 'conference']

def CONFERENCE_VOTING_OPENED(conf, user):
    # possono accedere alla pagina:
    #   chiunque durante il community voting
    #   i superuser
    #   gli speaker (della conferenza in corso)
    #   chi ha il gruppo special "pre_voting"
    if conf.voting() or user.is_superuser:
        return True
    from conference.models import TalkSpeaker, Speaker
    try:
        count = TalkSpeaker.objects.filter(talk__conference=CONFERENCE_CONFERENCE, speaker=user.speaker).count()
    except (AttributeError, Speaker.DoesNotExist):
        pass
    else:
        if count > 0:
            return True
    return user.groups.filter(name='pre_voting').exists()

def CONFERENCE_VOTING_ALLOWED(user):
    if not user.is_authenticated():
        return False
    if user.is_superuser:
        return True

    from conference.models import TalkSpeaker, Speaker
    try:
        count = TalkSpeaker.objects.filter(talk__conference=CONFERENCE_CONFERENCE, speaker=user.speaker).count()
    except Speaker.DoesNotExist:
        pass
    else:
        if count > 0:
            return True

    from p3 import models
    from django.db.models import Q
    # può votare chi ha almeno un biglietto confermato e che non ha
    # assegnato a qualcun'altro
    tickets = models.TicketConference.objects\
        .available(user, CONFERENCE_CONFERENCE)\
        .filter(Q(orderitem__order___complete=True)|Q(orderitem__order__method='admin'))\
        .filter(Q(p3_conference=None)|Q(p3_conference__assigned_to='')|Q(p3_conference__assigned_to=user.email))
    return tickets.count() > 0

def CONFERENCE_SCHEDULE_ATTENDEES(schedule, forecast):
    from p3.stats import presence_days
    from conference.models import Schedule
    if not isinstance(schedule, Schedule):
        output = {}
        for s in Schedule.objects.filter(conference=schedule):
            output[s.id] = CONFERENCE_SCHEDULE_ATTENDEES(s, forecast)
        return output
    d = schedule.date.strftime('%Y-%m-%d')
    s = presence_days(schedule.conference)
    for row in s['data']:
        if row['title'] == '%s (no staff)' % d:
            if forecast:
                return row['total_nc']
            else:
                return row['total']
    return 0

CONFERENCE_ADMIN_ATTENDEE_STATS = (
    'p3.stats.tickets_status',
    'p3.stats.hotel_tickets',
    'p3.stats.conference_speakers',
    'p3.stats.speaker_status',
    'p3.stats.presence_days',
    'p3.stats.shirt_sizes',
    'p3.stats.diet_types',
    'p3.stats.pp_tickets',
)

def CONFERENCE_VIDEO_COVER_EVENTS(conference):
    from conference import dataaccess
    from conference import models
    from datetime import timedelta
    conf = models.Conference.objects.get(code=conference)
    def valid(e):
        if e['tags'] & set(['special', 'break']):
            return False
        # gli ultimi due giorni si tengono gli sprint
        if e['time'].date() >= conf.conference_end - timedelta(days=1):
            return False
        # gli eventi serali non vengono ripresi
        if e['time'].hour >= 20:
            return False
        if len(e['tracks']) == 1 and (e['tracks'][0] in ('helpdesk1', 'helpdesk2')):
            return False
        return True
    return [ x['id'] for x in filter(valid, dataaccess.events(conf=conference)) ]

def CONFERENCE_VIDEO_COVER_IMAGE(eid, type='front', thumb=False):
    import re
    import os.path
    from PIL import Image, ImageDraw, ImageFont
    from conference import dataaccess

    event = dataaccess.event_data(eid)
    conference = event['conference']

    stuff = os.path.normpath(
        os.path.join(os.path.dirname(__file__), '..', 'documents', 'cover', conference))
    if not os.path.isdir(stuff):
        return None

    def wrap_text(font, text, width):
        words = re.split(' ', text)
        lines = []
        while words:
            word = words.pop(0).strip()
            if not word:
                continue
            if not lines:
                lines.append(word)
            else:
                line = lines[-1]
                w, h = font.getsize(line + ' ' + word)
                if w <= width:
                    lines[-1] += ' ' + word
                else:
                    lines.append(word)

        for ix, line in enumerate(lines):
            line = line.strip()
            while True:
                w, h = font.getsize(line)
                if w <= width:
                    break
                line = line[:-1]
            lines[ix] = line
        return lines

    if conference == 'ep2012':
        master = Image.open(os.path.join(stuff, 'cover-start-end.png')).convert('RGBA')

        if type == 'back':
            return master

        ftitle = ImageFont.truetype(
            os.path.join(stuff, 'League Gothic.otf'),
            36, encoding="unic")
        fauthor = ImageFont.truetype(
            os.path.join(stuff, 'Arial_Unicode.ttf'),
            21, encoding="unic")

        y = 175
        width = master.size[0] - 40
        d = ImageDraw.Draw(master)

        title = event['name']
        if event.get('custom'):
            # questo è un evento custom, se inizia con un anchor posso
            # estrane il riferimento
            m = re.match(r'<a href="(.*)">(.*)</a>', title)
            if m:
                title = m.group(2)
        lines = wrap_text(ftitle, title, width)
        for l in lines:
            d.text((20, y), l, font=ftitle, fill=(0x2f, 0x1c, 0x1c, 0xff))
            y += ftitle.getsize(l)[1] + 8

        if event.get('talk'):
            spks = [ x['name'] for x in event['talk']['speakers'] ]
            text = 'by ' + ','.join(spks)
            lines = wrap_text(fauthor, text, width)
            for l in lines:
                d.text((20, y), l, font=fauthor, fill=(0x3d, 0x7e, 0x8a, 0xff))
                y += fauthor.getsize(l)[1] + 8

        if thumb:
            master.thumbnail(thumb, Image.ANTIALIAS)
        return master
    else:
        return None

CONFERENCE_TICKET_BADGE_ENABLED = True
def CONFERENCE_TICKET_BADGE_PREPARE_FUNCTION(tickets):
    from p3.utils import conference_ticket_badge
    return conference_ticket_badge(tickets)

def CONFERENCE_TALK_VIDEO_ACCESS(request, talk):
    return True
    if talk.conference != CONFERENCE_CONFERENCE:
        return True
    u = request.user
    if u.is_anonymous():
        return False
    from conference.models import Ticket
    qs = Ticket.objects\
            .filter(id__in=[x.id for x in u.assopy_user.tickets()])\
            .filter(orderitem__order___complete=True, fare__ticket_type='conference')
    return qs.exists()

def ASSOPY_ORDERITEM_CAN_BE_REFUNDED(user, item):
    if not item.ticket:
        return False
    ticket = item.ticket
    if ticket.user != user:
        return False
    if ticket.fare.conference != CONFERENCE_CONFERENCE:
        return False
    if item.order.total() == 0:
        return False
    return item.order._complete

GENRO_BACKEND = False
ASSOPY_VIES_WSDL_URL = None
ASSOPY_BACKEND = 'http://assopy.pycon.it/conference/externalcall'
ASSOPY_SEARCH_MISSING_USERS_ON_BACKEND = True
ASSOPY_TICKET_PAGE = 'p3-tickets'
ASSOPY_SEND_EMAIL_TO = CONFERENCE_SEND_EMAIL_TO
ASSOPY_REFUND_EMAIL_ADDRESS = {
    'approve': ['info@pycon.it'],
    'execute': {
        None: ['dvd@gnx.it'],
        'bank': ['matteo@pycon.it'],
    },
    'credit-note': ['michele.bertoldi@gmail.com'],
}

ASSOPY_OTC_CODE_HANDLERS = {
    'e': 'p3.views.OTCHandler_E',
}

DEFAULT_URL_PREFIX = 'https://ep2012.europython.eu'
PINGBACK_TARGET_DOMAIN = 'ep2012.europython.eu'
COMMENTS_APP = 'hcomments'

from datetime import date
P3_TWITTER_USER = MICROBLOG_TWITTER_USERNAME
P3_HOTEL_RESERVATION = {
    'period': (date(2013, 6, 28), date(2013, 7, 9)),
    'default': (date(2013, 7, 2), date(2013, 7, 6)),
}
P3_USER_MESSAGE_FOOTER = '''

This message was sent from a participant at the conference EuroPython.
Your email address is not disclosed to anyone, to stop receiving messages
from other users you can change your privacy settings from this page:
https://ep2013.europython.eu/accounts/profile/
'''

TEMPLATESADMIN_EDITHOOKS = (
    'templatesadmin.edithooks.gitcommit.GitCommitHook',
)

HAYSTACK_SITECONF = 'web_site.search_sites'
HAYSTACK_SEARCH_ENGINE = 'whoosh'

def HCOMMENTS_RECAPTCHA(request):
    return not request.user.is_authenticated()

def HCOMMENTS_THREAD_OWNERS(o):
    from conference.models import Talk
    from microblog.models import Post
    if isinstance(o, Talk):
        return [ s.user for s in o.get_all_speakers() ]
    elif isinstance(o, Post):
        return [ o.author, ]
    return None

def HCOMMENTS_MODERATOR_REQUEST(request, comment):
    if request.user.is_superuser:
        return True
    else:
        owners = HCOMMENTS_THREAD_OWNERS(comment.content_object)
        if owners:
            return request.user in owners
    return False

P3_ANONYMOUS_AVATAR = 'p5/i/headshot-default.jpg'

P3_LIVE_TRACKS = {
    'track1': {
        'stream': {
            'external': 'https://www.youtube.com/watch?v=MpOzYZIdmqo',
            'internal': 'live/spaghetti',
        }
    },
    'track2': {
        'stream': {
            'external': 'https://www.youtube.com/watch?v=kT-Qgno3li8',
            'internal': 'live/lasagne',
        }
    },
    'track3': {
        'stream': {
            'external': 'https://www.youtube.com/watch?v=h7iJGt66gSE',
            'internal': 'live/ravioli',
        }
    },
    'track4': {
        'stream': {
            'external': 'https://www.youtube.com/watch?v=4jPvrK7bPBo',
            'internal': 'live/tagliatelle',
        }
    },
    'track-ita': {
        'stream': {
            'external': 'https://www.youtube.com/watch?v=-aTjP9_di4E',
            'internal': 'live/big_mac',
        }
    },
    'training1': {
        'stream': {
            'external': 'https://www.youtube.com/watch?v=iK8WSdZi3Hk',
            'internal': 'live/pizza_margherita',
        }
    },
    'training2': {
        'stream': {
            'external': 'https://www.youtube.com/watch?v=a8SrynF6ogc',
            'internal': 'live/pizza_napoli',
        }
    },
}

def P3_LIVE_EMBED(request, track=None, event=None):
    from django.core.cache import cache

    if not any((track, event)) or all((track, event)):
        raise ValueError('track or event, not both')

    if event:
        # ep2012, tutti i keynote vengono trasmessi dalla track "lasagne"
        if 'keynote' in event['tags'] or len(event['tracks'])>1:
            track = 'track2'
        else:
            track = event['tracks'][0]

    if request.META['REMOTE_ADDR'].startswith('2.228.78.'):
        try:
            url = 'live.ep/' + P3_LIVE_TRACKS[track]['stream']['internal']
        except KeyError:
            return None
        data = {
            'track': track,
            'stream': url.rsplit('/', 1)[1],
            'url': url.rsplit('/', 1)[0],
        }
        html = """
        <div>
            <div class="button" style="float: left; margin-right: 20px;">
                <h5><a href="rtsp://%(url)s">RTSP</a></h5>
                For almost all<br/>Linux, Windows, Android
            </div>
            <div class="button" style="float: left; margin-right: 20px;">
                <h5><a href="http://live.ep:1935/live/%(stream)s/playlist.m3u8">HLS&#xF8FF;</a></h5>
                Apple world (mainly)
            </div>
            <div class="button" style="float: left; margin-right: 20px;">
                <h5><a href="#" onclick="start_%(stream)s(); return false;">Flash</a></h5>
                Old good school
            </div>
            <div id="stream-%(track)s" style="clear: both();width:530px;height:298px;margin:0 auto;text-align:center"> </div>
            <script>
                function start_%(stream)s() {
                    $f("stream-%(track)s", "/static/p5/flowplayer/flowplayer-3.2.12.swf", {

                        clip: {
                            autoPlay: false,
                            url: 'mp4:%(stream)s',
                            scaling: 'fit',
                            // configure clip to use hddn as our provider, refering to our rtmp plugin
                            provider: 'hddn'
                        },

                        // streaming plugins are configured under the plugins node
                        plugins: {

                            // here is our rtmp plugin configuration
                            hddn: {
                                url: "/static/p5/flowplayer/flowplayer.rtmp-3.2.10.swf",

                                // netConnectionUrl defines where the streams are found
                                netConnectionUrl: 'rtmp://%(url)s'
                            }
                        }
                    });
                }
            </script>
        </div>
        """ % data
        return html
    else:
        data = cache.get('p3_live_embed_%s' % track)
        if data is not None:
            return data

        try:
            yurl = P3_LIVE_TRACKS[track]['stream']['external']
        except KeyError:
            return None

        import httplib2, json
        http = httplib2.Http()
        service = 'https://www.youtube.com/oembed'
        url = service + '?url=' + yurl + '&format=json&scheme=https'
        try:
            response, content = http.request(url)
            data = json.loads(content)
        except:
            return None
        cache.set('p3_live_embed_%s' % track, data['html'], 3600)
        return data['html']

# cronjob

def cron_latest_tweets():
    from conference.management.commands import latest_tweets
    cmd = latest_tweets.Command()
    cmd.handle('europython', count=5, output=CONFERENCE_LATEST_TWEETS_FILE)

def cron_cleanup():
    from django.core.management.commands import cleanup
    cmd = cleanup.Command()
    cmd.handle()

CRONTAB_COMMAND_PREFIX = 'DATA_DIR=%s OTHER_STUFF=%s' % (DATA_DIR, OTHER_STUFF)
CRONJOBS = [
    ('*/10 * * * *', 'pycon.settings.cron_latest_tweets'),
    ('@weekly', 'pycon.settings.cron_cleanup')
]

from settings_locale import *

if DEBUG:
    LOGGING['loggers']['django.request']['handlers'].append('console')
# i file sotto SECURE_MEDIA_ROOT devono essere serviti da django, questo if
# serve ad evitare che vengano messi in una subdir di MEDIA_ROOT che
# normalmente è servita da un webserver esterno.
import os.path
check = os.path.commonprefix((MEDIA_ROOT, SECURE_MEDIA_ROOT))
if check.startswith(MEDIA_ROOT):
    if not DEBUG:
        raise RuntimeError('SECURE_MEDIA_ROOT cannot be a subdir of MEDIA_ROOT')
    else:
        print 'WARN, SECURE_MEDIA_ROOT is a subdir of MEDIA_ROOT'

from django.core.files import storage
SECURE_STORAGE = storage.FileSystemStorage(location=SECURE_MEDIA_ROOT, base_url=SECURE_MEDIA_URL)

if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError('SECRET_KEY not set')
    else:
        print 'WARN, SECRET_KEY not set'
