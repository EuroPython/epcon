# Django settings for pycon_site project.

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('dvd', 'dvd@gnx.it'),
    ('c8e', 'carlo.miron@gmail.com'),
)

MANAGERS = ADMINS
SERVER_EMAIL = 'wtf@python.it'
DEFAULT_FROM_EMAIL = 'site@pycon.it'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db/p3.db',
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
PAGE_LANGUAGES = LANGUAGES

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

#ADMIN_MEDIA_ROOT = os.path.join(PROJECT_DIR, '../admin_media/')

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'kc-yf%25(%6e870u&z$)!rq@dm(b2giam-p$q$!vg#dv+j0!57'

# List of callables that know how to import templates from various sources.
#TEMPLATE_LOADERS = (
#    'django.template.loaders.filesystem.load_template_source',
#    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
#)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'pages.context_processors.media',
    'conference.context_processors.stuff',
    'p3.context_processors.highlight',
    'p3.context_processors.static',
    'django.contrib.messages.context_processors.messages',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'pycon_site.urls'

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
    'tagging',
    'taggit',
    'pages',
    'mptt',
    'conference',
    'p3',
    'microblog',
    'django.contrib.comments',
    'hcomments',
    'django_xmlrpc',
    'pingback',
    'rosetta',
    'south',
)

AUTHENTICATION_BACKENDS = (
    'assopy.auth_backends.EmailBackend',
    'assopy.auth_backends.JanRainBackend',
    'django.contrib.auth.backends.ModelBackend',
)
## used by the blog
#FEEDBURNER_BLOG_FEED = 'http://feeds.feedburner.com/pyconit'

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

PAGE_DEFAULT_LANGUAGE = 'it'

PAGE_UNIQUE_SLUG_REQUIRED = False
PAGE_TAGGING = True

MICROBLOG_LINK = 'http://www.europython.eu'
MICROBLOG_TITLE = 'Europython blog'
MICROBLOG_DESCRIPTION = 'latest news from europython'
MICROBLOG_DEFAULT_LANGUAGE = 'en'
MICROBLOG_POST_LIST_PAGINATION = True
MICROBLOG_POST_PER_PAGE = 10
MICROBLOG_MODERATION_TYPE = 'akismet'
MICROBLOG_AKISMET_KEY = '56c34997206c'

# se si vuole far servire a django i file statici
# popolare questo dizionario con coppie
# nome app -> static dir
STATIC_DIRS = {}

# directory dove memorizzare la roba dei vari pycon
STUFF_DIR = None

SESSION_COOKIE_NAME = 'p3_sessionid'

GNR_CONFERENCE = {
    'src': 'http://assopy.pycon.it/conference/',
    'size': (780, 480),
}

CONFERENCE_GOOGLE_MAPS = {
    # chiave info@pycon.it per http://localhost
    # 'key': 'ABQIAAAAaqki7uO3Z2gFXuaDbZ-9BBT2yXp_ZAY8_ufC3CFXhHIE1NvwkxSCRpOQNQwH5i15toJmp6eLWzSKPg',
    # chiave info@pycon.it per http://pycon.it
    'key': 'ABQIAAAAaqki7uO3Z2gFXuaDbZ-9BBT8rJViP5Kd0PVV0lwN5R_47a678xQFxoY_vNcqiT-2xRPjGe6Ua3A5oQ',
    'country': 'it',
}

CONFERENCE_CONFERENCE = 'ep2011'

DEFAULT_URL_PREFIX = 'http://ep2011.europython.eu'
PINGBACK_TARGET_DOMAIN = 'www.pycon.it'
COMMENTS_APP = 'hcomments'
P3_TWITTER_USER = 'europython'

ASSOPY_SEARCH_MISSING_USERS_ON_BACKEND = True

try:
    from settings_locale import *
except ImportError:
    pass
