# -*- coding: utf-8 -*-
""" Print accepted talks not scheduled and not accepted talks which have been scheduled.

"""
from   django.core.management.base import BaseCommand, CommandError
from   django.core  import urlresolvers
from   conference   import models
from   conference   import utils

from   collections  import defaultdict
from   optparse     import make_option
import operator
import simplejson   as json

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
def talk_schedule(talk):
    event = talk.get_event()

    if not event:
        #print('ERROR: Talk ({}) {} is not scheduled.'.format(talk.type, talk))
        return ''

    #TODO: should also check if the talk has more than one event.

    timerange = event.get_time_range()
    return '{}, {}'.format(str(timerange[0]), str(timerange[1]))


def talk_type(talk):
    type_names = dict(TYPE_NAMES)

    if 'EPS' in talk.title or 'EuroPython 20' in talk.title:
        type = 'europython'
    elif talk.title.lower().startswith('keynote'):
        type = 'keynote'
    else:
        type = talk.type

    return type_names[type]


def group_talks_by_type(talks):

    # Group by types
    type_talks = defaultdict(list)
    for talk in talks:
        if 'EPS' in talk.title or 'EuroPython 20' in talk.title:
            type = 'europython'
        elif talk.title.lower().startswith('keynote'):
            type = 'keynote'
        else:
            type = talk.type

        type_talks[type].append(talk)

    return type_talks

###

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--all_scheduled',
             action='store_true',
             dest='all_scheduled',
             default=False,
             help='Show a list of accepted talks which have not been scheduled',
        ),
        make_option('--all_accepted',
             action='store_true',
             dest='all_accepted',
             default=False,
             help='Show a list of scheduled talks which have not been accepted',
        ),
    )

    def handle(self, *args, **options):
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference not specified')

        if not options['all_scheduled'] and not options['all_accepted']:
            print('Please use either --all_scheduled or --all_accepted option.')

        if options['all_scheduled']:
            print('Checking that all accepted talks have been scheduled.')

            talks = (models.Talk.objects.filter(conference=conference, status='accepted'))
            type_talks = group_talks_by_type(talks)

            for type in type_talks:
                for talk in type_talks[type]:
                    talk_t = talk_type(talk)
                    if not talk_schedule(talk):
                        print('ERROR: Talk ({}) {} is not scheduled.'.format(talk_t, talk))

        if options['all_accepted']:
            print('Checking that all scheduled talks are accepted.')

            talks = (models.Talk.objects.filter(conference=conference))
            type_talks = group_talks_by_type(talks)

            for type in type_talks:
                for talk in type_talks[type]:
                    if talk.status != 'accepted' and talk_schedule(talk):
                        talk_t = talk_type(talk)
                        print('ERROR: Talk ({}) {} is scheduled but not accepted.'.format(talk_t, talk))
