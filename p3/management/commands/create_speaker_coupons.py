
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
from django.db.models import Q

from conference import models as cmodels
from assopy.models import Coupon


### Globals

# Discounts
#
# See cmodels.TALK_TYPES; this dictionary maps the first char of the talk
# type to a tuple (coupon_prefix, discount_code, include_combined)
#
# The coupon_prefix must have 3 chars.
#
TALK_TYPE_DISCOUNTS = {
    't': ('TLK', '25%', False),  # Talk
    'i': ('INT', '25%', False),  # Interactive
    'r': ('TRN', '100%', True), # Training
    'p': ('PST', '25%', False),  # Poster
    'n': ('PAN', '25%', False),  # Panel
    'h': ('HPD', '25%', False),  # Helpdesk
}

# Coupon prefixes used in the above dictionary
COUPON_PREFIXES = tuple(prefix
                        for ttype, (prefix, discount, include_combined)
                        in TALK_TYPE_DISCOUNTS.items())

# Add special keynote coupon prefix
COUPON_PREFIXES += ('KEY',)

assert 'TLK' in COUPON_PREFIXES

###

class Command(BaseCommand):

    # Dry run ?
    dry_run = False

    def add_arguments(self, parser):

        # Positional arguments
        parser.add_argument('conference')

        # Named (optional) arguments
        parser.add_argument('--dry-run',
                            action='store_true',
                            dest='dry_run',
                            default=False,
                            help='Do everything except create the coupons')

    @transaction.atomic
    def handle(self, *args, **options):

        self.dry_run = options.get('dry_run', False)
        conference = cmodels.Conference.objects.get(code=options['conference'])

        # Find speakers eligible for coupons
        speakers = {}
        qs = cmodels.TalkSpeaker.objects\
            .filter(Q(talk__conference=conference.code), 
                    Q(talk__status='accepted') | Q(talk__status='waitlist'),
                    Q(helper=False))\
            .select_related('talk', 'speaker__user')
        for row in qs:
            talk_code = row.talk.type[0]
            if talk_code not in TALK_TYPE_DISCOUNTS:
                continue
            coupon_prefix, discount_code, include_combined = \
                TALK_TYPE_DISCOUNTS[talk_code]
            admin_type = row.talk.admin_type
            talk_status = row.talk.status

            # Get possibly already existing entry
            if row.speaker_id in speakers:
                entry = speakers[row.speaker_id]
            else:
                entry = None

            # Handle special cases
            if admin_type == 'k':
                # Keynote talk
                coupon_prefix = 'KEY'
                discount_code = '100%'
                include_combined = True
                # Force an override
                entry = None

            elif admin_type:
                # All other admin types are not eligible for coupons
                continue
                
            if talk_code == 'r':
                # Override existing talk discount with training; this
                # means that someone who does e.g. both a talk and
                # training, will get the higher training discount
                if (entry is not None and
                    entry['discount'] != '100%'):
                    entry = None

            if talk_code == 'r' and talk_status == 'waitlist':
                # Training entries on the waiting list only get a
                # 25% coupon, not a 100% one
                discount_code = '25%'

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
                'include_combined': include_combined,
                'prefix': coupon_prefix,
                'talk_id': row.talk.id,
                'speaker_id': row.speaker_id,
                'talk_status': row.talk.status,
                }
            speakers[row.speaker_id] = entry

        # Valid fares (conference fares only, no training passes)
        conference_fares = cmodels.Fare.objects\
            .filter(conference=conference.code,
                    ticket_type='conference')\
            .exclude(code__startswith='TRT')\
            .exclude(code__startswith='TRC')
        combined_fares = cmodels.Fare.objects\
            .filter(conference=conference.code,
                    ticket_type='conference')\
            .exclude(code__startswith='TRT')

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

        # Output header
        csv_header = (
            'email',
            'name',
            'prefix',
            'code',
            'discount',
            'donated',
            'amount',
            'title', 
            'duration', 
            'type', 
            'admin_type', 
            'talk_id', 
            'speaker_id',
            'talk_status',
            'include_combined',
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
                        + ''.join(random.sample(string.ascii_uppercase, 6)))
                if code not in codes:
                    codes.add(code)
                    break

            # Build CSV data (see csv_header for order)
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
                entry['talk_status'],
                entry['include_combined'],
                )

            # Create coupon
            c = Coupon(conference=conference)
            c.code = code
            c.user = user.assopy_user
            c.max_usage = 1
            c.items_per_usage = 1
            c.value = value
            c.description = '[%s] %s Speaker Discount' % (
                conference, entry['prefix'])
            if entry['include_combined']:
                fares = combined_fares
            else:
                fares = conference_fares
            if not self.dry_run:
                c.save()
                c.fares = fares
            data.append(data_row)

        # Output CSV data, UTF-8 encoded
        data.insert(0, csv_header)
        for row in data:
            csv_data = ('"%s"' % (str(x).replace('"', '""'))
                        for x in row)
            print(','.join(csv_data))
