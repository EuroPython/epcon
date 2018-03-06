from pycon.settings import *

DEFAULT_URL_PREFIX='http://localhost:8000'
DEBUG=True

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

TEMPLATES[0]['OPTIONS']['debug'] = True

INSTALLED_APPS = INSTALLED_APPS + (
    'django_extensions',
    'django_pdb',
    'test_without_migrations',
    # 'devserver',
)

#TEST_WITHOUT_MIGRATIONS_COMMAND = 'django_nose.management.commands.test.Command'

MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (
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

DATABASES = {
   'default': {
       'ENGINE': 'django.db.backends.sqlite3',
       'NAME': '/tmp/p3.db',
   }
}


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': os.environ.get("DATABASE_NAME", 'epcon'),
#         'USER': os.environ.get("POSTGRES_USER", 'epcon'),
#         'PASSWORD': os.environ.get("POSTGRES_PASSWORD", 'epcon'),
#         'HOST': os.environ.get("POSTGRES_HOST", '172.15.201.10'),
#         'PORT': os.environ.get("POSTGRES_PORT", '5432'),
#     },
# }

