

"""
Things in this file are related to a special debug panel that helps us debug
things in production.
"""
import datetime
import platform
import subprocess

import django
from django.conf.urls import url
from django import forms
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.shortcuts import redirect

from common.http import PdfResponse
from conference.invoicing import (
    Invoice,
    ADDITIONAL_TEXT_FOR_YEAR,
    VAT_NOT_AVAILABLE_PLACEHOLDER,
    EP_CITY_FOR_YEAR,
    LOCAL_CURRENCY_BY_YEAR,
    ISSUER_BY_YEAR,
    REAL_INVOICE_PREFIX,
    next_invoice_code_for_year,
    render_invoice_as_html,
    export_invoices_to_tax_report,
    export_invoices_to_tax_report_csv,
    export_invoices_for_payment_reconciliation,
    extract_customer_info,
)
from conference.models import Fare, Conference
from conference.fares import (
    set_early_bird_fare_dates,
    set_regular_fare_dates,
)
from conference.tickets import sold_training_tickets_including_combined_tickets


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
        ('Conference_current',  Conference.objects.current()),
        ('SOLD_TRAINING_TICKETS',
         sold_training_tickets_including_combined_tickets(
             conference_code=settings.CONFERENCE_CONFERENCE,
         ).count()),
    ]

    allowed_settings = [
        'ADMINS',
        'DATA_DIR',
        'PROJECT_DIR',
        'DEFAULT_FROM_EMAIL',
        'SERVER_EMAIL',
        'CONFERENCE_CONFERENCE',
    ]

    for setting_name in allowed_settings:
        debug_vars.append(
            (setting_name, getattr(settings, setting_name))
        )

    return TemplateResponse(request, "conference/debugpanel/index.html", {
        'debug_vars': debug_vars
    })


def get_start_end_dates(request):
    DEFAULT_START_DATE = datetime.date(2018, 1, 1)
    DEFAULT_END_DATE   = datetime.date.today()

    start_date_param = request.GET.get('start_date')
    if start_date_param is None:
        start_date = DEFAULT_START_DATE
    else:
        start_date = datetime.datetime.strptime(start_date_param, '%Y-%m-%d')

    end_date_param = request.GET.get('end_date')
    if end_date_param is None:
        end_date = DEFAULT_END_DATE
    else:
        end_date = datetime.datetime.strptime(end_date_param, '%Y-%m-%d')

    return start_date, end_date


@staff_member_required
def debug_panel_invoice_example(request):
    """
    This view is used to render an example of the invoice based on current
    settings. (in PDF)
    """

    conference = Conference.objects.current()
    ctx = {
        'conference_name': conference.name,
        "conference_location": EP_CITY_FOR_YEAR[datetime.date.today().year],
        "bank_info": "",
        "currency": LOCAL_CURRENCY_BY_YEAR[datetime.date.today().year],
        'title': "#I/19.12345",
        'code': "#I/19.12345",
        'conference_start': conference.conference_start,
        'conference_end': conference.conference_end,
        'emit_date': datetime.date.today(),
        # TODO: possibly we need to stare it as separate date
        'time_of_supply': datetime.date.today(),
        'order': {
            'card_name': "Joe Doe",
            'address': "Neverland 123",
            'billing_notes': "Billing notes",
            'cf_code': "CF code",
            'vat_number': "EU 123 45 67 89",
        },
        'items': [
            {
                'code': 'TESP',
                'description': "Description",
                'count': 2,
                'value': 220,
                'net_price': 200,
            }
        ],
        # 'note': "A note",
        'price': {'net': "100", 'vat': "120", 'total': "120"},
        'vat': {'value': '10'},
        'is_real_invoice': True,
        "issuer": ISSUER_BY_YEAR[datetime.date.today().year],
        "invoice": None,
        "additional_text": ADDITIONAL_TEXT_FOR_YEAR[
            datetime.date.today().year
        ],
    }

    return PdfResponse(
        filename="Testinovoice.pdf",
        content=render_to_string('assopy/invoice.html', ctx)
    )


@staff_member_required
def debug_panel_invoice_export_for_tax_report(request):
    start_date, end_date = get_start_end_dates(request)
    invoices_and_exported = export_invoices_to_tax_report(
        start_date, end_date
    )

    return TemplateResponse(
        request, 'conference/debugpanel/invoices_export.html', {
            'invoices_and_exported': invoices_and_exported,
            'start_date': start_date,
            'end_date': end_date
        }
    )


@staff_member_required
def debug_panel_invoice_export_for_tax_report_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] =\
        'attachment; filename="export-invoices.csv"'

    start_date, end_date = get_start_end_dates(request)
    export_invoices_to_tax_report_csv(response, start_date, end_date)

    return response


@staff_member_required
def debug_panel_invoice_export_for_payment_reconciliation_json(request):
    start_date, end_date = get_start_end_dates(request)
    response = JsonResponse({
        # list() to flatten the generator – otherwise it's not serilizable
        'invoices': list(export_invoices_for_payment_reconciliation(
            start_date, end_date
        ))
    })
    response['Content-Disposition'] =\
        'attachment; filename="export-invoices.json"'

    # TODO: this json maybe big, maybe we could use StreamingHttpResponse?
    return response


@staff_member_required
def reissue_invoice(request, invoice_id):
    """
    Displays form that can issue another invoice based on previous one.
    Pre-fills the form with old invoice data.
    """
    old_invoice = Invoice.objects.get(pk=invoice_id)

    class ReissueInvoiceForm(forms.ModelForm):
        """
        TODO: this is a temporary location for the prototype. Move it somewhere
        else later.
        """

        class Meta:
            model = Invoice
            fields = ['emit_date', 'customer']

    if request.method == 'POST':
        form = ReissueInvoiceForm(data=request.POST)
        if form.is_valid():
            new_code = next_invoice_code_for_year(
                REAL_INVOICE_PREFIX,
                old_invoice.emit_date.year
            )

            new_invoice = Invoice(
                order=old_invoice.order,
                code=new_code,
                emit_date=form.cleaned_data['emit_date'],
                payment_date=old_invoice.payment_date,
                price=old_invoice.price,
                issuer=old_invoice.issuer,
                customer=form.cleaned_data['customer'],
                local_currency=old_invoice.local_currency,
                vat_in_local_currency=old_invoice.vat_in_local_currency,
                exchange_rate=old_invoice.exchange_rate,
                exchange_rate_date=old_invoice.exchange_rate_date,
                vat=old_invoice.vat
            )

            new_invoice.html = render_invoice_as_html(new_invoice)
            new_invoice.save()

            return redirect('debug_panel:invoice_export_for_tax_report')
    else:
        customer = (
            old_invoice.customer
            or extract_customer_info(old_invoice.order)
        )
        form = ReissueInvoiceForm(initial={
            'customer': customer,
            'emit_date': old_invoice.emit_date,
        })

    return TemplateResponse(
        request,
        'conference/debugpanel/reissue_invoice.html',
        {'form': form, 'old_invoice': old_invoice}
    )


@staff_member_required
def debugpanel_fares_setup(request):
    fares = Fare.objects.all()
    conference = Conference.objects.current()

    eb_setup_form = SetDatesForm()
    regular_setup_form = SetDatesForm()

    if request.method == 'POST':
        if FareSetup.set_eb_dates in request.POST:
            eb_setup_form = SetDatesForm(data=request.POST)
            if eb_setup_form.is_valid():
                set_early_bird_fare_dates(
                    conference=conference,
                    start_date=eb_setup_form.cleaned_data['start_date'],
                    end_date=eb_setup_form.cleaned_data['end_date'],
                )
                return redirect('.')

        if FareSetup.set_regular_dates in request.POST:
            regular_setup_form = SetDatesForm(data=request.POST)
            if regular_setup_form.is_valid():
                set_regular_fare_dates(
                    conference=conference,
                    start_date=regular_setup_form.cleaned_data['start_date'],
                    end_date=regular_setup_form.cleaned_data['end_date'],
                )
                return redirect('.')

    return TemplateResponse(
        request, 'conference/debugpanel/fares_setup.html', {
            'fares': fares,
            'FareSetup': FareSetup,
            'eb_setup_form': eb_setup_form,
            'regular_setup_form': regular_setup_form,
        }
    )


class SetDatesForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField()


class FareSetup:
    set_eb_dates = 'set_eb_dates'
    set_regular_dates = 'set_regular_dates'


urlpatterns = [
    url(r'^$', debug_panel_index, name='index'),
    url(r'^invoices/$',
        debug_panel_invoice_placeholders,
        name='invoice_placeholders'),
    url(r'^invoices/(?P<invoice_id>\d+)/$',
        debug_panel_invoice_force_preview,
        name="invoice_forcepreview"),
    url(r'^invoices_export/$',
        debug_panel_invoice_export_for_tax_report,
        name='invoice_export_for_tax_report'),
    url(r'^invoices_export.csv$',
        debug_panel_invoice_export_for_tax_report_csv,
        name='invoice_export_for_tax_report_csv'),
    url(r'^invoices_export_for_accounting.json$',
        debug_panel_invoice_export_for_payment_reconciliation_json,
        name='invoice_export_for_payment_reconciliation_json'),
    url(r'^invoices/reissue/(?P<invoice_id>\d+)/$',
        reissue_invoice,
        name='reissue_invoice'),

    url(r'^fares/setup/$',
        debugpanel_fares_setup,
        name='fares_setup'),

    url(r'^invoice-example/$',
        debug_panel_invoice_example,
        name='invoice_example'),
]
