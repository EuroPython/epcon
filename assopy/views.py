# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django.conf import settings as dsettings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.util import unquote
from django.core.urlresolvers import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt

from assopy import forms as aforms
from assopy import janrain
from assopy import models
from assopy import settings
if settings.GENRO_BACKEND:
    from assopy.clients import genro
from email_template import utils

import json
import logging
import urllib
from datetime import datetime

log = logging.getLogger('assopy.views')

class HttpResponseRedirectSeeOther(http.HttpResponseRedirect):
    status_code = 303

    def __init__(self, url):
        if not url.startswith('http'):
            url = dsettings.DEFAULT_URL_PREFIX + url
        super(HttpResponseRedirectSeeOther, self).__init__(url)

# see: http://www.djangosnippets.org/snippets/821/
def render_to(template):
    """
    Decorator for Django views that sends returned dict to render_to_response function
    with given template and RequestContext as context instance.

    If view doesn't return dict then decorator simply returns output.
    Additionally view can return two-tuple, which must contain dict as first
    element and string with template name as second. This string will
    override template name, given as parameter

    Parameters:

     - template: template name to use
    """
    def renderer(func):
        def wrapper(request, *args, **kw):
            output = func(request, *args, **kw)
            if isinstance(output, (list, tuple)):
                return render_to_response(output[1], output[0], RequestContext(request))
            elif isinstance(output, dict):
                return render_to_response(template, output, RequestContext(request))
            return output
        return wrapper
    return renderer

def render_to_json(f):
    from conference.views import json_dumps
    if dsettings.DEBUG:
        ct = 'text/plain'
        j = lambda d: json_dumps(d, indent=2)
    else:
        ct = 'application/json'
        j = json_dumps
    def wrapper(*args, **kw):
        try:
            result = f(*args, **kw)
        except Exception, e:
            result = j(str(e))
            status = 500
        else:
            if isinstance(result, http.HttpResponse):
                return result
            else:
                from django.forms.util import ErrorDict
                status = 200 if not isinstance(result, ErrorDict) else 400
                result = j(result)
        return http.HttpResponse(content=result, content_type=ct, status=status)
    return wrapper

@login_required
@render_to('assopy/profile.html')
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
@render_to('assopy/billing.html')
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

@render_to('assopy/new_account.html')
def new_account(request):
    if request.user.is_authenticated():
        return redirect('assopy-profile')

    if request.method == 'GET':
        form = aforms.NewAccountForm()
    else:
        form = aforms.NewAccountForm(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = models.User.objects.create_user(
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=data['password1'],
            )
            request.session['new-account-user'] = user.pk
            return HttpResponseRedirectSeeOther(reverse('assopy-new-account-feedback'))
    return {
        'form': form,
        'next': request.GET.get('next', '/'),
    }

@render_to('assopy/new_account_feedback.html')
def new_account_feedback(request):
    try:
        user = models.User.objects.get(pk=request.session['new-account-user'])
    except KeyError:
        return redirect('/')
    except models.User.DoesNotExist:
        user = None
    return {
        'u': user,
    }

def OTCHandler_V(request, token):
    auth.logout(request)
    user = token.user
    user.is_active = True
    user.save()
    user = auth.authenticate(uid=user.id)
    auth.login(request, user)
    return redirect('assopy-profile')

def OTCHandler_J(request, token):
    payload = json.loads(token.payload)
    email = payload['email']
    profile = payload['profile']
    log.info('"%s" verified; link to "%s"', email, profile['identifier'])
    identity = _linkProfileToEmail(email, profile)
    duser = auth.authenticate(identifier=identity.identifier)
    auth.login(request, duser)
    return redirect('assopy-profile')

@transaction.commit_on_success
def otc_code(request, token):
    t = models.Token.objects.retrieve(token)
    if t is None:
        raise http.Http404()

    from assopy.utils import dotted_import
    try:
        path = settings.OTC_CODE_HANDLERS[t.ctype]
    except KeyError:
        return http.HttpResponseBadRequest()

    return dotted_import(path)(request, t)

def _linkProfileToEmail(email, profile):
    try:
        current = auth.models.User.objects.get(email__iexact=email)
    except auth.models.User.DoesNotExist:
        current = auth.models.User.objects.create_user(janrain.suggest_username(profile), email)
        try:
            current.first_name = profile['name']['givenName']
        except KeyError:
            pass
        try:
            current.last_name = profile['name']['familyName']
        except KeyError:
            pass
        current.is_active = True
        current.save()
        log.debug('new (active) django user created "%s"', current)
    else:
        log.debug('django user found "%s"', current)
    try:
        # se current è stato trovato tra gli utenti locali forse esiste
        # anche la controparte assopy
        user = current.assopy_user
    except models.User.DoesNotExist:
        log.debug('the current user "%s" will become an assopy user', current)
        user = models.User(user=current)
        user.save()
    log.debug('a new identity (for "%s") will be linked to "%s"', profile['identifier'], current)
    identity = models.UserIdentity.objects.create_from_profile(user, profile)
    return identity

@csrf_exempt
@transaction.commit_on_success
def janrain_token(request):
    if request.method != 'POST':
        return http.HttpResponseNotAllowed(('POST',))
    redirect_to = request.session.get('jr_next', reverse('assopy-profile'))
    try:
        token = request.POST['token']
    except KeyError:
        return http.HttpResponseBadRequest()
    try:
        profile = janrain.auth_info(settings.JANRAIN['secret'], token)
    except Exception, e:
        log.warn('exception during janrain auth info: "%s"', str(e))
        return HttpResponseRedirectSeeOther(dsettings.LOGIN_URL)

    log.info('janrain profile from %s: %s', profile['providerName'], profile['identifier'])

    current = request.user
    duser = auth.authenticate(identifier=profile['identifier'])
    if duser is None:
        log.info('%s is a new identity', profile['identifier'])
        # è la prima volta che questo utente si logga con questo provider
        if not current.is_anonymous():
            verifiedEmail = current.email
        else:
            # devo creare tutto, utente django, assopy e identità
            if not 'verifiedEmail' in profile:
                # argh, il provider scelto non mi fornisce un email sicura; per
                # evitare il furto di account non posso rendere l'account
                # attivo.  Devo chiedere all'utente un email valida e inviare a
                # quella email un link di conferma.
                log.info('janrain profile without a verified email')
                request.session['incomplete-profile'] = profile
                return HttpResponseRedirectSeeOther(reverse('assopy-janrain-incomplete-profile'))
            else:
                verifiedEmail = profile['verifiedEmail']
                log.info('janrain profile with a verified email "%s"', verifiedEmail)
        identity = _linkProfileToEmail(verifiedEmail, profile)
        duser = auth.authenticate(identifier=identity.identifier)
        auth.login(request, duser)
    else:
        # è un utente conosciuto, devo solo verificare che lo user associato
        # all'identità e quello loggato in questo momento siano la stessa
        # persona
        if current.is_anonymous():
            # ok, non devo fare altro che loggarmi con l'utente collegato
            # all'identità
            auth.login(request, duser)
        elif current != duser:
            # l'utente corrente e quello collegato all'identità non coincidano
            # devo mostrare un messaggio di errore
            return HttpResponseRedirectSeeOther(reverse('assopy-janrain-login_mismatch'))
        else:
            # non ho niente da fare, l'utente è già loggato
            pass
    return HttpResponseRedirectSeeOther(redirect_to)

@render_to('assopy/janrain_incomplete_profile.html')
@transaction.commit_on_success
def janrain_incomplete_profile(request):
    p = request.session['incomplete-profile']
    try:
        name = p['displayName']
    except KeyError:
        name = '%s %s' % (p['name'].get('givenName', ''), p['name'].get('familyName', ''))
    class Form(forms.Form):
        email = forms.EmailField()
    if request.method == 'POST':
        form = Form(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            payload = {
                'email': email,
                'profile': p,
            }
            token = models.Token.objects.create(ctype='j', payload=json.dumps(payload))
            try:
                current = auth.models.User.objects.get(email=email)
            except auth.models.User.DoesNotExist:
                current = None
            utils.email(
                'janrain-incomplete',
                ctx={
                    'name': name,
                    'provider': p['providerName'],
                    'token': token,
                    'current': current,
                },
                to=[email]
            ).send()
            del request.session['incomplete-profile']
            return HttpResponseRedirectSeeOther(reverse('assopy-janrain-incomplete-profile-feedback'))
    else:
        form = Form()
    return {
        'provider': p['providerName'],
        'name': name,
        'form': form,
    }

@render_to('assopy/janrain_incomplete_profile_feedback.html')
def janrain_incomplete_profile_feedback(request):
    return {}

@render_to('assopy/janrain_login_mismatch.html')
def janrain_login_mismatch(request):
    return {}

@render_to('assopy/checkout.html')
def checkout(request):
    if request.method == 'POST':
        if not request.user.is_authenticated():
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
@render_to('assopy/tickets.html')
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
    o = get_object_or_404(models.Order, code=code.replace('-', '/'))
    if o.total() == 0:
        o.confirm_order(datetime.now())
        return HttpResponseRedirectSeeOther(reverse('assopy-paypal-feedback-ok', kwargs={'code': code}))
    form = aforms.PayPalForm(o)
    return HttpResponseRedirectSeeOther("%s?%s" % (form.paypal_url(), form.as_url_args()))

def paypal_cc_billing(request, code):
    # questa vista serve a eseguire il redirect su paypal e aggiungere le info
    # per billing con cc
    o = get_object_or_404(models.Order, code=code.replace('-', '/'))
    if o.total() == 0:
        o.confirm_order(datetime.now())
        return HttpResponseRedirectSeeOther(reverse('assopy-paypal-feedback-ok', kwargs={'code': code}))
    form = aforms.PayPalForm(o)
    cc_data = {
        "address_override" : 1,
        "no_shipping" : 1,
        "email": o.user.user.email,
        "first_name" : o.card_name,
        "last_name": "",
        "address1": o.address,
        "zip": o.zip_code,
        "state": o.state,
        "country": o.country,
        "address_name":o.card_name,
    }
    qparms = urllib.urlencode([ (k,x.encode('utf-8') if isinstance(x, unicode) else x) for k,x in cc_data.items() ])
    return HttpResponseRedirectSeeOther(
        "%s?%s&%s" % (
            form.paypal_url(),
            form.as_url_args(),
            qparms
        )
    )

@render_to('assopy/paypal_cancel.html')
def paypal_cancel(request, code):
    o = get_object_or_404(models.Order, code=code.replace('-', '/'))
    form = aforms.PayPalForm(o)
    return {'form': form }

# sembra che a volte la redirezione di paypal si concluda con una POST da parte
# del browser (qualcuno ha detto HttpResponseRedirectSeeOther?), dato che non
# eseguo niente di pericoloso evito di controllare il csrf
@csrf_exempt
@render_to('assopy/paypal_feedback_ok.html')
def paypal_feedback_ok(request, code):
    o = get_object_or_404(models.Order, code=code.replace('-', '/'))
    if o.user.user != request.user or o.method not in ('paypal', 'cc'):
        raise http.Http404()
    # aspettiamo un po' per dare tempo a Paypal di inviarci la notifica IPN
    from time import sleep
    sleep(0.4)
    return {
        'order': o,
    }

@login_required
@render_to('assopy/bank_feedback_ok.html')
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
        order = invoice.order
        address = '%s, %s<br />' % (order.address, order.zip_code)
        if order.city:
            address += '%s, ' % order.city
        address += unicode(order.country)
        ctx = {
            'title': unicode(invoice),
            'code': invoice.code,
            'emit_date': invoice.emit_date,
            'order': {
                'card_name': order.card_name,
                'address': address,
                'billing_notes': order.billing_notes,
            },
            'items': invoice.invoice_items(),
            'note': invoice.note,
            'price': {
                'net': invoice.net_price(),
                'vat': invoice.vat_value(),
                'total': invoice.price,
            },
            'vat': invoice.vat,
            'real': settings.IS_REAL_INVOICE(invoice.code),
        }
        return render_to_response('assopy/invoice.html', ctx, RequestContext(request))
    else:
        if settings.GENRO_BACKEND:
            assopy_id = invoice.assopy_id
            data = genro.invoice(assopy_id)
            if data.get('credit_note'):
                order = get_object_or_404(models.Order, invoices__credit_notes__assopy_id=assopy_id)
            else:
                order = get_object_or_404(models.Order, assopy_id=data['order_id'])
            raw = urllib.urlopen(genro.invoice_url(assopy_id))
        else:
            hurl = reverse('assopy-invoice-html', args=(order_code, code))
            if not settings.WKHTMLTOPDF_PATH:
                return HttpResponseRedirectSeeOther(hurl)
            raw = _pdf(request, hurl)
            order = invoice.order

        from conference.models import Conference
        try:
            conf = Conference.objects\
                .get(conference_start__year=order.created.year).code
        except Conference.DoesNotExist:
            conf = order.created.year
        fname = '[%s invoice] %s.pdf' % (conf, invoice.code.replace('/', '-'))

        response = http.HttpResponse(raw, mimetype='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="%s"' % fname
        return response

def _pdf(request, url):
    import subprocess
    command_args = [
        settings.WKHTMLTOPDF_PATH,
        '--cookie',
        dsettings.SESSION_COOKIE_NAME,
        request.COOKIES.get(dsettings.SESSION_COOKIE_NAME),
        '--zoom',
        '1.3',
        "%s%s" % (dsettings.DEFAULT_URL_PREFIX, url),
        '-'
    ]

    popen = subprocess.Popen(
        command_args,
        bufsize=4096,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    raw, _ = popen.communicate()
    return raw

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
        address = '%s, %s<br />' % (order.address, order.zip_code)
        if order.city:
            address += '%s, ' % order.city
        address += unicode(order.country)
        ctx = {
            'title': unicode(cnote),
            'code': cnote.code,
            'emit_date': cnote.emit_date,
            'order': {
                'card_name': order.card_name,
                'address': address,
                'billing_notes': order.billing_notes,
            },
            'items': cnote.note_items(),
            'note': '',
            'price': {
                'net': cnote.net_price(),
                'vat': cnote.vat_value(),
                'total': cnote.price,
            },
            'vat': cnote.invoice.vat,
            'real': True,
        }
        return render_to_response('assopy/invoice.html', ctx, RequestContext(request))
    else:
        hurl = reverse('assopy-credit_note-html', args=(order_code, code))
        if not settings.WKHTMLTOPDF_PATH:
            return HttpResponseRedirectSeeOther(hurl)
        raw = _pdf(request, hurl)

    from conference.models import Conference
    try:
        conf = Conference.objects\
            .get(conference_start__year=order.created.year).code
    except Conference.DoesNotExist:
        conf = order.created.year
    fname = '[%s credit note] %s.pdf' % (conf, cnote.code.replace('/', '-'))

    response = http.HttpResponse(raw, mimetype='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="%s"' % fname
    return response

@login_required
@render_to('assopy/voucher.html')
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
        if not settings.ORDERITEM_CAN_BE_REFUNDED(request.user, item):
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
