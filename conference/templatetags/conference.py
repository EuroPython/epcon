import mimetypes
import os
import os.path
import re
from collections import defaultdict

from django import template
from django.conf import settings as dsettings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from common.jsonify import json_dumps
from conference import dataaccess
from conference import models

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


class TNode(template.Node):
    def _set_var(self, v):
        if not v:
            return v
        if v.startswith('"') and v.endswith('"'):
            return v[1:-1]
        else:
            return template.Variable(v)

    def _get_var(self, v, context):
        try:
            return v.resolve(context)
        except AttributeError:
            return v


@register.filter
def image_resized(value, size='resized'):
    if isinstance(value, str):
        url = value
        if not url.startswith(dsettings.DEFAULT_URL_PREFIX + dsettings.MEDIA_URL):
            return url
    else:
        try:
            url = value.url
        except AttributeError:
            return ''
    try:
        dirname, basename = os.path.split(url)
    except:
        return ''
    else:
        return dirname + '/%s/%s' % (size, os.path.splitext(basename)[0] + '.jpg')


@register.tag
def conference_multilingual_attribute(parser, token):
    """
    {% conference_multilingual_attribute object attribute [as var] [fallback lang|any] %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        instance, attribute = contents[1:3]
    except ValueError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    contents = contents[3:]
    if contents and contents[0] == 'as':
        var_name = contents[1]
        contents = contents[2:]
    else:
        var_name = None

    if contents and contents[0] == 'fallback':
        fallback = contents[1]
        contents = contents[2:]
    else:
        fallback = None

    if contents:
        raise template.TemplateSyntaxError("%r had too many arguments" % tag_name)

    class AttributeNode(TNode):
        def __init__(self, instance, attribute, var_name, fallback):
            self.var_name = var_name
            self.instance = self._set_var(instance)
            self.attribute = self._set_var(attribute)
            self.fallback = self._set_var(fallback)

        def render(self, context):
            instance = self._get_var(self.instance, context)
            attribute = self._get_var(self.attribute, context)
            fallback = self._get_var(self.fallback, context)
            try:
                query = getattr(instance, attribute)
            except AttributeError:
                return ''

            contents = dict((c.language, c) for c in query.all() if (c.body and c.content == attribute))
            try:
                value = contents[context['LANGUAGE_CODE']]
            except KeyError:
                try:
                    value = contents[context['LANGUAGE_CODE'].split('-')[0]]
                except KeyError:
                    if fallback is None or not contents:
                        value = None
                    elif fallback != 'any':
                        value = contents.get(fallback)
                    else:
                        dlang = dsettings.LANGUAGES[0][0]
                        dlang_single = dsettings.LANGUAGES[0][0].split('-')[0]
                        if dlang in contents:
                            value = contents[dlang]
                        elif dlang_single in contents:
                            value = contents[dlang_single]
                        else:
                            value = list(contents.values())[0]
            if self.var_name:
                context[self.var_name] = value
                return ''
            else:
                return value.body if value else ''

    return AttributeNode(instance, attribute, var_name, fallback)



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


# TODO: Remove
@register.filter
def markdown2(text, arg=''):
    from markdown2 import markdown
    extensions = [e for e in arg.split(",") if e]
    if len(extensions) > 0 and extensions[0] == "nosafe":
        extensions = extensions[1:]
        safe_mode = None
    else:
        safe_mode = "escape"

    return mark_safe(markdown(text, safe_mode=safe_mode, extras=extensions))


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
def json_(val):
    return mark_safe(json_dumps(val))


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


@register.simple_tag()
def conference_js_data(tags=None):
    """
    Javascript Initialization for the conference app. The use of 'conference_js_data'
    injects on the 'conference' window, a variable with some information about the conference.
    """
    if tags is None:
        tags = dataaccess.tags()

    cts = dict(ContentType.objects.all().values_list('id', 'model'))
    items = {}
    for t, objects in tags.items():
        key = t.name
        if key not in items:
            items[key] = {}
        for ctid, oid in objects:
            k = cts[ctid]
            if k not in items[key]:
                items[key][k] = 0
            items[key][k] += 1

    tdata = defaultdict(list)
    for x in tags:
        tdata[x.category].append(x.name)

    data = {
        'tags': dict(tdata),
        'taggeditems': items,
    }

    return mark_safe('window.conference = {};'.format(json_dumps(data)))
