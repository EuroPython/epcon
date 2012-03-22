# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand, CommandError
from conference import models
from datetime import datetime
from email_template import utils

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference missing')

        try:
            afilter = args[1]
        except IndexError:
            afilter = ''

        qs = models.TalkSpeaker.objects\
            .filter(talk__conference=conference)\
            .select_related('talk', 'speaker__user')\
            .order_by('talk__created')
        if '@' in afilter:
            qs = qs.filter(speaker__user__email=afilter)
        elif '/' in afilter:
            d = datetime.strptime(afilter, '%Y/%m/%dT%H:%M:%S')
            qs = qs.filter(talk__created__gt=d)
        # more filters here...

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
            print email, '->', row.talk.title, '(%s)' % row.talk.type, row.talk.created
            data.append((email, ctx, tpl))

        for email, ctx, tpl in data:
            utils.email(tpl, ctx, to=[email]).send()

