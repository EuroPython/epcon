# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from conference import models
from conference import utils

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference not specified')

        talks = models.Talk.objects.filter(conference=conference)
        votes = models.VotoTalk.objects.filter(talk__in=talks)
        users = set(x.user_id for x in votes)
        print '%d talks / %d users / %d votes' % (talks.count(), len(users), len(votes))
        for ix, t in enumerate(utils.ranking_of_talks(talks)):
            print ix+1, '-', t.id, '-', t.title.encode('utf-8'), '(%s)' % (', '.join(s.name.encode('utf-8') for s in t.get_all_speakers()),)
