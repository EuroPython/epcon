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
def profile_identities(request):
    if request.method == 'POST':
        try:
            x = request.user.assopy_user.identities.get(identifier=request.POST['identifier'])
        except:
            return http.HttpResponseBadRequest()
        log.info(
            'Removed the identity "%s" from the user "%s" "%s"',
            x.identifier,
            x.user.name(),
            x.user.user.email)
        x.delete()
    if request.is_ajax():
        return http.HttpResponse('')
    else:
        return HttpResponseRedirectSeeOther(reverse('assopy-profile'))


@login_required
@render_to_template('assopy/billing.html')
def billing(request, order_id=None):
    user = request.user.assopy_user
    if request.method == 'POST':
        form = aforms.BillingData(data=request.POST, files=request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return HttpResponseRedirectSeeOther('.')
    else:
        form = aforms.BillingData(instance=user)
    return {
        'user': user,
        'form': form,
    }


@render_to_template('assopy/checkout.html')
def checkout(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return http.HttpResponseBadRequest('unauthorized')
        form = aforms.FormTickets(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            o = models.Order.objects.create(user=request.user.assopy_user, payment=data['payment'], items=data['tickets'])
            if o.payment_url:
                return HttpResponseRedirectSeeOther(o.payment_url)
            else:
                return HttpResponseRedirectSeeOther(reverse('assopy-tickets'))
    else:
        form = aforms.FormTickets()

    return {
        'form': form,
    }


@login_required
@render_to_template('assopy/tickets.html')
def tickets(request):
    return {}


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

@csrf_exempt
def order_complete(request, assopy_id):
    if request.method != 'POST':
        return http.HttpResponseNotAllowed(('POST',))
    log.debug('Order complete notice (assopy_id %s): %s', assopy_id, request.environ)
    order = get_object_or_404(models.Order, assopy_id=assopy_id)
    r = order.complete()
    log.info('remote notice! order "%s" (%s) complete! result=%s', order.code, order.assopy_id, r)
    return http.HttpResponse('')
