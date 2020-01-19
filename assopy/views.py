import logging

from django import http
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from assopy import models
from common.http import PdfResponse

log = logging.getLogger('assopy.views')


@login_required
def invoice(request, order_code, code, mode='html'):
    if not request.user.is_staff:
        userfilter = {
            'order__user__user': request.user,
        }
    else:
        userfilter = {}

    invoice = get_object_or_404(
        models.Invoice,
        code=unquote(code),
        order__code=unquote(order_code),
        **userfilter
    )

    if mode == 'html':
        return http.HttpResponse(invoice.html)

    return PdfResponse(filename=invoice.get_invoice_filename(),
                       content=invoice.html)
