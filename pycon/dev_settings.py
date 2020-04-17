import os

from pycon.settings import *  # noqa

DEFAULT_URL_PREFIX = 'http://localhost:8888'
DEBUG = True

LOGGING['loggers']['django.request']['handlers'].append('console')  # noqa

# Turn off HTTPS
if 'HTTPS' in os.environ:
    del os.environ['HTTPS']
HTTPS = False

# Disable all the caching
DISABLE_CACHING = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# however for some tests we *do* want to test caches, hence we're going to use
# @override_settings(CACHES=settings.ENABLE_LOCMEM_CACHE)
ENABLE_LOCMEM_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

CACHES = DISABLE_CACHING

TEMPLATES[0]['OPTIONS']['debug'] = True  # noqa

INSTALLED_APPS = INSTALLED_APPS + (  # noqa
    'django_extensions',
    'django_pdb',
    # 'devserver',
)

MIDDLEWARE = MIDDLEWARE + (  # noqa
    'django_pdb.middleware.PdbMiddleware',
    # 'devserver.middleware.DevServerMiddleware',
)

DEVSERVER_MODULES = (
    'devserver.modules.sql.SQLRealTimeModule',
    'devserver.modules.sql.SQLSummaryModule',
    'devserver.modules.profile.ProfileSummaryModule',

    # Modules not enabled by default
    'devserver.modules.profile.LineProfilerModule',
)

DEVSERVER_AUTO_PROFILE = True

# Show emails on console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

GRAPH_MODELS = {
    'all_applications': True,
    'group_models': True,
}

# Test keys (for CI tests)
# Please set these via env vars!
#STRIPE_SECRET_KEY = ""
#STRIPE_PUBLISHABLE_KEY = ""
