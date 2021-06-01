from django.core.management.base import BaseCommand, CommandError
from conference import models
from conference import utils

from optparse import make_option


class Command(BaseCommand):

    def add_arguments(self, parser):

        # Positional arguments
        parser.add_argument('conference')

        # Named (optional) arguments
        parser.add_argument(
            '--missing-vote',
            action='store',
            dest='missing_vote',
            default=0,
            type=float,
            help='Used when a user didn\'t vote a talk'
            )
        parser.add_argument(
            '--show-input',
            action='store_true',
            dest='show_input',
            default=False,
            help='Show the input data piped to votengine',
            )

    def handle(self, *args, **options):
        try:
            conference = options['conference']
        except IndexError:
            raise CommandError('conference not specified')

        talks = models.Talk.objects\
            .filter(conference=conference, status='proposed')
        if options['show_input']:
            print(utils._input_for_ranking_of_talks(talks, missing_vote=options['missing_vote']))
        else:
            qs = models.VotoTalk.objects\
                .filter(talk__in=talks)\
                .values('user')
            votes = qs.count()
            users = qs.distinct().count()
            print(f'Talk voting results for {conference}: {talks.count()} talks / {users} users / {votes} votes')
            print('')
            print(f'Rank,TalkID,TalkType,TalkLanguage,TalkTitle,FirstSpeaker,AllSpeakers')
            for ix, t in enumerate(utils.ranking_of_talks(talks, missing_vote=options['missing_vote'])):
                speakers = [str(speaker) for speaker in list(t.get_all_speakers())]
                first_speaker = speakers[0]
                all_speakers = ', '.join(speakers)
                print(f'{ix + 1},{t.id},{t.type},{t.language},"{t.title}","{first_speaker}","{all_speakers}"')
