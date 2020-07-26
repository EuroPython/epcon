import urllib.parse

from django.conf import settings


class UrlMixin(object):
    """
    DEPRECATED - DO NOT USE

    This is kept here for legacy reasons as migrations require it and in case
    we need to reffer to it. It was used in the Talk and Speaker models.
    """
    def get_url(self):
        if hasattr(self.get_url_path, 'dont_recurse'):
            raise NotImplementedError

        try:
            path = self.get_url_path()
        except NotImplementedError:
            raise

        # Should we look up a related site?
        # if getattr(self._meta, 'url_by_site'):
        prefix = getattr(settings, 'DEFAULT_URL_PREFIX', 'http://localhost')
        return prefix + path

    get_url.dont_recurse = True

    def get_url_path(self):
        if hasattr(self.get_url, 'dont_recurse'):
            raise NotImplementedError
        try:
            url = self.get_url()
        except NotImplementedError:
            raise

        bits = urllib.parse.urlparse(url)
        return urllib.parse.urlunparse(('', '') + bits[2:])

    get_url_path.dont_recurse = True
