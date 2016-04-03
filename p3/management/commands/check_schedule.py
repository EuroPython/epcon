# -*- coding: utf-8 -*-
""" Print accepted talks not scheduled and not accepted talks which have been
scheduled.
"""
from   collections  import defaultdict
from   optparse     import make_option
import operator

import simplejson   as json

from   django.core.management.base import BaseCommand, CommandError
from   django.core  import urlresolvers
from   conference   import models
from   conference   import utils
from   conference.models import TALK_TYPE, TALK_ADMIN_TYPE

### Globals
# TALK_TYPE = (
#     ('t_30', 'Talk (30 mins)'),
#     ('t_45', 'Talk (45 mins)'),
#     ('t_60', 'Talk (60 mins)'),
#     ('i_60', 'Interactive (60 mins)'),
#     ('r_180', 'Training (180 mins)'),
#     ('p_180', 'Poster session (180 mins)'),
#     ('n_60', 'Panel (60 mins)'),
#     ('n_90', 'Panel (90 mins)'),
#     ('h_180', 'Help desk (180 mins)'),
# )

# TALK_ADMIN_TYPE = (
#     ('o', 'Opening session'),
#     ('c', 'Closing session'),
#     ('l', 'Lightning talk'),
#     ('k', 'Keynote'),
#     ('r', 'Recruiting session'),
#     ('m', 'EPS session'),
#     ('s', 'Open space'),
#     ('e', 'Social event'),
# )


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
    if talk.admin_type:
        typ = talk.get_admin_type_display()
    else:
        typ = talk.get_type_display()
    return typ


def group_talks_by_type(talks):
    # Group by types
    type_talks = defaultdict(list)
    for talk in talks:
        type_talks[talk_type(talk)].append(talk)

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

            talks = (models.Talk.objects.filter(conference=conference,
                                                status='accepted'))
            type_talks = group_talks_by_type(talks)

            for type in type_talks:
                for talk in type_talks[type]:
                    talk_t = talk_type(talk)
                    if not talk_schedule(talk):
                        print('ERROR: {} (id: {}) "{}" is not '
                              'scheduled'.format(talk_t, talk.id, talk))

        if options['all_accepted']:
            print('Checking that all scheduled talks are accepted.')

            talks = (models.Talk.objects.filter(conference=conference))
            type_talks = group_talks_by_type(talks)

            for type in type_talks:
                for talk in type_talks[type]:
                    if talk.status != 'accepted' and talk_schedule(talk):
                        talk_t = talk_type(talk)
                        print('ERROR: {} (id: {}) "{}" is scheduled but '
                              'not accepted.'.format(talk_t, talk.id, talk))
