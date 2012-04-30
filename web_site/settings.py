# -*- coding: UTF-8 -*-
# Django settings for pycon_site project.

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('dvd', 'dvd@gnx.it'),
    ('c8e', 'carlo.miron@gmail.com'),
)

MANAGERS = ADMINS
SERVER_EMAIL = 'wtf@python.it'
DEFAULT_FROM_EMAIL = 'info@pycon.it'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Rome'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'

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
# calendars according to the current locale
USE_L10N = True


# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'
SECURE_MEDIA_URL = '/p3/secure_media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of callables that know how to import templates from various sources.
#TEMPLATE_LOADERS = (
#    'django.template.loaders.filesystem.Loader',
#    'django.template.loaders.app_directories.Loader',
#)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'pages.context_processors.media',
    'conference.context_processors.current_url',
    'conference.context_processors.stuff',
    'django.contrib.messages.context_processors.messages',
    'p3.context_processors.countdown',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    'assopy.middleware.DebugInfo',
    'pingback.middleware.PingbackMiddleware',
)

ROOT_URLCONF = 'web_site.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'assopy',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.markup',
    'django.contrib.redirects',
    'django.contrib.staticfiles',
    'tagging',
    'taggit',
    'authority',
    'pages',
    'mptt',
    #'haystack',
    'conference',
    'p3',
    'microblog',
    'django.contrib.comments',
    'hcomments',
    'django_xmlrpc',
    'pingback',
    'rosetta',
    'south',
    'templatesadmin',
    'email_template',
    'filebrowser',
    'develer_tools',
)

AUTHENTICATION_BACKENDS = (
    'assopy.auth_backends.IdBackend',
    'assopy.auth_backends.EmailBackend',
    'assopy.auth_backends.JanRainBackend',
    'django.contrib.auth.backends.ModelBackend',
)

FILEBROWSER_URL_FILEBROWSER_MEDIA = '/static/filebrowser/'

PAGE_USE_SITE_ID = False
DEFAULT_PAGE_TEMPLATE = 'p3/content.html'
PAGE_TEMPLATES = (
    ('p3/index.html', 'homepage'),
    ('p3/index-simple.html', 'homepage (semplificata)'),
    ('p3/content.html', 'content page'),
    ('p3/content-1col.html', 'content page (una colonna)'),
    ('p3/content-assopy.html', 'assopy page (una colonna)'),
    ('p3/p5_homepage.html', '(p5) homepage'),
)
PAGE_UNIQUE_SLUG_REQUIRED = False
PAGE_TAGGING = True
PAGE_DEFAULT_LANGUAGE = 'it'
PAGE_LANGUAGES = LANGUAGES
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
MICROBLOG_EMAIL_INTEGRATION = False

MICROBLOG_TWITTER_USERNAME = 'europython'
MICROBLOG_TWITTER_POST_URL_MANGLER = 'microblog.utils.bitly_url'
MICROBLOG_TWITTER_INTEGRATION = False

def MICROBLOG_POST_FILTER(posts, user):
    if user and user.is_staff:
        return posts
    else:
        return filter(lambda x: x.is_published(), posts)

SESSION_COOKIE_NAME = 'ep_sessionid'

GNR_CONFERENCE = {
    'src': 'http://assopy.pycon.it/conference/',
    'size': (780, 480),
}

CONFERENCE_OLARK_KEY = '1751-12112149-10-1389'
CONFERENCE_GOOGLE_MAPS = {
    # chiave info@pycon.it per http://localhost
    # 'key': 'ABQIAAAAaqki7uO3Z2gFXuaDbZ-9BBT2yXp_ZAY8_ufC3CFXhHIE1NvwkxSCRpOQNQwH5i15toJmp6eLWzSKPg',
    # chiave info@pycon.it per http://pycon.it
    'key': 'ABQIAAAAaqki7uO3Z2gFXuaDbZ-9BBT8rJViP5Kd0PVV0lwN5R_47a678xQFxoY_vNcqiT-2xRPjGe6Ua3A5oQ',
    'country': 'it',
}

CONFERENCE_CONFERENCE = 'ep2012'
CONFERENCE_SEND_EMAIL_TO = [ 'pycon-organization@googlegroups.com', ]
CONFERENCE_VOTING_DISALLOWED = 'https://ep2012.europython.eu/voting-disallowed'

CONFERENCE_FORMS = {
    'PaperSubmission': 'p3.forms.P3SubmissionForm',
    'AdditionalPaperSubmission': 'p3.forms.P3SubmissionAdditionalForm',
    'Profile': 'p3.forms.P3ProfileForm',
    'EventBooking': 'p3.forms.P3EventBookingForm',
}

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
    from p3.utils import conference_stats
    from conference.models import Schedule
    if not isinstance(schedule, Schedule):
        output = {}
        for s in Schedule.objects.filter(conference=schedule):
            output[s.id] = CONFERENCE_SCHEDULE_ATTENDEES(s, forecast)
        return output
    code = 'nostaff_days_' + schedule.date.strftime('%Y-%m-%d')
    stats = conference_stats(schedule.conference, code)
    if not stats:
        return 0
    if forecast:
        return stats[0]['additional_info']
    else:
        return stats[0]['count']

def CONFERENCE_ADMIN_STATS(conference, stat=None):
    from p3.utils import conference_stats
    return conference_stats(conference, stat)

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
    'credit-note': ['dvd@gnx.it'],
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
    'period': (date(2012, 6, 29), date(2012, 7, 10)),
    'default': (date(2012, 7, 2), date(2012, 7, 6)),
}
P3_USER_MESSAGE_FOOTER = '''

This message was sent from a participant at the conference EuroPython.
Your email address is not disclosed to anyone, to stop receiving messages
from other users you can change your privacy settings from this page:
https://ep2012.europython.eu/accounts/profile/
'''

TEMPLATESADMIN_EDITHOOKS = (
    'templatesadmin.edithooks.gitcommit.GitCommitHook',
)

HAYSTACK_SITECONF = 'web_site.search_sites'
HAYSTACK_SEARCH_ENGINE = 'whoosh'

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

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'with_level': {
            'format': '%(name)-12s %(levelname)-8s %(message)s',
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        '': {
            'level': 'DEBUG',
        },
        'suds': {
            'level': 'INFO',
        },
        'south': {
            'level': 'INFO',
        },
        'assopy.genro': {
            'level': 'INFO',
        },
    }
}

from settings_locale import *

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
