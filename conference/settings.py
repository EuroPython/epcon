# -*- coding: UTF-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

CONFERENCE_STUFF_URL = getattr(settings, 'CONFERENCE_STUFF_URL', '%sstuff/' % settings.MEDIA_URL)
CONFERENCE_STUFF_DIR = getattr(settings, 'CONFERENCE_STUFF_DIR', settings.MEDIA_ROOT)
CONFERENCE_GOOGLE_MAPS = getattr(settings, 'CONFERENCE_GOOGLE_MAPS', None)
