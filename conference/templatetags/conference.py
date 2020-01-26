import mimetypes
import re

from django import template
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


# XXX - remove
@register.simple_tag(takes_context=True)
def get_talk_speakers(context, talk):
    c = _request_cache(context['request'], 'talk_speakers_%s' % talk.conference)
    if not c:
        c['items'] = models.TalkSpeaker.objects.speakers_by_talks(talk.conference)
    return c['items'].get(talk.id, [])


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
    except:
        return None


@register.simple_tag()
def profile_data(uid):
    return dataaccess.profile_data(uid)


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
            return [ attrib_(x, attrib) for x in ob ]
