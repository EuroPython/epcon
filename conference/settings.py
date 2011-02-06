# -*- coding: UTF-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

STUFF_URL = getattr(settings, 'CONFERENCE_STUFF_URL', '%sstuff/' % settings.MEDIA_URL)
STUFF_DIR = getattr(settings, 'CONFERENCE_STUFF_DIR', settings.MEDIA_ROOT)
GOOGLE_MAPS = getattr(settings, 'CONFERENCE_GOOGLE_MAPS', None)

MIMETYPE_NAME_CONVERSION_DICT = getattr(settings, 'CONFERENCE_MIMETYPE_NAME_CONVERSION_DICT', {
        'application/zip': 'ZIP Archive',
        'application/pdf': 'PDF Document',
        'application/vnd.ms-powerpoint': 'PowerPoint',
        'application/vnd.oasis.opendocument.presentation': 'ODP Document',
    }
)

VIDEO_DOWNLOAD_FALLBACK = getattr(settings, 'CONFERENCE_VIDEO_DOWNLOAD_FALLBACK', True)
try:
    CONFERENCE = settings.CONFERENCE_CONFERENCE
except AttributeError:
    raise ImproperlyConfigured('Current conference not set (CONFERENCE_CONFERENCE)')
