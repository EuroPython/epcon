# -*- coding: UTF-8 -*-
""" Create coupons for speakers:

    Talk     - 25%
    Training - 100%

    Write the created coupons as CSV data to stdout.

"""
import string
import random
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from conference import models as cmodels
from assopy.models import Coupon


### Globals

# From cmodels.TALK_TYPES
TALK_TYPE_TALK = 's'
TALK_TYPE_TRAINING = 't'

# Discounts
SPEAKER_DISCOUNT = '25%'
TRAINING_DISCOUNT = '100%'

# Coupon prefix (3 letters)
COUPON_PREFIX = {
    'speaker': 'SPK',
    'trainer': 'TRN',
    }

###

class Command(BaseCommand):
    
    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
                    action='store_true',
                    dest='dry_run',
                    help='Do everything except create the coupons',
                    ),
    )

    # Dry run ?
    dry_run = False

    @transaction.commit_on_success
    def handle(self, *args, **options):

        self.dry_run = options.get('dry_run', False)
        
        try:
            conference = cmodels.Conference.objects.get(code=args[0])
        except IndexError:
            raise CommandError('conference missing')

        # Find speakers eligible for coupons
        speakers = {}
        qs = cmodels.TalkSpeaker.objects\
            .filter(talk__conference=conference.code, talk__status='accepted')\
            .select_related('talk', 'speaker__user')
        for row in qs:
            if row.talk.type not in (TALK_TYPE_TALK,
                                     TALK_TYPE_TRAINING):
                continue
            if row.speaker_id not in speakers:
                entry = {
                    'spk': row.speaker,
                    'title': row.talk.title,
                    'duration': row.talk.duration,
                    'discount': SPEAKER_DISCOUNT,
                    'type': 'speaker',
                    }
                speakers[row.speaker_id] = entry
            else:
                entry = speakers[row.speaker_id]
            # Override discount with 'training' for trainings; this
            # means that someone who does both a talk and training,
            # will get a training discount
            if row.talk.type == TALK_TYPE_TRAINING:
                entry['discount'] = TRAINING_DISCOUNT
                entry['type'] = 'trainer'
                entry['title'] = row.talk.title
                entry['duration'] = row.talk.duration

        # Valid fares (conference fares only)
        fares = cmodels.Fare.objects\
            .filter(conference=conference.code,
                    ticket_type='conference')

        # Get set of existing codes
        codes = set([c['code'] for c in Coupon.objects\
            .filter(conference=conference.code)\
            .values('code')])

        # Create coupons
        data = []
        for sid, entry in speakers.items():
            # Coupon type
            type = entry['type']

            # Determine a new code
            coupon_prefix = COUPON_PREFIX[type]
            while True:
                # Codes: SPK-RANDOM
                code = (coupon_prefix + '-'
                        + ''.join(random.sample(string.uppercase, 6)))
                if code not in codes:
                    codes.add(code)
                    break

            # Coupon value
            value = entry['discount']

            # Get user data
            user = entry['spk'].user
            name = u'%s %s' % (user.first_name, user.last_name)
            data_row = (
                user.email,
                name,
                entry['type'],
                code,
                value,
                entry['title'],
                entry['duration'],
                )

            # Create coupon
            c = Coupon(conference=conference)
            c.code = code
            c.user = user.assopy_user
            c.max_usage = 1
            c.items_per_usage = 1
            c.value = value
            c.description = '[%s] %s discount' % (
                conference, entry['type'])
            if not self.dry_run:
                c.save()
                c.fares = fares
            data.append(data_row)

        # Output CSV data, UTF-8 encoded
        data.insert(0, (
            # Header
            'email', 'name', 'type', 'code', 'discount', 'title', 'duration'))
        for row in data:
            csv_data = (u'"%s"' % (unicode(x).replace(u'"', u'""'))
                        for x in row)
            print (u','.join(csv_data).encode('utf-8'))
