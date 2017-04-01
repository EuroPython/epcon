# -*- coding: UTF-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

if not settings.LANGUAGES:
    raise ImproperlyConfigured('You need at least one entry in the LANGUAGES settings')   

# Default language for the blog posts
MICROBLOG_DEFAULT_LANGUAGE = getattr(
    settings, 'MICROBLOG_DEFAULT_LANGUAGE', 
    settings.LANGUAGES[0][0])

# url style for microblog posts. date or category
MICROBLOG_URL_STYLE = getattr(settings, 'MICROBLOG_URL_STYLE', 'date')
assert MICROBLOG_URL_STYLE in ('date', 'category'), "MICROBLOG_URL_STYLE should be either date or category"

MICROBLOG_LANGUAGE_FALLBACK_ON_POST_LIST = getattr(settings, 'MICROBLOG_LANGUAGE_FALLBACK_ON_POST_LIST', False)

# enable/disable the server side support for the trackback protocol
MICROBLOG_TRACKBACK_SERVER = getattr(settings, 'MICROBLOG_TRACKBACK_SERVER', True)

# enable/disable the server side support for the pingback protocol
MICROBLOG_PINGBACK_SERVER = getattr(settings, 'MICROBLOG_PINGBACK_SERVER', True)
if MICROBLOG_PINGBACK_SERVER:
    # il middleware è necessario per registrae il server xmlrpc
    if 'pingback.middleware.PingbackMiddleware' not in settings.MIDDLEWARE_CLASSES:
        raise ImproperlyConfigured('pingback middleware "pingback.middleware.PingbackMiddleware" not set')

MICROBLOG_TITLE = getattr(settings, 'MICROBLOG_TITLE', 'My Microblog')
MICROBLOG_DESCRIPTION = getattr(settings, 'MICROBLOG_DESCRIPTION', '')
MICROBLOG_AUTHOR_NAME = getattr(settings, 'MICROBLOG_AUTHOR_NAME', None)
MICROBLOG_AUTHOR_EMAIL = getattr(settings, 'MICROBLOG_AUTHOR_EMAIL', None)
MICROBLOG_AUTHOR_LINK = getattr(settings, 'MICROBLOG_AUTHOR_LINK', None)

# configure the moderation system:
# None - moderation disabled
# light - auto moderate comments after 30 days and sends email 
# akismet - light + akismet validation
# always - always moderate
MICROBLOG_MODERATION_TYPE = getattr(settings, 'MICROBLOG_MODERATION_TYPE', 'light')
MICROBLOG_AKISMET_KEY = getattr(settings, 'MICROBLOG_AKISMET_KEY', None)
if MICROBLOG_MODERATION_TYPE == 'akismet' and not MICROBLOG_AKISMET_KEY:
    raise ImproperlyConfigured('please set your akismet key')
elif MICROBLOG_AKISMET_KEY:
    try:
        import akismet
    except ImportError:
        raise ImproperlyConfigured('In order to use the akismet service you need the akismet module')

if hasattr(settings, 'MICROBLOG_ENABLE_MODERATION'):
    print 'warning, MICROBLOG_ENABLE_MODERATION is deprecated, use MICROBLOG_MODERATION_TYPE instead'
    if settings.MICROBLOG_ENABLE_MODERATION:
        if settings.MICROBLOG_AKISMET_KEY:
            MICROBLOG_MODERATION_TYPE = 'akismet'
        else:
            MICROBLOG_MODERATION_TYPE = 'light'
    else:
        MICROBLOG_MODERATION_TYPE = None

# Enable forwarding of blog posts via email
MICROBLOG_EMAIL_INTEGRATION = getattr(settings, 'MICROBLOG_EMAIL_INTEGRATION', False)

MICROBLOG_EMAIL_RECIPIENTS = getattr(settings, 'MICROBLOG_EMAIL_RECIPIENTS', [])
MICROBLOG_EMAIL_LANGUAGES = getattr(settings, 'MICROBLOG_EMAIL_LANGUAGES', None)
MICROBLOG_EMAIL_BODY_TEMPLATE = getattr(settings, 'MICROBLOG_EMAIL_BODY_TEMPLATE', '{% if content.summary %}{{ content.summary|safe }}\n{% endif %}{{ content.body|safe }}')
MICROBLOG_EMAIL_SUBJECT_TEMPLATE = getattr(settings, 'MICROBLOG_EMAIL_SUBJECT_TEMPLATE', '{{ content.headline|safe }}')
# Microblog twitter integration configuration

# Enable Twitter integration
MICROBLOG_TWITTER_INTEGRATION = getattr(settings, 'MICROBLOG_TWITTER_INTEGRATION', False)
# ... True to dump the tweet on stdout
MICROBLOG_TWITTER_DEBUG = getattr(settings, 'MICROBLOG_TWITTER_DEBUG', False)
# ... tweet only post in this language
MICROBLOG_TWITTER_LANGUAGES = getattr(settings, 'MICROBLOG_TWITTER_LANGUAGES', None)
# ... username/password of the twitter account
MICROBLOG_TWITTER_USERNAME = getattr(settings, 'MICROBLOG_TWITTER_USERNAME', None)
MICROBLOG_TWITTER_PASSWORD = getattr(settings, 'MICROBLOG_TWITTER_PASSWORD', None)
# ... django template to render the tweet
MICROBLOG_TWITTER_MESSAGE_TEMPLATE = getattr(settings, 'MICROBLOG_TWITTER_MESSAGE_TEMPLATE', '{{ headline }} ( {{ url }} )')
# ... callable to obtain the url of a post 
MICROBLOG_TWITTER_POST_URL_MANGLER = getattr(settings, 'MICROBLOG_TWITTER_POST_URL_MANGLER', lambda p: p.get_url())

# In order to use bitly as url shortening service set your credentials and use
# 'microblog.utils.bitly_url' as MICROBLOG_TWITTER_POST_URL_MANGLER
MICROBLOG_BITLY_LOGIN = getattr(settings, 'MICROBLOG_BITLY_LOGIN', None)
MICROBLOG_BITLY_APIKEY = getattr(settings, 'MICROBLOG_BITLY_APIKEY', None)

# Enable the pagination for posts in the post list pages
MICROBLOG_POST_LIST_PAGINATION = getattr(settings, 'MICROBLOG_POST_LIST_PAGINATION', False)

# Number of post in a single page
MICROBLOG_POST_PER_PAGE = getattr(settings, 'MICROBLOG_POST_PER_PAGE', 20)
if MICROBLOG_POST_LIST_PAGINATION and MICROBLOG_POST_PER_PAGE < 1:
    raise ImproperlyConfigured('MICROBLOG_POST_PER_PAGE must be greater than zero')

MICROBLOG_UPLOAD_TO = getattr(settings, 'MICROBLOG_UPLOAD_TO', 'microblog')

def MICROBLOG_POST_FILTER(posts, user):
    if user and user.is_authenticated():
        return posts
    else:
        return filter(lambda x: x.is_published(), posts)
MICROBLOG_POST_FILTER = getattr(settings, 'MICROBLOG_POST_FILTER', MICROBLOG_POST_FILTER)
