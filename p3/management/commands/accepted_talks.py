# -*- coding: utf-8 -*-
""" Print out a listing of accepted talks.

"""
from django.core.management.base import BaseCommand, CommandError
from conference import models

from ...utils import (talk_title,
                      profile_url)

### Globals

# These must match the talk .type or .admin_type
TYPE_NAMES = (
    ('k', 'Keynotes', ''),
    ('t', 'Talks', ''),
    ('r', 'Training sessions', ''),
    ('p', 'Poster sessions', ''),
    ('i', 'Interactive sessions', ''),
    ('n', 'Panels', ''),
    ('h', 'Help desks', 'Help desks provide slots for attendees to discuss their problems one-on-one with experts from the projects.'),
    ('m', 'EuroPython sessions', 'The EuroPython sessions are intended for anyone interested in helping with the EuroPython organization in the coming years.'),
    )

def _check_talk_types(type_names):
    d = set(x[0] for x in type_names)
    for code, entry in models.TALK_TYPE:
        assert code[0] in d, 'Talk type code %r is missing' % code[0]
_check_talk_types(TYPE_NAMES)

### Helpers

def speaker_listing(talk):
    return u', '.join(
        u'<a href="%s"><i>%s %s</i></a>' % (
            profile_url(speaker.user),
            speaker.user.first_name,
            speaker.user.last_name)
        for speaker in talk.get_all_speakers())


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
    
    args = '<conference>'
    
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
            talk_type = talk.type[:1]
            admin_type = talk.admin_type[:1]
            if (admin_type == 'm' or
               'EPS' in talk.title or
               'EuroPython 20' in talk.title):
                type = 'm'
            elif (admin_type == 'k' or
                  talk.title.lower().startswith('keynote')):
                #print ('found keynote: %r' % talk)
                type = 'k'
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

        # Print list of submissions
        print ('<h2>Accepted submissions</h2>')
        for type, type_name, description in TYPE_NAMES:
            bag = talk_types.get(type, [])
            if not bag:
                continue
            # Sort by talk title using title case
            bag.sort(key=lambda talk: talk_title(talk).title())
            print ('')
            print ('<h3>%s</h3>' % type_name)
            if description:
                print ('<p>%s</p>' % description)
            print ('<ul>')
            for talk in bag:
                print ((u'<li><a href="%s">%s</a> by %s</li>' % (
                    talk.get_absolute_url(),
                    talk_title(talk),
                    speaker_listing(talk))
                    ).encode('utf-8'))
            print ('</ul>')
