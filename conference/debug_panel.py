# coding: utf-8

"""
Things in this file are related to a special debug panel that helps us debug
things in production.
"""
import csv
import datetime
import platform
import subprocess

import django
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template.response import TemplateResponse

from common.http import PdfResponse


from conference.invoicing import (
    Invoice,
    VAT_NOT_AVAILABLE_PLACEHOLDER,
    render_invoice_as_html
)


def get_current_commit_hash():
    command = 'git rev-parse HEAD'
    process = subprocess.Popen(
        command.split(), stdout=subprocess.PIPE, cwd=settings.PROJECT_DIR
    )
    full_hash = process.communicate()[0]
    return "%s %s" % (full_hash[:8], full_hash)


commit_hash_in_current_process = get_current_commit_hash()


@staff_member_required
def debug_panel_invoice_placeholders(request):
    """
    In 2018 we needed to start the ticket sales before we could issue full
    legal invoices (because of missing VAT ID), so instead we created the
    Invoice instances with placeholder value, the idea being we can later
    'upgrade' them to proper invoices.

    This view allows us to see how many invoices are still placeholders and
    then check the previews of how would they look like when issued.
    """
    placeholders = Invoice.objects.filter(html=VAT_NOT_AVAILABLE_PLACEHOLDER)
    return TemplateResponse(
        request, "conference/debugpanel/invoice_placeholders.html", {
            'placeholders': placeholders
        }
    )


@staff_member_required
def debug_panel_invoice_force_preview(request, invoice_id):
    invoice = Invoice.objects.get(id=invoice_id)
    return PdfResponse(filename=invoice.get_invoice_filename(),
                       content=render_invoice_as_html(invoice))


@staff_member_required
def debug_panel_index(request):

    debug_vars = [
        ('Current_Commit_Hash', get_current_commit_hash()),
        ('Commit_Hash_in_current_process', commit_hash_in_current_process),
        ('Django_Version',      django.VERSION),
        ('Python_Version',      platform.python_version()),
    ]

    allowed_settings = [
        'ADMINS',
        'DATA_DIR',
        'PROJECT_DIR',
        'DEFAULT_FROM_EMAIL',
        'SERVER_EMAIL',
    ]

    for setting_name in allowed_settings:
        debug_vars.append(
            (setting_name, getattr(settings, setting_name))
        )

    return TemplateResponse(request, "conference/debugpanel/index.html", {
        'debug_vars': debug_vars
    })


# business functions
def export_account_invoices(start_date, end_date=None):
    if end_date is None:
        end_date = datetime.date.today()

    invoices = Invoice.objects.filter(emit_date__range=(start_date, end_date))
    for invoice in invoices:
        yield invoice


def export_account_invoices_to_csv(fp, start_date, end_date=None):
    writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
    for invoice in export_account_invoices(start_date, end_date):
        user = invoice.order.user.user
        result = [
            invoice.code,
            invoice.emit_date,
            invoice.order.user.user.get_full_name(),
            invoice.order.address,
            invoice.order.country.name,
            invoice.order.vat_number,
            invoice.price,
            invoice.vat_in_local_currency,
            invoice.total,
        ]
        writer.writerow(result)


@staff_member_required
def debug_panel_invoice_export(request):
    # import pdb; pdb.set_trace()
    start_date_param = request.GET.get('start_date')
    if start_date_param is None:
        start_date = datetime.date(2018, 1, 1)
    else:
        start_date = datetime.datetime.strptime(start_date_param, '%Y-%m-%d')

    end_date_param = request.GET.get('end_date')
    if end_date_param is None:
        end_date = datetime.date(2018, 1, 1)
    else:
        end_date = datetime.datetime.strptime(end_date_param, '%Y-%m-%d')

    invoices = export_account_invoices(start_date, end_date)

    return render(request, 'conference/debugpanel/invoices_export.html',
                  {'invoices': invoices,
                   'start_date': start_date,
                   'end_date': end_date})


@staff_member_required
def debug_panel_invoice_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="export-invoices.csv"'

    start_date_param = request.GET.get('start_date')
    if start_date_param is None:
        start_date = datetime.date(2018, 1, 1)
    else:
        start_date = datetime.datetime.strptime(start_date_param, '%Y-%m-%d')

    end_date_param = request.GET.get('end_date')
    if end_date_param is None:
        end_date = datetime.date(2018, 1, 1)
    else:
        end_date = datetime.datetime.strptime(end_date_param, '%Y-%m-%d')

    export_account_invoices_to_csv(response, start_date, end_date)

    return response
