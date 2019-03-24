import logging
import urllib.error
import urllib.parse
import urllib.request

from django import http
from django.conf import settings as dsettings
from django.contrib import messages
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from assopy import forms as aforms
from assopy import models, settings
from common.decorators import render_to_json, render_to_template
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
    if settings.TICKET_PAGE:
        return redirect(settings.TICKET_PAGE)
    return {}


@login_required
@render_to_json
def geocode(request):
    address = request.GET.get('address', '').strip()
    region = request.GET.get('region')
    if not address:
        return ''
    from assopy.utils import geocode as g
    return g(address, region=region)


def paypal_billing(request, code):
    # questa vista serve a eseguire il redirect su paypol
    log.debug('Paypal billing request (code %s): %s', code, request.environ)
    o = get_object_or_404(models.Order, code=code.replace('-', '/'))
    if o.total() == 0:
        o.confirm_order(timezone.now())
        return HttpResponseRedirectSeeOther(reverse('assopy-paypal-feedback-ok', kwargs={'code': code}))
    form = aforms.PayPalForm(o)
    return HttpResponseRedirectSeeOther("%s?%s" % (form.paypal_url(), form.as_url_args()))


def paypal_cc_billing(request, code):
    # questa vista serve a eseguire il redirect su paypal e aggiungere le info
    # per billing con cc
    log.debug('Paypal CC billing request (code %s): %s', code, request.environ)
    o = get_object_or_404(models.Order, code=code.replace('-', '/'))
    if o.total() == 0:
        o.confirm_order(timezone.now())
        return HttpResponseRedirectSeeOther(reverse('assopy-paypal-feedback-ok', kwargs={'code': code}))
    form = aforms.PayPalForm(o)
    cc_data = {
        "address_override" : 0,
        "no_shipping" : 1,
        "email": o.user.user.email,
        "first_name" : o.card_name,
        "last_name": "",
        "address1": o.address,
        #"zip": o.zip_code,
        #"state": o.state,
        "country": o.country,
        "address_name": o.card_name,
    }
    qparms = urllib.parse.urlencode([ (k,x.encode('utf-8') if isinstance(x, str) else x) for k,x in cc_data.items() ])
    return HttpResponseRedirectSeeOther(
        "%s?%s&%s" % (
            form.paypal_url(),
            form.as_url_args(),
            qparms
        )
    )


@render_to_template('assopy/paypal_cancel.html')
def paypal_cancel(request, code):
    log.debug('Paypal billing cancel request (code %s): %s', code, request.environ)
    o = get_object_or_404(models.Order, code=code.replace('-', '/'))
    form = aforms.PayPalForm(o)
    return {'form': form }


# looks like sometimes the redirect from paypal is ended with a POST request
# from the browser (someone said HttpResponseRedirectSeeOther?), since we are not
# executing anything critical I can skip the csrf check
@csrf_exempt
@render_to_template('assopy/paypal_feedback_ok.html')
def paypal_feedback_ok(request, code):
    log.debug('Paypal billing OK request (code %s): %s', code, request.environ)
    o = get_object_or_404(models.Order, code=code.replace('-', '/'))
    if o.user.user != request.user or o.method not in ('paypal', 'cc'):
        raise http.Http404()
    # let's wait a bit to get the IPN notification from PayPal
    from time import sleep
    sleep(0.4)
    return {
        'order': o,
    }


@login_required
@render_to_template('assopy/bank_feedback_ok.html')
def bank_feedback_ok(request, code):
    o = get_object_or_404(models.Order, code=code.replace('-', '/'))
    if o.user.user != request.user or o.method != 'bank':
        raise http.Http404()
    return {
        'order': o,
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


@login_required
def credit_note(request, order_code, code, mode='html'):
    if not request.user.is_staff:
        userfilter = { 'invoice__order__user__user': request.user, }
    else:
        userfilter = {}
    try:
        cnote = models.CreditNote.objects\
            .select_related('invoice__order')\
            .get(code=unquote(code), invoice__order__code=unquote(order_code), **userfilter)
    except models.CreditNote.DoesNotExist:
        raise http.Http404()

    order = cnote.invoice.order
    if mode == 'html':
        address = '%s, %s' % (order.address, str(order.country))
        items = cnote.note_items()
        for x in items:
            x['price'] = x['price'] * -1

        invoice = cnote.invoice
        rif = invoice.code
        if invoice.payment_date:
            rif = '%s - %s' % (rif, invoice.payment_date.strftime('%d %b %Y'))
        note = 'Nota di credito / Credit Note <b>Rif: %s</b>' % rif
        ctx = {
            'document': ('Nota di credito', 'Credit note'),
            'title': str(cnote),
            'code': cnote.code,
            'emit_date': cnote.emit_date,
            'order': {
                'card_name': order.card_name,
                'address': address,
                'billing_notes': order.billing_notes,
                'cf_code': order.cf_code,
                'vat_number': order.vat_number,
            },
            'items': items,
            'note': note,
            'price': {
                'net': cnote.net_price() * -1,
                'vat': cnote.vat_value() * -1,
                'total': cnote.price * -1,
            },
            'vat': cnote.invoice.vat,
            'real': True,
        }
        return render_to_response('assopy/invoice.html', ctx, RequestContext(request))
    else:
        hurl = reverse('assopy-credit_note-html', args=(order_code, code))
        if not settings.WKHTMLTOPDF_PATH:
            print("NO WKHTMLTOPDF_PATH SET")
            return HttpResponseRedirectSeeOther(hurl)
        raw = _pdf(request, hurl)

    from conference.models import Conference
    try:
        conf = Conference.objects\
            .get(conference_start__year=order.created.year).code
    except Conference.DoesNotExist:
        conf = order.created.year
    fname = '[%s credit note] %s.pdf' % (conf, cnote.code.replace('/', '-'))

    response = http.HttpResponse(raw, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="%s"' % fname
    return response

@login_required
@render_to_template('assopy/voucher.html')
def voucher(request, order_id, item_id):
    item = get_object_or_404(models.OrderItem, order=order_id, id=item_id)
    if (not item.ticket or item.ticket.fare.payment_type != 'v' or item.order.user.user != request.user) and not request.user.is_superuser:
        raise http.Http404()
    return {
        'item': item,
    }

@csrf_exempt
def order_complete(request, assopy_id):
    if request.method != 'POST':
        return http.HttpResponseNotAllowed(('POST',))
    log.debug('Order complete notice (assopy_id %s): %s', assopy_id, request.environ)
    order = get_object_or_404(models.Order, assopy_id=assopy_id)
    r = order.complete()
    log.info('remote notice! order "%s" (%s) complete! result=%s', order.code, order.assopy_id, r)
    return http.HttpResponse('')

@login_required
@render_to_json
def refund(request, order_id, item_id):
    try:
        item = models.OrderItem.objects\
            .select_related('order')\
            .get(order=order_id, id=item_id)
    except models.OrderItem.DoesNotExist:
        raise http.Http404()

    try:
        r = models.RefundOrderItem.objects.select_related('refund').get(orderitem=item_id)
        if r.refund.status == 'rejected':
            r = None
    except models.RefundOrderItem.DoesNotExist:
        r = None

    if request.method == 'POST':
        if r:
            return http.HttpResponseBadRequest()
        try:
            d = request.session['doppelganger']
        except KeyError:
            user = request.user
        else:
            from django.contrib.auth.models import User
            user = User.objects.get(id=d[0])
        if not settings.ORDERITEM_CAN_BE_REFUNDED(user, item):
            return http.HttpResponseBadRequest()
        form = aforms.RefundItemForm(item, data=request.POST)
        if not form.is_valid():
            return form.errors

        data = form.cleaned_data
        note = ''
        if data['paypal'] or data['bank']:
            if data['paypal']:
                note += 'paypal: %s\n' % data['paypal']
            if data['bank']:
                note += 'bank routing: %s\n' % data['bank']
            note += '----------------------------------------\n'
        r = models.Refund.objects.create_from_orderitem(
            item, reason=data['reason'], internal_note=note)
    if not r:
        return None
    return {
        'status': r.status,
    }
