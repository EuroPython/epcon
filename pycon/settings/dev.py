from __future__ import absolute_import

from pycon.settings.core import *  # NOQA

DEFAULT_URL_PREFIX = 'http://localhost:8000'
DEBUG = True

PAYPAL_TEST = True

INSTALLED_APPS = INSTALLED_APPS + (   # NOQA
    'django_extensions',
    'django_pdb',
    'test_without_migrations',
    # 'devserver',
)

MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (  # NOQA
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

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
