# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import mimetypes
import os
import os.path
import re
from django import template
from django.conf import settings

from p3 import models
from pages import models as PagesModels
from conference import models as ConferenceModels

mimetypes.init()

register = template.Library()

@register.inclusion_tag('p3/box_pycon_italia.html')
def box_pycon_italia():
    return {}

@register.inclusion_tag('p3/box_newsletter.html')
def box_newsletter():
    return {}

@register.inclusion_tag('p3/box_download.html')
def box_download(fname, label=None):
    if '..' in fname:
        raise template.TemplateSyntaxError("file path cannot contains ..")
    if fname.startswith('/'):
        raise template.TemplateSyntaxError("file path cannot starts with /")
    if label is None:
        label = os.path.basename(fname)
    try:
        fpath = os.path.join(settings.P3_STUFF_DIR, fname)
        print fpath
        stat = os.stat(fpath)
    except (AttributeError, OSError), e:
        print e
        fsize = ftype = None
    else:
        fsize = stat.st_size
        ftype = mimetypes.guess_type(fpath)[0]
        
    return {
        'url': settings.MEDIA_URL + 'p3/stuff/' + fname,
        'label': label,
        'fsize': fsize,
        'ftype': ftype,
    }

@register.inclusion_tag('p3/box_didyouknow.html')
def box_didyouknow():
    try:
        d = ConferenceModels.DidYouKnow.objects.order_by('?')[0]
    except IndexError:
        d = None
    return { 'd': d }
