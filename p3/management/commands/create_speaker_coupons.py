# -*- coding: UTF-8 -*-
""" Create coupons for speakers:

    Talk        - 25%
    Poster      - 25%
    Helpdesk    - 25%
    Interactive - 25%
    Panel       - 25%

    Training    - 100%

    Write the created coupons as CSV data to stdout. The script makes
    sure that no duplicate coupons are created. If you want a coupon
    to get recreated, deleted it in the database first and then run
    the script.

    Use --dry-run to test drive the script.

    WARNING: This script will create coupons for all speakers,
    including ones which are giving sponsored talks.

"""
import string
import random
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from conference import models as cmodels
from assopy.models import Coupon


### Globals

# Discounts
#
# See cmodels.TALK_TYPES; this dictionary maps the first char of the talk
# type to a tuple (coupon_prefix, discount_code)
#
# The coupon_prefix must have 3 chars.
#
TALK_TYPE_DISCOUNTS = {
    't': ('TLK', '25%'), # Talk
    'i': ('INT', '25%'), # Interactive
    'r': ('TRN', '100%'),# Training
    'p': ('PST', '25%'), # Poster
    'n': ('PAN', '25%'), # Panel
    'h': ('HPD', '25%'), # Helpdesk
}

# Coupon prefixes used in the above dictionary
COUPON_PREFIXES = tuple(prefix for (prefix, discount) in TALK_TYPE_DISCOUNTS.items())

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
            talk_code = row.talk.type[0]
            if talk_code not in TALK_TYPE_DISCOUNTS:
                continue
            coupon_prefix, discount_code = TALK_TYPE_DISCOUNTS[talk_code]
            if row.speaker_id not in speakers:
                entry = {
                    'spk': row.speaker,
                    'title': row.talk.title,
                    'duration': row.talk.duration,
                    'discount': discount_code,
                    'prefix': coupon_prefix,
                    }
                speakers[row.speaker_id] = entry
            else:
                entry = speakers[row.speaker_id]
            # Override existing discount with training; this
            # means that someone who does e.g. both a talk and training,
            # will get a training discount
            if talk_code == 'r':
                entry['discount'] = discount_code
                entry['prefix'] = coupon_prefix
                entry['title'] = row.talk.title
                entry['duration'] = row.talk.duration

        # Valid fares (conference fares only)
        fares = cmodels.Fare.objects\
            .filter(conference=conference.code,
                    ticket_type='conference')

        # Get set of existing codes
        codes = set(c['code'] for c in Coupon.objects\
            .filter(conference=conference.code)\
            .values('code'))

        # Get coupon emails of already issued coupons
        existing_coupon_emails = set(
            c['user__user__email']
            for c in Coupon.objects\
            .filter(conference=conference.code)\
            .select_related('user')\
            .values('user__user__email', 'code')
            if (c['code'].startswith(COUPON_PREFIXES)
                and c['user__user__email'])
            )

        # Create coupons
        data = []
        for sid, entry in speakers.items():

            # Get coupon data
            coupon_prefix = entry['prefix']
            user = entry['spk'].user
            value = entry['discount']

            # Check if we have already issued a coupon
            if user.email in existing_coupon_emails:
                continue

            # Determine a new code
            while True:
                # Codes: SPK-RANDOM
                code = (coupon_prefix + '-'
                        + ''.join(random.sample(string.uppercase, 6)))
                if code not in codes:
                    codes.add(code)
                    break

            # Build CSV data
            name = u'%s %s' % (user.first_name, user.last_name)
            data_row = (
                user.email,
                name,
                entry['prefix'],
                code,
                value,
                '', # donated (date)
                '', # donated amount
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
                conference, entry['prefix'])
            if not self.dry_run:
                c.save()
                c.fares = fares
            data.append(data_row)

        # Output CSV data, UTF-8 encoded
        data.insert(0, (
            # Header
            'email', 'name', 'prefix', 'code', 'discount', 'donated', 'amount',
            'title', 'duration'))
        for row in data:
            csv_data = (u'"%s"' % (unicode(x).replace(u'"', u'""'))
                        for x in row)
            print (u','.join(csv_data).encode('utf-8'))
