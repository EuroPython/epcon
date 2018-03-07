# coding: utf-8

"""
------------------------------------------------------------------------------
THIS WHOLE MODULE ASSUMES WE'RE BASING EVERYTHING IN EUROS,
AND CONVERT EITHER TO OR FROM EUROS. KEEP THAT IN MIND.
------------------------------------------------------------------------------

This module handles ECB exchange rates which we sometimes need for invoices.

Starting in 2018, with EuroPython in Edinburgh, we need to include VAT in local
currency (GBP), to do that we can use ECB published exchange rates available at
this URL
    -> https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml

The way it works is this xml shows latest (published every day at 1600 CET) ECB
exchange rates.

What we're going to do is take that XML, parse it, and then cache the results
for 24 hours, because we're just interested in using latest value (if we need
historical values we can get full XML since 1999 here:

    https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml
    or as CSV
    https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip

------------------------------------------------------------------------------
THIS WHOLE MODULE ASSUMES WE'RE BASING EVERYTHING IN EUROS,
AND CONVERT EITHER TO OR FROM EUROS. KEEP THAT IN MIND.
------------------------------------------------------------------------------
"""

from __future__ import unicode_literals, absolute_import, print_function

from datetime import datetime
from decimal import Decimal

from django.core.cache import cache

import requests
from lxml import etree as ET


DAILY_ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
CURRENCY_CACHE_KEY = 'currency_xrates'
CURRENCY_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

# we probably can assume rounding to 0.01 for most of the currencie we're going
# to ever use.
DEFAULT_DECIMAL_PLACES = Decimal('0.01')

# The actual XML will have more currencies.
EXAMPLE_ECB_DAILY_XML = """
<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
    xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
    <gesmes:subject>Reference rates</gesmes:subject>
    <gesmes:Sender>
        <gesmes:name>European Central Bank</gesmes:name>
    </gesmes:Sender>
    <Cube>
        <Cube time="2018-03-06">
            <Cube currency="USD" rate="1.2411"/>
            <Cube currency="JPY" rate="131.84"/>
            <Cube currency="GBP" rate="0.89165"/>
        </Cube>
    </Cube>
</gesmes:Envelope>
""".strip()


def fetch_latest_ecb_exrates():
    """
    Example of the XML (see EXAMPLE_XML constant)
    """
    response = requests.get(DAILY_ECB_URL)
    info = ET.fromstring(response.content)[2][0]
    datestamp = datetime.strptime(info.attrib['time'], "%Y-%m-%d").date()
    rates = [x.attrib for x in info]

    return dict(
        datestamp=datestamp,
        **{x['currency']: Decimal(x['rate']) for x in rates}
    )


def get_ecb_rates_for_currency(currency):
    """
    IMPORATANT: This returns latest copy it has from cache OR if cache is
    invalid (or nonexistent) it will fetch new data via
    fetch_latest_ecb_exrates()

    Then it returns tuple with the datestamp and Decimal value of conversion
    rate.
    """
    cached = cache.get(CURRENCY_CACHE_KEY)
    if cached:
        exrates = cached
    else:
        exrates = fetch_latest_ecb_exrates()
        cache.set(CURRENCY_CACHE_KEY, exrates, CURRENCY_CACHE_TIMEOUT)

    return (exrates['datestamp'], exrates[currency])


def convert_from_EUR_using_latest_exrates(amount_in_eur, to_currency):
    assert isinstance(amount_in_eur, Decimal)

    datestamp, exrate = get_ecb_rates_for_currency(to_currency)
    new_amount = (amount_in_eur * exrate).quantize(DEFAULT_DECIMAL_PLACES)

    return {
        'converted': new_amount,
        'using_exrate_date': datestamp,
        'exrate': exrate
    }
