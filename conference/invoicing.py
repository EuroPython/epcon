# coding: utf-8

"""
This module handles all things related to creating a new invoice, including

* keeping track of when they were issued
* making sure they have unique and correct invoice numbers
* keeping track who was the issuer of the invoice (changes form year to year)
* stroing full copy in the Invoice model to be viewed later.
* rendering PDFs of the invoice.
"""


from __future__ import unicode_literals, absolute_import

from collections import OrderedDict
from decimal import Decimal
import datetime

import unicodecsv as csv

from django.template.loader import render_to_string
from django.db.models import Max
from django.db import transaction

from assopy.models import Invoice, Order

from conference.currencies import (
    convert_from_EUR_using_latest_exrates,
    normalize_price
)


ACPYSS_16 = """
Asociación de Ciencias de la Programación Python San Sebastian (ACPySS)
P° Manuel Lardizabal 1, Oficina 307-20018 Donostia (Spain)
VAT-ID ESG75119511
Tel/Phone (+34) 943.01.80.47 | (+34) 688.64.52.32
Email: info@pyss.org
""".strip()

PYTHON_ITALIA_17 = """
Python Italia APS
Via Mugellese, 1/A
50013 Campi Bisenzio (FI)
Italy
VAT-ID: IT05753460483
Codice Fiscale: 94144670489
Contact Email: info@python.it
""".strip()

EPS_18 = """
EuroPython Society
c/o Open End AB
Norra Ågatan 10
41664  Göteborg
Sweden
EU VAT-ID: SE802417770401
Contact Email: billing@europython.eu
https://www.europython-society.org
""".strip()


ISSUER_BY_YEAR = {
    2016: ACPYSS_16,
    2017: PYTHON_ITALIA_17,
    2018: EPS_18,
}

LOCAL_CURRENCY_BY_YEAR = {
    # Used for local VAT calculations if required by local law.
    2016: "EUR",
    2017: "EUR",
    2018: "GBP",
}

EP_CITY_FOR_YEAR = {
    2016: "Bilbao",
    2017: "Rimini",
    2018: "Edinburgh",
}

ADDITIONAL_TEXT_FOR_YEAR = {
    2016: "",
    2017: "",
    2018: "assopy/invoices/_additional_text_for_2018.html",
}

REAL_INVOICE_PREFIX = "I/"
FAKE_INVOICE_PREFIX = "F/"   # pro forma(?)

invoice_code_templates = {
    REAL_INVOICE_PREFIX: "I/%(year_two_digits)s.%(sequential_id)s",
    FAKE_INVOICE_PREFIX: "F/%(year_two_digits)s.%(sequential_id)s",
}

VAT_NOT_AVAILABLE_PLACEHOLDER = """
VAT invoices will be generated as soon as we have been issued a VAT ID.
Please stay tuned.
""".strip()

# NOTE(artcz)(2018-06-26) – This is a global setting that decides whether we
# issue placeholders (basically Invoice is normal but it's html is equal to
# VAT_NOT_AVAILABLE_PLACEHOLDER – or regular invoice with a proper template.
FORCE_PLACEHOLDER = False


def is_real_invoice_code(invoice_code):
    return invoice_code.startswith(REAL_INVOICE_PREFIX)


def increment_invoice_code(code):
    NUMBER_OF_DIGITS_WITH_PADDING = 4

    prefix_with_year, number = code.split('.')
    number = str(int(number) + 1).zfill(NUMBER_OF_DIGITS_WITH_PADDING)
    return "{}.{}".format(prefix_with_year, number)


def latest_invoice_code_for_year(prefix, year):
    """
    returns latest used invoice.code in a given year.
    rtype – string or None
    """
    assert 2016 <= year <= 2020, year
    assert prefix in [REAL_INVOICE_PREFIX, FAKE_INVOICE_PREFIX]

    invoices = Invoice.objects.filter(
        code__startswith=prefix,
        emit_date__year=year,
    )

    return invoices.aggregate(max=Max('code'))['max']


def next_invoice_code_for_year(prefix, year):
    assert 2016 <= year <= 2020, year
    assert prefix in [REAL_INVOICE_PREFIX, FAKE_INVOICE_PREFIX]

    current_code = latest_invoice_code_for_year(prefix, year)
    if current_code:
        next_code = increment_invoice_code(current_code)
        return next_code

    # if there are no current codes, return the first one
    template = invoice_code_templates[prefix]
    return template % {'year_two_digits': year % 1000, 'sequential_id': '0001'}


def extract_customer_info(order):
    assert isinstance(order, Order)

    customer = []
    customer.append(order.card_name)
    customer.append(order.address)
    if order.cf_code:
        customer.append(order.cf_code)
    if order.vat_number:
        customer.append(order.vat_number)
    if order.billing_notes:
        customer.append(order.billing_notes)

    return '\n'.join(customer)


def create_invoices_for_order(order, force_placeholder=False):
    assert isinstance(order, Order)

    payment_date = order.payment_date
    emit_date = payment_date if payment_date else order.created
    prefix = REAL_INVOICE_PREFIX if payment_date else FAKE_INVOICE_PREFIX

    # First transaction takes care of "create all invoices or nothing"
    # Making it more reliable and threadsafe
    with transaction.atomic():

        invoices = []
        for vat_item in order.vat_list():
            # Second, nested, transaction is here because otherwise getting new
            # invoice_code wouldn't work with database fetch, we would need to
            # increment it manually. (hence another transaction per item)
            with transaction.atomic():

                code = next_invoice_code_for_year(
                    prefix=prefix,
                    year=emit_date.year
                )

                gross_price = vat_item['price']
                vat_rate    = normalize_price(1 + vat_item['vat'].value / 100)
                net_price   = normalize_price(vat_item['price'] / vat_rate)
                vat_price   = vat_item['price'] - net_price

                currency = LOCAL_CURRENCY_BY_YEAR[emit_date.year]
                if currency != 'EUR':
                    conversion = convert_from_EUR_using_latest_exrates(
                        vat_price, currency
                    )
                else:
                    conversion = {
                        'currency': 'EUR',
                        'converted': vat_price,
                        'exrate': Decimal('1.0'),
                        'using_exrate_date': emit_date,
                    }

                customer = extract_customer_info(order)

                invoice, _ = Invoice.objects.update_or_create(
                    order=order,
                    code=code,
                    defaults={
                        'issuer':         ISSUER_BY_YEAR[emit_date.year],
                        'customer':       customer,
                        'vat':            vat_item['vat'],
                        'price':          gross_price,
                        'payment_date':   payment_date,
                        'emit_date':      emit_date,
                        'local_currency': currency,
                        'vat_in_local_currency': conversion['converted'],
                        'exchange_rate':  conversion['exrate'],
                        'exchange_rate_date': conversion['using_exrate_date'],
                    }
                )

                if force_placeholder:
                    invoice.html = VAT_NOT_AVAILABLE_PLACEHOLDER
                else:
                    invoice.html = render_invoice_as_html(invoice)

                invoice.save()

                assert invoice.net_price() == net_price
                assert invoice.vat_value() == vat_price

                invoices.append(invoice)

    return invoices


def upgrade_invoice_placeholder_to_real_invoice(invoice):
    invoice.issuer = ISSUER_BY_YEAR[invoice.emit_date.year]
    invoice.html = render_invoice_as_html(invoice)
    invoice.save()
    return invoice


def render_invoice_as_html(invoice):
    assert isinstance(invoice, Invoice)

    items = invoice.invoice_items()
    for item in items:
        item['net_price'] = normalize_price(
            item['price'] / (1 + invoice.vat.value / 100)
        )

    # TODO this is copied as-is from assopy/views.py, but can be simplified
    # TODO: also if there are any images included in the invoice make sure to
    # base64 them.

    order = invoice.order
    address = '%s, %s' % (order.address, unicode(order.country))
    # TODO: why, instead of passing invoice objects, it explicitly passes
    # every attribute?
    ctx = {
        # TODO: get it from Conference instance
        'conference_name': "EuroPython 2018",
        "conference_location": EP_CITY_FOR_YEAR[invoice.emit_date.year],
        "bank_info": "",
        "currency": invoice.local_currency,
        'document': ('Fattura N.', 'Invoice N.'),
        'title': unicode(invoice),
        'code': invoice.code,
        'emit_date': invoice.emit_date,
        # TODO: possibly we need to stare it as separate date
        'time_of_supply': invoice.payment_date,
        'order': {
            'card_name': order.card_name,
            'address': address,
            'billing_notes': order.billing_notes,
            'cf_code': order.cf_code,
            'vat_number': order.vat_number,
        },
        'items': items,
        'note': invoice.note,
        'price': {
            'net': invoice.net_price(),
            'vat': invoice.vat_value(),
            'total': invoice.price,
        },
        'vat': invoice.vat,
        'is_real_invoice': is_real_invoice_code(invoice.code),
        "issuer": invoice.issuer,
        "invoice": invoice,
        "additional_text": ADDITIONAL_TEXT_FOR_YEAR[invoice.emit_date.year]
    }

    return render_to_string('assopy/invoice.html', ctx)


CSV_2018_REPORT_COLUMNS = [
    'ID',
    'Emit Date',
    'Buyer Name',
    'Business Name',
    'Address',
    'Country',
    'VAT ID',
    'Net Price in GBP',
    'VAT in GBP',
    'Gross Price in GBP',
]


def export_invoices_to_2018_tax_report(start_date, end_date=None):
    if end_date is None:
        end_date = datetime.date.today()

    invoices = Invoice.objects.filter(
        emit_date__range=(start_date, end_date),
    )
    for invoice in invoices:
        # Building it that way because of possible holes in the data (like in
        # the case of the country)
        output = OrderedDict()
        output["ID"] = invoice.code
        output['Emit Date']     = invoice.emit_date.strftime("%Y-%m-%d")
        # This may be wrong if we assign ticket to another attendee
        output['Buyer Name'] = invoice.order.user.user.get_full_name()
        output['Business Name'] = invoice.order.card_name
        output['Address']       = invoice.order.address
        try:
            output['Country']   = invoice.order.country.name
        except AttributeError:
            # If country is None, then .name would cause AttributeError
            output['Country']   = ""

        output['VAT ID']        = invoice.order.vat_number
        output['Net Price in %s' % invoice.local_currency] =\
            invoice.net_price_in_local_currency
        output['VAT in %s' % invoice.local_currency] =\
            invoice.vat_in_local_currency
        output['Gross Price in %s' % invoice.local_currency] =\
            invoice.price_in_local_currency

        yield invoice, output


def export_invoices_to_2018_tax_report_csv(fp, start_date, end_date=None):
    writer = csv.DictWriter(fp, CSV_2018_REPORT_COLUMNS, quoting=csv.QUOTE_ALL)
    writer.writeheader()

    for invoice, to_export in export_invoices_to_2018_tax_report(
        start_date, end_date
    ):
        writer.writerow(to_export)


def export_invoices_for_payment_reconciliation(start_date, end_date=None):
    if end_date is None:
        end_date = datetime.date.today()

    invoices = Invoice.objects.filter(
        emit_date__range=(start_date, end_date),
    )
    for invoice in invoices:
        # Building it that way because of possible holes in the data (like in
        # the case of the country)
        output = {
            'ID': invoice.code,
            'net': str(invoice.net_price()),
            'vat': str(invoice.vat_value()),
            'gross': str(invoice.price),
            'order': invoice.order.code,
            'stripe': invoice.order.stripe_charge_id,
        }

        yield output
