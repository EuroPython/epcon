# coding: utf-8

from __future__ import unicode_literals, absolute_import

from django.template.loader import render_to_string

from assopy.settings import IS_REAL_INVOICE


ISSUER_BY_YEAR = {
    2016: "Bilbao FIXME",
    2017: "Rimini FIXME",
    2018: "Edinburgh FIXME",
}


def render_invoice_as_html(invoice):

    # TODO this is copied as-is from assopy/views.py, but can be simplified
    # TODO: also if there are any images included in the invoice make sure to
    # base64 them.

    order = invoice.order
    address = '%s, %s' % (order.address, unicode(order.country))
    # TODO: why, instead of passing invoice objects, it explicitly passes
    # every attribute?
    ctx = {
        'document': ('Fattura N.', 'Invoice N.'),
        'title': unicode(invoice),
        'code': invoice.code,
        'emit_date': invoice.emit_date,
        'order': {
            'card_name': order.card_name,
            'address': address,
            'billing_notes': order.billing_notes,
            'cf_code': order.cf_code,
            'vat_number': order.vat_number,
        },
        'items': invoice.invoice_items(),
        'note': invoice.note,
        'price': {
            'net': invoice.net_price(),
            'vat': invoice.vat_value(),
            'total': invoice.price,
        },
        'vat': invoice.vat,
        'real': IS_REAL_INVOICE(invoice.code),
        "issuer": invoice.issuer,
    }

    return render_to_string('assopy/invoice.html', ctx)
