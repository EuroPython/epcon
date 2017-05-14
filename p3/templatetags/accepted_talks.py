from __future__ import unicode_literals
from django import template

from conference import models

from ..utils import profile_url, talk_title

register = template.Library()

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
    ('m', 'EuroPython sessions', (
        'The EuroPython sessions are intended for anyone interested '
        'in helping with the EuroPython organization in the coming years.'
    )),
)


def _check_talk_types(type_names):
    d = set(x[0] for x in type_names)
    for code, entry in models.TALK_TYPE:
        assert code[0] in d, 'Talk type code %r is missing' % code[0]


def speaker_listing(talk):
    return [{
        'url': profile_url(speaker.user),
        'fullname': '{} {}'.format(speaker.user.first_name, speaker.user.last_name),
    } for speaker in talk.get_all_speakers()]


@register.assignment_tag
def get_accepted_talks(conference, filter_types=None):
    _check_talk_types(TYPE_NAMES)

    talks = models.Talk.objects.filter(
        conference=conference, status='accepted')

    # Group by types
    talk_types = {}
    for talk in talks:
        talk_type = talk.type[:1]
        admin_type = talk.admin_type[:1]
        if (admin_type == 'm' or 'EPS' in talk.title or
                'EuroPython 20' in talk.title):
            type = 'm'
        elif (admin_type == 'k' or talk.title.lower().startswith('keynote')):
            type = 'k'
        elif admin_type in ('x', 'o', 'c', 'l', 'r', 's', 'e'):
            # Don't list these placeholders or plenary sessions
            # used in the schedule
            continue
        else:
            type = talk_type
        if type in talk_types:
            talk_types[type].append(talk)
        else:
            talk_types[type] = [talk]

    output = {}

    types = TYPE_NAMES

    if filter_types is not None:
        filter_types = [x.strip() for x in filter_types.split(',')]

        types = [t for t in TYPE_NAMES if t[0] in filter_types]

    for type, type_name, description in types:
        bag = talk_types.get(type, [])

        # Sort by talk title using title case
        bag.sort(key=lambda talk: talk_title(talk).title())

        output[type] = {
            'type': type_name,
            'talks': [{
                'title': talk_title(talk),
                'url': talk.get_absolute_url(),
                'speakers': speaker_listing(talk),
                'talk': talk,
            } for talk in bag]
        }

    return output
