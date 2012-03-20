# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand, CommandError
from conference import models
from email_template import utils

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference missing')

        # filtro dei poveri per selezionare i talk da una certa data in poi;
        # servirebbe un vero campo `data` nel Talk
        try:
            start_id = args[1]
        except IndexError:
            start_id = None

        qs = models.TalkSpeaker.objects\
            .filter(talk__conference=conference)\
            .select_related('talk', 'speaker__user')
        if start_id:
            qs = qs.filter(talk__id__gte=start_id)

        data = []
        for row in qs:
            email = row.speaker.user.email
            ctx = {
                'user': row.speaker.user,
                'talk': row.talk,
            }
            if row.talk.type == 's':
                tpl = 'verify-talk-data'
            elif row.talk.type == 'p':
                tpl = 'verify-poster-data'
            elif row.talk.type == 't':
                tpl = 'verify-training-data'
            else:
                raise ValueError('unknown talk type')
            data.append((email, ctx, tpl))

        for email, ctx, tpl in data:
            utils.email(tpl, ctx, to=[email]).send()

