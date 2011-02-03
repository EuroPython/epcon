# -*- coding: UTF-8 -*-
from django.conf import settings

if hasattr(settings, 'ASSOPY_JANRAIN'):
    JANRAIN = {
        'domain': settings.ASSOPY_JANRAIN['domain'],
        'app_id': settings.ASSOPY_JANRAIN['app_id'],
        'secret': settings.ASSOPY_JANRAIN['secret'],
    }
else:
    JANRAIN = None

BACKEND = 'http://assopy.pycon.it/conference/externalcall'

SEARCH_MISSING_USERS_ON_BACKEND = getattr(settings, 'ASSOPY_SEARCH_MISSING_USERS_ON_BACKEND', False)
