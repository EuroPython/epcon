# -*- coding: UTF-8 -*-
import json
import signal
import sys
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from conference import utils
from conference import settings

signal.alarm(5*60)

class Command(BaseCommand):
    """
    """
    option_list = BaseCommand.option_list + (
        make_option('--count',
            action='store',
            dest='count',
            default=1,
            help='How many tweet retrieve',
        ),
        make_option('--output',
            action='store',
            dest='output',
            default=settings.LATEST_TWEETS_FILE,
            help='Write the output in this. If an error occurs output file is not overwritten. - means stdout',
        ),
    )
    def handle(self, *args, **options):
        try:
            screen_name = args[0]
        except IndexError:
            raise CommandError('screen_name missing')

        data = json.dumps(utils.latest_tweets(screen_name, count=options['count']))
        if data:
            if options['output'] in ('-', None):
                sys.stdout.write(data)
            else:
                file(options['output'], 'w').write(data)
