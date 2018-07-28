""" Session related tags

    Note: It's better to use tag names without underscores, since those need
    to be escaped in MarkItUp CMS plugins.

"""
from __future__ import unicode_literals
from django import template
from conference import models

from ..utils import profile_url, talk_title

register = template.Library()

### Constants

# These must match the talk .type or .admin_type
TYPE_NAMES = (
    ('k', 'Keynotes', ''),
    ('t', 'Talks', ''),
    ('r', 'Training sessions', ''),
    ('p', 'Poster sessions', ''),
    ('i', 'Interactive sessions', ''),
    ('n', 'Panels', ''),
    ('h', 'Help desks', (
        'Help desks provide slots for attendees to discuss '
        'their problems one-on-one with experts from the projects.'
    )),
    ('e', 'EuroPython sessions', (
        'The EuroPython sessions are intended for anyone interested '
        'in helping with the EuroPython organization in the coming years.'
    )),
    ('c', 'Community sessions', (
        'The community sessions are intended for Python communities such as '
        'the Python Software Foundation (PSF) to use for members meetings.'
    )),
)

def _check_talk_types(type_names):
    d = set(x[0] for x in type_names)
    for code, entry in models.TALK_TYPE:
        assert code[0] in d, 'Talk type code %r is missing' % code[0]
_check_talk_types(TYPE_NAMES)

### Helpers

def speaker_listing(talk):
    return [{
        'url': profile_url(speaker.user),
        'fullname': '{} {}'.format(speaker.user.first_name,
                                   speaker.user.last_name),
    } for speaker in talk.get_all_speakers()]

def speaker_name(speaker):

    name = u'%s %s' % (
        speaker.user.first_name,
        speaker.user.last_name)

    # Remove whitespace
    return name.strip()

def speaker_list_key(entry):

    speaker = entry[1]
    name = u'%s %s' % (
        speaker.user.first_name,
        speaker.user.last_name)

    # Remove whitespace and use title case
    return name.strip().title()

###

EXAMPLE_ACCEPTEDSESSIONS = """
{% load sessions %}
{% acceptedsessions "ep2018" filter_types="t,r,p,i,h,m" as sessiondata %}

{% for category in sessiondata %}
<h3>{{ category.name }}</h3>
{% if category.description %}
<p>{{ category.description }}</p>
{% endif %}
<ul>
{% for session in category.sessions %}
<li><a href="{{ session.url }}">{{ session.title }}</a> by 
{% for speaker in session.speakers %}
<a href="{{ speaker.url }}">{{ speaker.fullname }}</a>{% if not forloop.last %}, {% endif %}
{% endfor %}
</li>
{% endfor %}
</ul>
{% if not category.sessions %}
<ul><li>No sessions have been selected yet.</li></ul>
{% endif %}
{% endfor %}
"""

@register.assignment_tag
def acceptedsessions(conference, filter_types=None, filter_community=None):

    talks = models.Talk.objects.filter(
        conference=conference, status='accepted')
    if filter_community:
        talks = talks.filter(
            p3_talk__sub_community=filter_community.strip())

    # Group by types
    talk_types = {}
    for talk in talks:
        talk_type = talk.type[:1]
        admin_type = talk.admin_type[:1]
        if (admin_type == 'm' or 
            'EPS' in talk.title or
            'EuroPython 20' in talk.title):
            # EPS sessions
            type = 'e'
        elif (admin_type == 'k' or 
              talk.title.lower().startswith('keynote')):
            # Keynotes
            type = 'k'
        elif (admin_type == 'p'):
            # Community sessions
            type = 'c'
        elif admin_type in ('x', 'o', 'c', 'l', 'r', 's', 'e'):
            # Don't list these placeholders or plenary sessions
            # used in the schedule
            continue
        elif 'reserved for' in talk.title.lower():
            # Don't list reserved talk slots
            continue
        else:
            type = talk_type
        if type in talk_types:
            talk_types[type].append(talk)
        else:
            talk_types[type] = [talk]

    if filter_types is not None:
        filter_types = [x.strip() for x in filter_types.split(',')]
        types = [t 
                 for t in TYPE_NAMES 
                 if t[0] in filter_types]
    else:
        types = TYPE_NAMES

    output = []
    for type, type_name, description in types:
        bag = talk_types.get(type, [])

        # Sort by talk title using title case
        bag.sort(key=lambda talk: talk_title(talk).title())

        output.append({
            'type': type,
            'name': type_name,
            'description': description,
            'sessions': [{
                'title': talk_title(talk),
                'url': talk.get_absolute_url(),
                'speakers': speaker_listing(talk),
                'session': talk,
            } for talk in bag]
        })
    return output

EXAMPLE_SPEAKERS = """
{% load sessions %}
{% speakers "ep2018" as speakerdata %}

{% for name, group in speakerdata.groups.items %}
<h3>{{ name }} ...</h3>
<ul>
{% for speaker in group %}
<li><a href="{{ speaker.url }}">{{ speaker.fullname }}</a></li>
{% endfor %}
</ul>
{% endfor %}

<p>{{ speakerdata.count }} speakers in total.</p>
"""

@register.assignment_tag
def speakers(conference, filter_types=None):

    talks = models.Talk.objects.filter(
        conference=conference, status='accepted')

    # Find all speakers
    speaker_dict = {}
    for talk in talks:
        for speaker in talk.get_all_speakers():
            name = speaker_name(speaker)
            if not name:
                continue
            if name.lower() in ('to be announced', 'tobey announced'):
                # Skip place holder names
                continue
            speaker_dict[speaker_name(speaker)] = speaker

    # Prepare list
    speaker_list = speaker_dict.items()
    speaker_list.sort(key=speaker_list_key)

    data = {
        'listing': speaker_list,
        'count': len(speaker_list),
    }

    # Print list of speakers
    groups = {}
    group = ''
    for entry in speaker_list:
        name, speaker = entry
        sort_name = speaker_list_key(entry)
        if not group or group != sort_name[0]:
            group = sort_name[0]
            group_data = []
            groups[group] = group_data
        group_data.append({
            'speaker': speaker,
            'url': profile_url(speaker.user),
            'fullname': name,
        })
    data['groups'] = groups
    data['groups_list'] = sorted(groups.items())
    return data
