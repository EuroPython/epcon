

import mimetypes
import os
import os.path
import re
import random
import sys
import urllib.request, urllib.parse, urllib.error
from collections import defaultdict
from datetime import datetime
from itertools import groupby

from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from conference import dataaccess as cdataaccess
from conference import models as ConferenceModels
from conference.settings import STUFF_DIR, STUFF_URL

from assopy import models as amodels
from p3 import dataaccess
from p3 import forms as p3forms
from p3 import models


mimetypes.init()

register = template.Library()

@register.inclusion_tag('p3/box_toc.html', takes_context=True)
def box_toc(context):
    return context

@register.inclusion_tag('p3/box_sponsor.html', takes_context=True)
def box_sponsor(context):
    return context

@register.inclusion_tag('p3/box_newsletter.html', takes_context=True)
def box_newsletter(context):
    return context


@register.inclusion_tag('p3/box_didyouknow.html', takes_context = True)
def box_didyouknow(context):
    try:
        d = ConferenceModels.DidYouKnow.objects.filter(visible = True).order_by('?')[0]
    except IndexError:
        d = None
    return {
        'd': d,
        'LANGUAGE_CODE': context.get('LANGUAGE_CODE'),
    }

@register.inclusion_tag('p3/box_talks_conference.html', takes_context = True)
def box_talks_conference(context, talks):
    """
    mostra i talk passati raggruppati per conferenza
    """
    conf = defaultdict(list)
    for t in talks:
        conf[t.conference].append(t)

    talks = []
    for c in reversed(sorted(conf.keys())):
        talks.append((c, conf[c]))

    return { 'talks': talks }

@register.simple_tag(takes_context=True)
def event_partner_program(context, event):
    fare_id = re.search(r'f(\d+)', event.track)
    if fare_id is None:
        return ''
    from conference.templatetags.conference import _request_cache
    c = _request_cache(context['request'], 'fares')
    if not c:
        for f in ConferenceModels.Fare.objects.all():
            c[str(f.id)] = f
    fare = c[fare_id.group(1)]
    return mark_safe('<a href="/partner-program/#%s">%s</a>' % (slugify(fare.name), event.custom,))

@register.filter
def schedule_to_be_splitted(s):
    tracks = ConferenceModels.Track.objects.by_schedule(s)
    s = []
    for t in tracks:
        if t.track.startswith('partner') or t.track.startswith('sprint'):
            s.append(t)
    return len(tracks) != len(s)

@register.simple_tag()
def p3_profile_data(uid):
    return dataaccess.profile_data(uid)

@register.simple_tag()
def p3_talk_data(tid):
    return dataaccess.talk_data(tid)

@register.simple_tag(takes_context=True)
def all_user_tickets(context, uid=None, conference=None,
                     status="complete", fare_type="conference"):
    if uid is None:
        uid = context['request'].user.id
    if conference is None:
        conference = settings.CONFERENCE_CONFERENCE
    tickets = dataaccess.all_user_tickets(uid, conference)
    if status == 'complete':
        tickets = [x for x in tickets if x[3]]
    elif status == 'incomplete':
        tickets = [x for x in tickets if not x[3]]
    if fare_type != "all":
        tickets = [x for x in tickets if x[1] == fare_type]

    return tickets

@register.simple_tag()
def p3_tags():
    return dataaccess.tags()

@register.simple_tag(takes_context=True)
def render_profile_box(context, profile, conference=None, user_message="auto"):
    if conference is None:
        conference = settings.CONFERENCE_CONFERENCE
    if isinstance(profile, int):
        profile = dataaccess.profile_data(profile)
    ctx = context.flatten()
    ctx.update({
        'profile': profile,
        'conference': conference,
        'user_message': user_message if user_message in ('auto', 'always', 'none') else 'auto',
    })
    return render_to_string('p3/fragments/render_profile_box.html', ctx)

@register.filter
def timetable_remove_first(timetable, tag):
    if not tag:
        return timetable
    start = None
    for time, events in timetable.iterOnTimes():
        stop = False
        for e in events:
            if tag not in e['tags']:
                stop = True
                break
        start = time.time()
        if stop:
            break

    return timetable.slice(start=start)
