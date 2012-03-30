# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from conference import models
from conference import utils

from collections import defaultdict
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

        talks = models.Talk.objects\
            .filter(conference=conference, status='proposed')
        if options['show_input']:
            print utils._input_for_ranking_of_talks(talks)
        else:
            qs = models.VotoTalk.objects\
                .filter(talk__in=talks)\
                .values('user')
            votes = qs.count()
            users = qs.distinct().count()
            speakers = defaultdict(list)
            sqs = models.TalkSpeaker.objects\
                .filter(talk__in=talks)\
                .values('talk', 'speaker__user__first_name', 'speaker__user__last_name')
            for row in sqs:
                name = '%s %s' % (row['speaker__user__first_name'], row['speaker__user__last_name'])
                speakers[row['talk']].append(name.encode('utf-8'))

            print '%d talks / %d users / %d votes' % (talks.count(), users, votes)
            results = defaultdict(lambda: defaultdict(list))
            for t in utils.ranking_of_talks(talks):
                results[t.type][t.language].append(t)

            for type, label in models.TALK_TYPE:
                for language, subset in results[type].items():
                    if subset:
                        print label, '(%s)' % language
                        print '-' * 79
                        for ix, t in enumerate(subset):
                            print ix+1, '-', t.id, '-', t.title.encode('utf-8'), '(%s)' % ', '.join(speakers[t.id])
                        print ''
