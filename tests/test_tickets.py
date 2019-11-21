from datetime import date

import responses
from freezegun import freeze_time
from pytest import mark

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone

from assopy.models import Vat, Order, Country, Refund, Invoice
from conference.fares import (
    pre_create_typical_fares_for_conference,
    set_early_bird_fare_dates,
    set_regular_fare_dates,
    SOCIAL_EVENT_FARE_CODE
)
from conference.currencies import (
    DAILY_ECB_URL,
    EXAMPLE_ECB_DAILY_XML,
    fetch_and_store_latest_ecb_exrates,
)
from conference.models import Conference, Fare, Ticket
from p3.models import TicketConference
from email_template.models import Email

from tests.common_tools import make_user


DEFAULT_VAT_RATE = "7.7"  # 7.7%

# TODO - this should be defined somewhere around the models.
DEFAULT_SHIRT_SIZE        = None
DEFAULT_DIET              = None
DEFAULT_PYTHON_EXPERIENCE = 0


def make_basic_fare_setup():
    assert Fare.objects.all().count() == 0

    Conference.objects.get_or_create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_NAME,
        # using 2018 dates
        # those dates are required for Tickets to work.
        # (for setting up/rendering attendance days)
        conference_start=date(2018, 7, 23),
        conference_end=date(2018, 7, 29),
    )
    default_vat_rate, _ = Vat.objects.get_or_create(value=DEFAULT_VAT_RATE)
    pre_create_typical_fares_for_conference(
        settings.CONFERENCE_CONFERENCE, default_vat_rate
    )

    # Using some totally random dates just to test early vs regular in cart
    set_early_bird_fare_dates(
        settings.CONFERENCE_CONFERENCE, date(2018, 3, 10), date(2018, 3, 12)
    )

    set_regular_fare_dates(
        settings.CONFERENCE_CONFERENCE, date(2018, 3, 20), date(2018, 6, 30)
    )

    SOCIAL = Fare.objects.get(code=SOCIAL_EVENT_FARE_CODE)
    SOCIAL.start_validity = date(2018, 6, 20)
    SOCIAL.end_validity = date(2018, 7, 30)
    SOCIAL.save()
    assert Fare.objects.all().count() == 28  # 3**3 + social event


# Same story as previously - using TestCase beacuse of django's asserts like
# assertRedirect even though it's run via pytest
class TestBuyingTickets(TestCase):

    def setUp(self):
        self.user = make_user()
        make_basic_fare_setup()
        with responses.RequestsMock() as rsps:
            # mocking responses for the invoice VAT exchange rate feature
            rsps.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
            fetch_and_store_latest_ecb_exrates()
