# -*- coding: utf-8 -*-



from django.core.management.base import BaseCommand

from conference.invoicing import (
    Invoice,
    VAT_NOT_AVAILABLE_PLACEHOLDER,
    upgrade_invoice_placeholder_to_real_invoice
)


def generate_invoices_from_placeholders_for_year(year):
    print("====== making real invoices from polaceholders =======")
    invoices = Invoice.objects.filter(emit_date__year=year,
                                      html=VAT_NOT_AVAILABLE_PLACEHOLDER)
    total = invoices.count()

    print("Found %s placeholder invoices for %s" % (total, year))
    for i, invoice in enumerate(invoices, 1):
        invoice = upgrade_invoice_placeholder_to_real_invoice(invoice)
        print('Replaced %d out of %d - %s' % (i, total, invoice.code))


class Command(BaseCommand):
    """
    In 2018 we needed to generate the placeholder invoices because of missing
    VAT ID when we started the ticket sales.

    This function goes through all of the invoices that are marked as
    placeholders (based on their content) and then generates proper,
    non-placeholder invoice and saves it inplace.
    """
    def handle(self, *args, **options):
        generate_invoices_from_placeholders_for_year(2018)
