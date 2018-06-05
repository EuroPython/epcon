# -*- coding: UTF-8 -*-

from __future__ import print_function

from django.core.management.base import BaseCommand

from conference.exchangerates import (
    SUPPORTED_CURRENCIES,
    check_for_exrates_updates
)


class Command(BaseCommand):
    """
    Checks ECB API endpoint for the new exrates, if there are any updates it
    stores them in db.
    """
    def handle(self, *args, **options):
        for currency in SUPPORTED_CURRENCIES:
            check_for_exrates_updates(currency)
