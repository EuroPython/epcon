# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from conference import models
from assopy.models import Coupon

import string
import random

class Command(BaseCommand):
    """
    """
    @transaction.commit_on_success
    def handle(self, *args, **options):
        try:
            conference = models.Conference.objects.get(code=args[0])
        except IndexError:
            raise CommandError('conference missing')
        
        speakers = {}
        qs = models.TalkSpeaker.objects\
            .filter(talk__conference=conference.code, talk__status='accepted')\
            .select_related('talk', 'speaker__user')
        for row in qs:
            if row.talk.type not in ('t', 's'):
                continue
            if row.speaker_id not in speakers:
                 speakers[row.speaker_id] = {
                    'spk': row.speaker,
                    'discount': 'talk',
                }
            s = speakers[row.speaker_id]
            if row.talk.type == 't':
                s['discount'] = 'training'


        fares = models.Fare.objects\
            .filter(conference=conference.code, ticket_type='conference')
        codes = set([c['code'] for c in Coupon.objects\
            .filter(conference=conference.code)\
            .values('code')])

        for sid, data in speakers.items():
            while True:
                code = ''.join(random.sample(string.uppercase, 6))
                if code not in codes:
                    codes.add(code)
                    break
            if data['discount'] == 'training':
                value = '100%'
            else:
                value = '100'

            u = data['spk'].user
            name = '%s %s' % (u.first_name, u.last_name)
            print code, name.encode('utf-8'), u.email, 'value:', value
            c = Coupon(conference=conference)
            c.code = code
            c.user = u.assopy_user
            c.max_usage = 1
            c.items_per_usage = 1
            c.value = value
            c.description = '[%s] speaker discount' % conference
            c.save()
            c.fares = fares
