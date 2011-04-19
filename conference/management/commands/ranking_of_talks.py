# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from conference import models
from conference import utils

from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--show-input',
            action='store_true',
            dest='show_input',
            default=False,
            help='Show the input data piped to votengine',
        ),
    )
    def handle(self, *args, **options):
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference not specified')

        talks = models.Talk.objects.filter(conference=conference)
        votes = models.VotoTalk.objects.filter(talk__in=talks)
        users = set(x.user_id for x in votes)
        if options['show_input']:
            print utils._input_for_ranking_of_talks(talks)
        else:
            print '%d talks / %d users / %d votes' % (talks.count(), len(users), len(votes))
            for ix, t in enumerate(utils.ranking_of_talks(talks)):
                print ix+1, '-', t.id, '-', t.title.encode('utf-8'), '(%s)' % (', '.join(s.name.encode('utf-8') for s in t.get_all_speakers()),)
