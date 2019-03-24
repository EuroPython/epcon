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

What we're going to do is take that XML, parse it, and then store the result in
DB for later, but we're mostly interested in using latest value (if we need
historical values we can get full XML since 1999 here:

    https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml
    or as CSV
    https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip

------------------------------------------------------------------------------
THIS WHOLE MODULE ASSUMES WE'RE BASING EVERYTHING IN EUROS,
AND CONVERT EITHER TO OR FROM EUROS. KEEP THAT IN MIND.
------------------------------------------------------------------------------
"""

from datetime import datetime, date
from decimal import Decimal

import requests
from lxml import etree as ET

from conference.models import ExchangeRate


HTTP_SUCCESS = 200
DAILY_ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

# we probably can assume rounding to 0.01 for most of the currencie we're going
# to ever use.
DEFAULT_DECIMAL_PLACES = Decimal('0.01')

# The actual XML will have more currencies.
EXAMPLE_ECB_DATE = date(2018, 3, 6)
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
            <Cube currency="CHF" rate="1.15372"/>
        </Cube>
    </Cube>
</gesmes:Envelope>
""".strip()

SUPPORTED_CURRENCIES = ["GBP", "CHF"]


class CurrencyNotSupported(Exception):
    pass


def normalize_price(price):
    return price.quantize(Decimal(DEFAULT_DECIMAL_PLACES))


def fetch_and_store_latest_ecb_exrates():
    """
    Example of the XML (see EXAMPLE_XML constant)
    """
    response = requests.get(DAILY_ECB_URL)
    # Raise exception if status_code != 200 or ConnectionError
    response.raise_for_status()
    info = ET.fromstring(response.content)[2][0]
    datestamp = datetime.strptime(info.attrib['time'], "%Y-%m-%d").date()
    rates = [x.attrib for x in info]

    exrates = []
    for item in rates:
        if item['currency'] in SUPPORTED_CURRENCIES:
            exrate, created = ExchangeRate.objects.update_or_create(
                datestamp=datestamp,
                currency=item['currency'],
                defaults={'rate': Decimal(item['rate'])}
            )
            exrates.append(exrate)
            print(exrate, "NEW EXRATE!" if created else "<noupdate>")

    return exrates


def get_latest_ecb_rates_from_db(currency):
    # if there are no ExchangeRates cached, this is going to raise
    # DoesNotExist; and we're going to assume there is at least one
    # ExchangeRate for that currency in the database.
    exrate = ExchangeRate.objects.filter(currency=currency).latest('datestamp')
    return {
        'datestamp': exrate.datestamp,
        exrate.currency: exrate.rate
    }


def get_ecb_rates_for_currency(currency):
    """
    Returns tuple with the datestamp and Decimal value of conversion rate.
    """
    # UPDATE 2018-06-05 -- read directly from the database, and skip caching
    if currency not in SUPPORTED_CURRENCIES:
        raise CurrencyNotSupported("Currently we don't support %s" % currency)
    exrates = get_latest_ecb_rates_from_db(currency)
    return (exrates['datestamp'], exrates[currency])


def convert_from_EUR_using_latest_exrates(amount_in_eur, to_currency):
    assert isinstance(amount_in_eur, Decimal)

    datestamp, exrate = get_ecb_rates_for_currency(to_currency)
    new_amount = normalize_price(amount_in_eur * exrate)

    return {
        'converted': new_amount,
        'using_exrate_date': datestamp,
        'exrate': exrate
    }
