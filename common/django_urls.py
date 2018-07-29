# -*- coding: UTF-8 -*-

# see: http://code.google.com/p/django-urls/
# see: http://code.djangoproject.com/wiki/ReplacingGetAbsoluteUrl

from django.conf import settings

try:
    from urllib.parse import urlparse, urlunparse
except ImportError:
    from urlparse import urlparse


class UrlMixin(object):  # pragma: no cover
    
    def get_url(self):
        if hasattr(self.get_url_path, 'dont_recurse'):
            raise NotImplemented
        try:
            path = self.get_url_path()
        except NotImplemented:
            raise
        # Should we look up a related site?
        #if getattr(self._meta, 'url_by_site'):
        prefix = getattr(settings, 'DEFAULT_URL_PREFIX', 'http://localhost')
        return prefix + path
    get_url.dont_recurse = True
    
    def get_url_path(self):
        if hasattr(self.get_url, 'dont_recurse'):
            raise NotImplemented
        try:
            url = self.get_url()
        except NotImplemented:
            raise
        bits = urlparse(url)
        return urlunparse(('', '') + bits[2:])
    get_url_path.dont_recurse = True
