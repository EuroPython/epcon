import os

from pycon.settings import *  # NOQA

DEFAULT_URL_PREFIX = 'http://localhost:37266'

DEBUG = True
LOGGING['loggers']['django.request']['handlers'].append('console')     # NOQA

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

PAYPAL_TEST = True

TEMPLATES[0]['OPTIONS']['debug'] = True  # NOQA

INSTALLED_APPS = INSTALLED_APPS + (  # NOQA
    'django_extensions',
    'django_pdb',
    # 'devserver',
)

MIDDLEWARE = MIDDLEWARE + (  # NOQA
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


STRIPE_SECRET_KEY = "sk_test_4eC39HqLyjWDarjtT1zdp7dc"
STRIPE_PUBLISHABLE_KEY = "pk_test_TYooMQauvdEDq54NiTphI7jx"
