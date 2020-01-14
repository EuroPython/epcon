import logging

from django import http
from django.conf import settings as dsettings
from django.contrib import messages
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from assopy import forms as aforms
from assopy import models
from common.decorators import render_to_template
from common.http import PdfResponse
from conference.invoicing import VAT_NOT_AVAILABLE_PLACEHOLDER

log = logging.getLogger('assopy.views')


class HttpResponseRedirectSeeOther(http.HttpResponseRedirect):
    status_code = 303

    def __init__(self, url):
        if not url.startswith('http'):
            url = dsettings.DEFAULT_URL_PREFIX + url
        super(HttpResponseRedirectSeeOther, self).__init__(url)


@login_required
@render_to_template('assopy/profile.html')
def profile(request):
    user = request.user.assopy_user
    if request.method == 'POST':
        form = aforms.Profile(data=request.POST, files=request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.info(request, 'Profile updated')
            return HttpResponseRedirectSeeOther('.')
    else:
        form = aforms.Profile(instance=user)
    return {
        'user': user,
        'form': form,
        'VAT_NOT_AVAILABLE_PLACEHOLDER': VAT_NOT_AVAILABLE_PLACEHOLDER,
    }


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
