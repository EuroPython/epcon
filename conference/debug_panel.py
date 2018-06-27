# coding: utf-8

"""
Things in this file are related to a special debug panel that helps us debug
things in production.
"""

import platform
import subprocess

import django
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
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
