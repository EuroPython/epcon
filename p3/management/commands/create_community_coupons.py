# -*- coding: utf-8 -*-
""" Create EPS community discount coupons.

    Parameters: <conference> <count>

    Valid for conference tickets, 50 uses at most and one item per
    order.  Not valid for the social event.

    Created coupons are written as CSV data to stdout.

    Use --dry-run to test drive the script.

"""
import string
import random
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from conference import models as cmodels
from assopy.models import Coupon


### Globals

# Coupon prefix
COUPON_PREFIX = 'EPS'

# Discount
EPS_COMMUNITY_DISCOUNT = '10%'

# Max usage per coupon
COUPON_MAX_USAGE = 50

# Max items per order
COUPON_ITEMS_PER_USAGE = 1

###

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
                    action='store_true',
                    dest='dry_run',
                    help='Do everything except create the coupons',
                    ),
    )

    args = '<conference> <count>'

    # Dry run ?
    dry_run = False

    @transaction.atomic
    def handle(self, *args, **options):

        self.dry_run = options.get('dry_run', False)

        try:
            conference = cmodels.Conference.objects.get(code=args[0])
        except IndexError:
            raise CommandError('conference missing')

        try:
            number_of_coupons = int(args[1])
        except IndexError:
            raise CommandError('coupon count missing')

        # Valid fares (conference fares only)
        fares = cmodels.Fare.objects\
            .filter(conference=conference.code,
                    ticket_type='conference')

        # Get set of existing codes
        codes = set(c['code'] for c in Coupon.objects\
            .filter(conference=conference.code)\
            .values('code'))

        # Create coupons
        data = []
        for i in range(number_of_coupons):

            coupon_prefix = COUPON_PREFIX
            value = EPS_COMMUNITY_DISCOUNT

            # Determine a new code
            while True:
                # Codes: SPK-RANDOM
                code = (coupon_prefix + '-'
                        + ''.join(random.sample(string.uppercase, 6)))
                if code not in codes:
                    codes.add(code)
                    break

            # Create coupon
            c = Coupon(conference=conference)
            c.code = code
            c.max_usage = COUPON_MAX_USAGE
            c.items_per_usage = COUPON_ITEMS_PER_USAGE
            c.value = value
            c.description = 'EPS Community Discount'
            if not self.dry_run:
                c.save()
                c.fares = fares

            # Build CSV data
            data_row = (
                c.code,
                c.value,
                c.max_usage,
                c.items_per_usage,
                )
            data.append(data_row)

        # Output CSV data, UTF-8 encoded
        data.insert(0, (
            # Header
            'code', 'value', 'max_usage', 'items_per_usage',
            ))
        for row in data:
            csv_data = ('"%s"' % (str(x).replace('"', '""'))
                        for x in row)
            print(','.join(csv_data).encode('utf-8'))
