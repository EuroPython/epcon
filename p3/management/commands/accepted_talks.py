# -*- coding: utf-8 -*-
""" Print out a listing of accepted talks.

"""
from django.core.management.base import BaseCommand, CommandError
from django.core import urlresolvers
from conference import models
from conference import utils

from collections import defaultdict
from optparse import make_option
import operator

### Globals

TYPE_NAMES = (
    ('keynote', 'Keynotes', ''),
    ('t', 'Talks', ''),
    ('r', 'Training sessions', ''),
    ('p', 'Poster sessions', ''),
    ('i', 'Interactive sessions', ''),
    ('n', 'Panels', ''),
    ('h', 'Help desks', 'Help desks provide slots for attendees to discuss their problems one-on-one with experts from the projects.'),
    ('europython', 'EuroPython sessions', 'The EuroPython sessions are intended for anyone interested in helping with the EuroPython organization in the coming years.'),
    )

def _check_talk_types(type_names):
    d = set(x[0] for x in type_names)
    for code, entry in models.TALK_TYPE:
        assert code[0] in d, 'Talk type code %r is missing' % code[0]
_check_talk_types(TYPE_NAMES)

### Helpers

def profile_url(user):

    return urlresolvers.reverse('conference-profile',
                                args=[user.attendeeprofile.slug])

def speaker_listing(talk):

    return u', '.join(
        u'<a href="%s"><i>%s %s</i></a>' % (
            profile_url(speaker.user),
            speaker.user.first_name,
            speaker.user.last_name)
        for speaker in talk.get_all_speakers())

def talk_title(talk):

    # Remove whitespace
    title = talk.title.strip()

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
                type = talk.type[0]
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
        
