
""" Create training pass coupons for trainers:

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

_debug = 0

# Discounts
#
# See cmodels.TALK_TYPES; this dictionary maps the first char of the talk
# type to a tuple (coupon_prefix, discount_code)
#
# The coupon_prefix must have 3 chars.
#
TALK_TYPE_DISCOUNTS = {
    'r': ('TRP', '100%'), # Training passes
}

# Coupon prefixes used in the above dictionary
COUPON_PREFIXES = tuple(prefix
                        for ttype, (prefix, discount)
                        in TALK_TYPE_DISCOUNTS.items())

# MAL 2018-06-07: Program WG decided against giving training passes to
# keynote speakers.

# Add special keynote coupon prefix
#COUPON_PREFIXES += ('KYT',)

assert 'TRP' in COUPON_PREFIXES

###

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
                    action='store_true',
                    dest='dry_run',
                    help='Do everything except create the coupons',
                    ),
    )

    args = '<conference>'

    # Dry run ?
    dry_run = False

    @transaction.atomic
    def handle(self, *args, **options):

        self.dry_run = options.get('dry_run', False)

        try:
            conference = cmodels.Conference.objects.get(code=args[0])
        except IndexError:
            raise CommandError('conference missing')

        # Find speakers eligible for coupons
        speakers = {}
        qs = cmodels.TalkSpeaker.objects\
            .filter(talk__conference=conference.code, 
                    talk__status='accepted',
                    helper=False)\
            .select_related('talk', 'speaker__user')
        if _debug: 
            print('Found %i speakers' % len(qs))
        for row in qs:
            talk_code = row.talk.type[0]
            if talk_code not in TALK_TYPE_DISCOUNTS:
                continue
            coupon_prefix, discount_code = TALK_TYPE_DISCOUNTS[talk_code]
            admin_type = row.talk.admin_type

            # Get possibly already existing entry
            if row.speaker_id in speakers:
                entry = speakers[row.speaker_id]
            else:
                entry = None

            # Handle special cases
            if 0:
               pass

#            elif admin_type == 'k':
#                # Keynote talk
#                coupon_prefix = 'KYT'
#                discount_code = '100%'
#                # Force an override
#                entry = None

            elif admin_type:
                # All other admin types are not eligible for coupons
                continue
                
            # Entry already exists, so don't create a new coupon
            if entry is not None:
                continue

            # Create a new entry
            entry = {
                'spk': row.speaker,
                'title': row.talk.title,
                'type': talk_code,
                'admin_type': row.talk.admin_type,
                'duration': row.talk.duration,
                'discount': discount_code,
                'prefix': coupon_prefix,
                'talk_id': row.talk.id,
                'speaker_id': row.speaker_id,
                }
            speakers[row.speaker_id] = entry

        if _debug: 
            print('%i speakers are eligible' % len(speakers))

        # Valid fares (training pass fares only)
        fares = cmodels.Fare.objects\
            .filter(conference=conference.code,
                    ticket_type='conference',
                    code__startswith='TRT')
        if _debug:
            print('Found %i fares: %r' % 
                  (len(fares), [str(f) for f in fares]))

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
            name = '%s %s' % (user.first_name, user.last_name)
            value = entry['discount']
            title = entry['title']

            # Check for reserved slots
            if (entry['admin_type'] == 'x' or 
                'reserved for' in title.lower()):
                continue

            # Check for placeholder entries
            if name.lower() in ('to be announced', 'tobey announced'):
                continue

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
                entry['type'],
                entry['admin_type'],
                entry['talk_id'],
                entry['speaker_id'],
                )

            # Create coupon
            c = Coupon(conference=conference)
            c.code = code
            c.user = user.assopy_user
            c.max_usage = 1
            c.items_per_usage = 1
            c.value = value
            c.description = '[%s] %s Trainer Discount' % (
                conference, entry['prefix'])
            if not self.dry_run:
                c.save()
                c.fares = fares
                if _debug: 
                    print('Added fares %r to %r' % (fares, c))
            data.append(data_row)

        # Output CSV data, UTF-8 encoded
        data.insert(0, (
            # Header
            'email', 'name', 'prefix', 'code', 'discount', 'donated', 'amount',
            'title', 'duration', 'type', 'admin_type', 'talk_id', 'speaker_id'))
        for row in data:
            csv_data = ('"%s"' % (str(x).replace('"', '""'))
                        for x in row)
            print(','.join(csv_data).encode('utf-8'))
