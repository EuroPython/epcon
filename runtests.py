import sys
from django.conf import settings

settings.configure(
    DEBUG=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'assopy.sqlite'
        }
    },
    ROOT_URLCONF='assopy.urls',
    INSTALLED_APPS=(
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',

        'assopy',
        'assopy.stripe',

        'conference',
        'microblog',
        'taggit',

    ),
    STATIC_URL='/static/',

    GENRO_BACKEND=False,
    CONFERENCE_CONFERENCE="testconf",

    DEFAULT_PAGE_TEMPLATE = "cms/content.html",
    PAGE_LANGUAGES = (
        ('en-us', 'English'),
    ),

    MICROBLOG_PINGBACK_SERVER = False,

    STRIPE_SECRET_KEY="sk_test_N5pR3SD63rk0ODlSdD1ljnrW",
    STRIPE_PUBLISHABLE_KEY="pk_test_qRUg4tJTFJgUiLz0FxKnuOXO",
    STRIPE_COMPANY_NAME="Foo Bar",
    STRIPE_COMPANY_LOGO="foo-bar-logo-url",
)

from django.contrib import admin
admin.autodiscover()

from django.test.simple import DjangoTestSuiteRunner
test_runner = DjangoTestSuiteRunner(verbosity=1)
failures = test_runner.run_tests(['assopy', 'stripe'])
if failures:
    sys.exit(failures)
