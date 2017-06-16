from pycon.settings import *

DEFAULT_URL_PREFIX='http://localhost:8000'
DEBUG=True

PAYPAL_TEST = True

TEMPLATES[0]['OPTIONS']['debug'] = True

INSTALLED_APPS = INSTALLED_APPS + ('django_extensions',)