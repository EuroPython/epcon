# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand, CommandError

from microblog import models

from optparse import make_option

class Command(BaseCommand):
    args = "account"
    option_list = BaseCommand.option_list + (
        make_option('--type',
            action='store',
            dest='type',
            default='e',
            help='spam type: e - email, t - twitter'),
        )

    def handle(self, *args, **options):
        try:
            value = args[0]
        except IndexError:
            raise CommandError('email address not specified')

        for p in models.Post.objects.published():
            if not p.spammed(method=options['type'], value=value):
                s = models.Spam(post=p, method=options['type'], value=value)
                s.save()
