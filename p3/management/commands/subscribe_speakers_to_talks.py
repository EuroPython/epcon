# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand, CommandError
from conference import models as cmodels
from hcomments import models as hmodels

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            conf = args[0]
        except IndexError:
            raise CommandError('conference missing')
        qs = cmodels.TalkSpeaker.objects\
            .filter(talk__conference=conf)\
            .select_related('talk', 'speaker__user')
        for row in qs:
            u = row.speaker.user
            t = row.talk
            print '%s %s -> %s' % (u.first_name, u.last_name, t.title)
            hmodels.ThreadSubscription.objects.subscribe(t, u)
