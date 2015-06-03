# -*- coding: utf-8 -*-
""" Print out a JSON of accepted talks with the abstracts

"""
from django.core.management.base import BaseCommand, CommandError
from django.core import urlresolvers
from conference import models
from conference import utils

from collections import defaultdict, OrderedDict
from optparse import make_option
import operator
import simplejson as json

### Globals

TYPE_NAMES = (
    ('keynote', 'Keynotes'),
    ('s', 'Talks'),
    ('t', 'Trainings'),
    ('p', 'Poster sessions'),
    ('h', 'Help desks'),
    ('europython', 'EuroPython sessions'),
    ('i', 'Other sessions'),
    )

def _check_talk_types(type_names):
    d = dict(type_names)
    for code, entry in models.TALK_TYPE:
        assert code in d, 'Talk type code %r is missing' % code
_check_talk_types(TYPE_NAMES)

### Helpers


def speaker_listing(talk):
    return u', '.join(
        u'{} {}'.format(speaker.user.first_name, speaker.user.last_name) for speaker in talk.get_all_speakers())


def talk_title(talk):

    # Remove whitespace
    title = talk.title.strip()

    # Remove double spaces
    title = title.replace("  ", " ")

    # Remove quotes
    if title[0] == '"' and title[-1] == '"':
        title = title[1:-1]

    return title

###

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        # make_option('--option',
        #     action='store',
        #     dest='option_attr',
        #     default=0,
        #     type='int',
        #     help='Help text',
        # ),
    )
    def handle(self, *args, **options):
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference not specified')

        talks = (models.Talk.objects
                 .filter(conference=conference,
                         status='accepted'))

        # Group by types
        talk_types = {}
        for talk in talks:
            if 'EPS' in talk.title or 'EuroPython 20' in talk.title:
                type = 'europython'
            elif talk.title.lower().startswith('keynote'):
                type = 'keynote'
            else:
                type = talk.type
            if type in talk_types:
                talk_types[type].append(talk)
            else:
                talk_types[type] = [talk]

        sessions = OrderedDict()
        # Print list of submissions
        for type, type_name in TYPE_NAMES:
            bag = talk_types.get(type, [])
            if not bag:
                continue

            sessions[type_name] = OrderedDict()

            # Sort by talk title using title case
            bag.sort(key=lambda talk: talk_title(talk).title())
            for talk in bag:
                sessions[type_name][talk.id] = {
                'talk_id':   talk.id,
                'duration':  talk.duration,
                'title':     talk_title(talk).encode('utf-8'),
                'speakers':  speaker_listing(talk).encode('utf-8'),
                'abstracts': talk.abstracts}

        print(json.dumps(sessions))
