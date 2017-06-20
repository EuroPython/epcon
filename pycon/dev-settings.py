from pycon.settings import *

DEFAULT_URL_PREFIX='http://localhost:8000'
DEBUG=True

PAYPAL_TEST = True

TEMPLATES[0]['OPTIONS']['debug'] = True

INSTALLED_APPS = INSTALLED_APPS + (
    'django_extensions',
    'django_pdb',
    'test_without_migrations',
)

#TEST_WITHOUT_MIGRATIONS_COMMAND = 'django_nose.management.commands.test.Command'

MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (
    'django_pdb.middleware.PdbMiddleware',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/p3.db',
    }
}
