# -*- coding: UTF-8 -*-
import haystack

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
        talks = models.Talk.objects.accepted(conference.code)
        for t in talks:
            for s in t.get_all_speakers():
                if t.training_available:
                    speakers[s] = 'training'
                elif s not in speakers:
                    speakers[s] = 'talk'
        codes = set(c['code'] for c in Coupon.objects.filter(conference=conference.code).values('code'))
        for spk, tt in speakers.items():
            while True:
                code = ''.join(random.sample(string.letters, 6))
                if code not in codes:
                    codes.add(code)
                    break
            if tt == 'training':
                value = '100%'
            else:
                value = '100'
            print code, spk.user.assopy_user.name().encode('utf-8'), spk.user.email, 'value:', value
            c = Coupon(conference=conference)
            c.code = code
            c.user = spk.user.assopy_user
            c.max_usage = 1
            c.value = value
            c.description = '[%s] speaker discount' % conference
            c.save()
