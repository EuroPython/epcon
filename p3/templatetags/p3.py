import re
from collections import defaultdict

from django import template
from django.conf import settings
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from conference import models as ConferenceModels

from p3 import dataaccess

register = template.Library()


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
