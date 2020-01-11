
from django.conf import settings

try:
    BACKEND = settings.ASSOPY_BACKEND
except AttributeError:
    BACKEND = None

SEARCH_MISSING_USERS_ON_BACKEND = getattr(settings, 'ASSOPY_SEARCH_MISSING_USERS_ON_BACKEND', False)

SEND_EMAIL_TO = getattr(settings, 'ASSOPY_SEND_EMAIL_TO', None)

WKHTMLTOPDF_PATH = '/usr/bin/wkhtmltopdf'
