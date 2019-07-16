from pycon.settings import *  # noqa

# DEFAULT_URL_PREFIX='http://localhost:8000'
# DEBUG=True

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

TEMPLATES[0]['OPTIONS']['debug'] = True  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/p3.db',
    }
}
