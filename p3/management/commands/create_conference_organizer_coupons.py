""" Create EPS Python conference organizer discount coupons.

    Parameters: <conference> <count>

    Valid for conference tickets, one use and one item per order.  Not valid
    for the social event.

    Created coupons are written as CSV data to stdout.

    Use --dry-run to test drive the script.

"""
import string
import random
import csv
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from conference import models as cmodels
from conference.fares import FARE_CODE_REGEXES, FARE_CODE_VARIANTS
from assopy.models import Coupon


# ## Globals

# Coupon prefix
COUPON_PREFIX = "PYO"

# Discount
EPS_PYORGANIZER_DISCOUNT = "100%"

# Max usage per coupon
COUPON_MAX_USAGE = 1

# Max items per order
COUPON_ITEMS_PER_USAGE = 1

###


class Command(BaseCommand):

    # Dry run ?
    dry_run = False

    def add_arguments(self, parser):

        # Positional arguments
        parser.add_argument("conference")
        parser.add_argument("count", type=int)

        # Named (optional) arguments
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Do everything except create the coupons",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        self.dry_run = options.get("dry_run", False)

        conference = cmodels.Conference.objects.get(code=options["conference"])
        number_of_coupons = options["count"]

        # Valid fares (conference fares only)
        fares = cmodels.Fare.objects.filter(
            conference=conference.code,
            code__regex=FARE_CODE_REGEXES["variants"][
                FARE_CODE_VARIANTS.STANDARD
            ],
        )

        # Get set of existing codes
        codes = set(
            c["code"]
            for c in Coupon.objects.filter(conference=conference.code).values(
                "code"
            )
        )

        # Create coupons
        data = []
        for i in range(number_of_coupons):

            coupon_prefix = COUPON_PREFIX
            value = EPS_PYORGANIZER_DISCOUNT

            # Determine a new code
            while True:
                # Codes: SPK-RANDOM
                code = (
                    coupon_prefix
                    + "-"
                    + "".join(random.sample(string.ascii_uppercase, 6))
                )
                if code not in codes:
                    codes.add(code)
                    break

            # Create coupon
            c = Coupon(
                conference=conference,
                code=code,
                max_usage=COUPON_MAX_USAGE,
                items_per_usage=COUPON_ITEMS_PER_USAGE,
                value=value,
                description="EPS Python Conference Organizer Discount",
            )
            if not self.dry_run:
                c.save()
                c.fares = fares

            # Build CSV data
            data_row = (c.code, c.value, c.max_usage, c.items_per_usage)
            data.append(data_row)

        header = "code", "value", "max_usage", "items_per_usage"
        writer = csv.writer(sys.stdout)

        writer.writerow(header)

        for row in data:
            writer.writerow(row)
