import logging
import os.path

from django import http
from django.shortcuts import get_object_or_404

from conference import models as cmodels


log = logging.getLogger('p3.views')


def p3_profile_avatar(request, slug):
    p = get_object_or_404(cmodels.AttendeeProfile, slug=slug).p3_profile
    from urllib.request import urlopen
    try:
        response = urlopen(p.profile_image_url())
    except Exception:
        import p3
        from django.conf import settings
        path = os.path.join(os.path.dirname(p3.__file__), 'static', settings.P3_ANONYMOUS_AVATAR)
        with open(path, 'rb') as image_file:
            image = image_file.read()
        ct = 'image/jpg'
    else:
        headers = response.info()
        image = response.read()
        ct = headers.get('content-type')
    return http.HttpResponse(image, content_type=ct)
