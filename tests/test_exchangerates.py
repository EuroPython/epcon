# coding: utf-8

from __future__ import unicode_literals, absolute_import

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.test.utils import override_settings

from pytest import mark, raises
import responses

from tests.common_tools import clear_all_the_caches

from conference.exchangerates import (
    DAILY_ECB_URL,
    EXAMPLE_ECB_DAILY_XML,
    ExchangeRate,
    get_ecb_rates_for_currency,
    convert_from_EUR_using_latest_exrates
)


@responses.activate
@mark.django_db
# in this test we want to check if values are cached correctly...
@override_settings(CACHES=settings.ENABLE_LOCMEM_CACHE)
def test_exchange_rates_are_working():
    """
    https://github.com/EuroPython/epcon/issues/617
    """
    # just in case because we relay on cache behaviour in this test
    clear_all_the_caches()

    # by default responses raises ConnectionError, so before we set up any
    # responses it's good to test how the code behaves when there is no
    # connection.
    with raises(ExchangeRate.DoesNotExist):
        assert get_ecb_rates_for_currency("GBP")
        assert len(responses.calls) == 1

    # This step will store new value in cache and in db
    clear_all_the_caches()
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    assert get_ecb_rates_for_currency("GBP") == (
        # date is used in example xml, so it will be reutrned here as well
        date(2018, 3, 6), Decimal('0.89165')
    )
    assert len(responses.calls) == 2

    # second call will use cache instead of calling URL so the responses are
    # still at 2.
    assert get_ecb_rates_for_currency("JPY") == (
        date(2018, 3, 6), Decimal('131.84')
    )
    assert len(responses.calls) == 2

    # So then when we clear the cache, and cause an error we should get a
    # response back from db, so the responses are at 3, but the output is
    # correct
    clear_all_the_caches()
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML,
                  status=500)
    assert get_ecb_rates_for_currency("GBP") == (
        # date is used in example xml, so it will be reutrned here as well
        date(2018, 3, 6), Decimal('0.89165')
    )
    assert len(responses.calls) == 3

    # and same for 404
    clear_all_the_caches()
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML,
                  status=404)
    assert get_ecb_rates_for_currency("GBP") == (
        # date is used in example xml, so it will be reutrned here as well
        date(2018, 3, 6), Decimal('0.89165')
    )
    assert len(responses.calls) == 4

    a = convert_from_EUR_using_latest_exrates(Decimal("10"), "GBP")
    b = {'converted': Decimal('8.92'),
         'using_exrate_date': date(2018, 3, 6),
         'exrate': Decimal('0.89165')}
    assert a == b
