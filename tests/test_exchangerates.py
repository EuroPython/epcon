# coding: utf-8



from datetime import date
from decimal import Decimal

from pytest import mark, raises
import responses

from tests.common_tools import clear_all_the_caches

from conference.currencies import (
    DAILY_ECB_URL,
    EXAMPLE_ECB_DAILY_XML,
    CurrencyNotSupported,
    ExchangeRate,
    get_ecb_rates_for_currency,
    convert_from_EUR_using_latest_exrates,
    fetch_and_store_latest_ecb_exrates,
)


@responses.activate
@mark.django_db
def test_exchange_rates_are_working():
    """
    https://github.com/EuroPython/epcon/issues/617
    """
    # by default responses raises ConnectionError, so before we set up any
    # responses it's good to test how the code behaves when there is no
    # connection.
    with raises(ExchangeRate.DoesNotExist):
        get_ecb_rates_for_currency("GBP")
    assert len(responses.calls) == 0

    # This step will store new value in cache and in db
    clear_all_the_caches()
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    fetch_and_store_latest_ecb_exrates()
    assert len(responses.calls) == 1

    assert get_ecb_rates_for_currency("GBP") == (
        # date is used in example xml, so it will be returned here as well
        date(2018, 3, 6), Decimal('0.89165')
    )
    assert len(responses.calls) == 1   # no additional calls to API

    with raises(CurrencyNotSupported):
        get_ecb_rates_for_currency("JPY")
    assert len(responses.calls) == 1

    a = convert_from_EUR_using_latest_exrates(Decimal("10"), "GBP")
    b = {'converted': Decimal('8.92'),
         'using_exrate_date': date(2018, 3, 6),
         'exrate': Decimal('0.89165')}
    assert a == b
    assert len(responses.calls) == 1   # no additional calls to API
