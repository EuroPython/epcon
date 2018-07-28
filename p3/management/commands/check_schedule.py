# -*- coding: utf-8 -*-
""" Print accepted talks not scheduled and not accepted talks which have been
scheduled.
"""
from   optparse     import make_option

from   django.core.management.base import BaseCommand, CommandError
from   conference   import models

from ...utils import (talk_schedule,
                      talk_type,
                      group_talks_by_type,
                      talk_track_title)


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
                    schedules = list(talk_schedule(talk))
                    if not schedules:
                        print('ERROR: {} (id: {}) "{}" is not '
                              'scheduled'.format(talk_type(talk), talk.id, talk))
                    elif len(schedules) > 1:
                        print('ERROR: {} (id: {}) "{}" is '
                              'scheduled {} times: {} in {}.'.format(talk_type(talk),
                                                                     talk.id,
                                                                     talk,
                                                                     len(schedules),
                                                                     schedules,
                                                                     talk_track_title(talk)))


        if options['all_accepted']:
            print('Checking that all scheduled talks are accepted.')

            talks = (models.Talk.objects.filter(conference=conference))
            type_talks = group_talks_by_type(talks)

            for type in type_talks:
                for talk in type_talks[type]:
                    schedules = list(talk_schedule(talk))
                    if talk.status != 'accepted' and schedules:
                        print('ERROR: {} (id: {}) "{}" is scheduled but '
                              'not accepted.'.format(talk_type(talk),
                                                     talk.id,
                                                     talk))
