
""" Create a batch of single use discount coupons from a CSV file.

    Parameters: <conference> <csv-file>

    Creates coupons based on the CSV file contents:
    
	code		- coupon code
        max_usage 	- max. number of uses
	items_per_usage - max number of items per use
	value		- value of the coupon in percent
	description     - description
	fares 		- comma separated list of included fares

    Use --dry-run to test drive the script.

"""
import sys
import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from conference import models as cmodels
from assopy.models import Coupon

###

class Command(BaseCommand):

    args = '<conference> <count>'

    # Dry run ?
    dry_run = False

    def add_arguments(self, parser):

        # Positional arguments
        parser.add_argument('conference')
        parser.add_argument('csv')

        # Named (optional) arguments
        parser.add_argument('--dry-run',
                            action='store_true',
                            dest='dry_run',
                            default=False,
                            help='Do everything except create the coupons')

    @transaction.atomic
    def handle(self, *args, **options):

        conference = cmodels.Conference.objects.get(code=options['conference'])
        self.dry_run = options.get('dry_run', False)
        csv_filename = options['csv']

        # Get set of existing coupon codes
        all_codes = dict((c.code, c)
            for c in Coupon.objects\
                .filter(conference=conference.code))

        # Valid fares (conference fares only)
        all_fares = cmodels.Fare.objects\
            .filter(conference=conference.code)
        
        # Create coupons
        if csv_filename == 'stdin':
            csv_file = sys.stdin
        else:
            csv_file = open(csv_filename)
        with csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                #print ('Row %r' % row)
                code = row['code'].strip()
                if not code or code == '0':
                    # Skip lines without code
                    continue
                if code in all_codes:
                    print ('Coupon %r already exists - updating' % code)
                    c = all_codes[code]
                else:
                    print ('New coupon %r will be created' % c.code)
                    c = Coupon(conference=conference)
                    c.code = code
                c.max_usage = int(row.get('max_usage', 1))
                c.items_per_usage = int(row.get('items_per_usage', 1))
                c.value = row['value']
                c.description = row.get('description', '')
                if not self.dry_run:
                    c.save()
                    c.fares.set(all_fares.filter(
                        code__in = [x.strip()
                                    for x in row['fares'].split(',')]))
