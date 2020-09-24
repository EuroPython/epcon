import mimetypes
import re

from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from conference import dataaccess, models

mimetypes.init()

register = template.Library()


def _request_cache(request, key):
    """
    Returns (or create) a linked object dictionary usable past as cache with
    visibility equal to that of the request.
    """
    try:
        return request._conf_cache[key]
    except KeyError:
        request._conf_cache[key] = {}
    except AttributeError:
        request._conf_cache = {key: {}}
    return request._conf_cache[key]


# DO NOT REMOVE - Current conference object used in the CMS templates
@register.simple_tag()
def current_conference():
    return models.Conference.objects.current()


@register.filter
def full_name(u):
    return "%s %s" % (u.first_name, u.last_name)


@register.filter
def fare_blob(fare, field):
    try:
        blob = fare.blob
    except AttributeError:
        blob = fare['blob']

    match = re.search(r'%s\s*=\s*(.*)$' % field, blob, re.M + re.I)
    if match:
        return match.group(1).strip()
    return ''


@register.simple_tag
def tagged_items(tag):
    return dataaccess.tags().get(tag, {})


@register.simple_tag()
def talk_data(tid):
    return dataaccess.talk_data(tid)


@register.simple_tag()
def schedule_data(sid):
    return dataaccess.schedule_data(sid)


@register.filter
def content_type(id):
    return ContentType.objects.get(id=id)


@register.filter
def field_label(value, fieldpath):
    mname, fname = fieldpath.split('.')
    model = getattr(models, mname)
    field = model._meta.get_field(fname)
    for k, v in field.choices:
        if k == value:
            return v
    return None


@register.simple_tag()
def admin_urlname_fromct(ct, action, id=None):
    r = 'admin:%s_%s_%s' % (ct.app_label, ct.model, action)
    if id is None:
        args = ()
    else:
        args = (str(id),)
    try:
        return reverse(r, args=args)
    except Exception:
        return None


@register.simple_tag()
def profile_data(uid):
    return dataaccess.profile_data(uid)


@register.simple_tag()
def sponsor_data():
    return models.Sponsor.objects.filter(
        sponsorincome__conference=settings.CONFERENCE_CONFERENCE
    ).order_by('-sponsorincome__income')


@register.filter
def attrib_(ob, attrib):
    try:
        return ob[attrib]
    except (KeyError, IndexError):
        return None
    except TypeError:
        try:
            iter(ob)
        except TypeError:
            return getattr(ob, attrib, None)
        else:
            return [attrib_(x, attrib) for x in ob]
