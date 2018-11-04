# -*- coding: utf-8 -*-



from django.core.management.base import BaseCommand

from conference.currencies import fetch_and_store_latest_ecb_exrates


class Command(BaseCommand):
    """
    Checks ECB API endpoint for the new exrates, if there are any updates it
    stores them in db.
    """
    def handle(self, *args, **options):
        print("PULLING LATEST ECB RATES")
        fetch_and_store_latest_ecb_exrates()
