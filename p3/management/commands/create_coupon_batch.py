# -*- coding: UTF-8 -*-
""" Create a batch of single use discount coupons.

    Parameters: <conference> <ticket-code> <count> <amount> [<coupon-code>]

    Creates single use coupons for the given amount and ticket-code.
    Coupon code ise used a prefix for the coupon code. Default is 'SPC'

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
DEFAULT_PREFIX = 'SPC'

# Max usage per coupon
COUPON_MAX_USAGE = 1

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
            ticket_code = str(args[1])
        except IndexError:
            raise CommandError('ticket code missing')

        try:
            number_of_coupons = int(args[2])
        except IndexError:
            raise CommandError('coupon count missing')

        try:
            amount_per_coupon = str(args[3])
        except IndexError:
            raise CommandError('coupon discount amount missing')

        try:
            coupon_prefix = str(args[4])
        except IndexError:
            coupon_prefix = DEFAULT_PREFIX

        # Valid fares (conference fares only)
        fares = cmodels.Fare.objects\
            .filter(conference=conference.code,
                    code__contains=ticket_code)

        # Get set of existing coupon codes
        codes = set(c['code'] for c in Coupon.objects\
            .filter(conference=conference.code)\
            .values('code'))

        # Create coupons
        data = []
        for i in range(number_of_coupons):

            value = amount_per_coupon

            # Determine a new code
            while True:
                # Codes: SPC-RANDOM (10 chars)
                code = (coupon_prefix + '-'
                        + ''.join(random.sample(string.uppercase, 9 - len(coupon_prefix))))
                if code not in codes:
                    codes.add(code)
                    break

            # Create coupon
            c = Coupon(conference=conference)
            c.code = code
            c.max_usage = COUPON_MAX_USAGE
            c.items_per_usage = COUPON_ITEMS_PER_USAGE
            c.value = value
            c.description = 'Special Discount'
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
            print((','.join(csv_data)))
