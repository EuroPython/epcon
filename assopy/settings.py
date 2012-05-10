# -*- coding: UTF-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

if hasattr(settings, 'ASSOPY_JANRAIN'):
    JANRAIN = {
        'domain': settings.ASSOPY_JANRAIN['domain'],
        'app_id': settings.ASSOPY_JANRAIN['app_id'],
        'secret': settings.ASSOPY_JANRAIN['secret'],
    }
else:
    JANRAIN = None

try:
    BACKEND = settings.ASSOPY_BACKEND
except AttributeError:
    raise ImproperlyConfigured('Assopy Backend not set')

CHECK_DB_SCHEMA = getattr(settings, 'ASSOPY_CHECK_DB_SCHEMA', True)

SEARCH_MISSING_USERS_ON_BACKEND = getattr(settings, 'ASSOPY_SEARCH_MISSING_USERS_ON_BACKEND', False)

TICKET_PAGE = getattr(settings, 'ASSOPY_TICKET_PAGE', None)

SEND_EMAIL_TO = getattr(settings, 'ASSOPY_SEND_EMAIL_TO', None)

REFUND_EMAIL_ADDRESS = getattr(settings, 'ASSOPY_REFUND_EMAIL_ADDRESS', {
    'approve': SEND_EMAIL_TO,
    'execute': {None: SEND_EMAIL_TO},
    'credit-note': SEND_EMAIL_TO,
})

VIES_WSDL_URL = getattr(settings, 'ASSOPY_VIES_WSDL_URL', 'http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl')

OTC_CODE_HANDLERS = {
    'v': 'assopy.views.OTCHandler_V',
    'j': 'assopy.views.OTCHandler_J',
}
OTC_CODE_HANDLERS.update(getattr(settings, 'ASSOPY_OTC_CODE_HANDLERS', {}))
