# -*- coding: UTF-8 -*-
from assopy import models as amodels
from assopy import forms as aforms
from assopy.views import render_to_json, HttpResponseRedirectSeeOther
from django import forms
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from p3 import forms as p3forms

class P3BillingData(aforms.BillingData):
    card_name = forms.CharField(
        label='Your Name',
        max_length=200,
    )
    payment = forms.ChoiceField(choices=amodels.ORDER_PAYMENT, initial='paypal')
    code_conduct = forms.BooleanField(label='I have read and accepted the <a class="trigger-overlay" href="/code-of-conduct" target="blank">code of conduct</a>.')

    def __init__(self, *args, **kwargs):
        super(P3BillingData, self).__init__(*args, **kwargs)
        self.fields['country'].required = True
        self.fields['address'].required = True

    class Meta(aforms.BillingData.Meta):
        exclude = ('vat_number',)

class P3BillingDataCompany(P3BillingData):
    vat_number = forms.CharField(max_length=22, required=False)

    billing_notes = forms.CharField(
        label='Additional billing information',
        help_text='If your company needs some information to appear on the invoice in addition to those provided above (eg. VAT number, PO number, etc.), write them here.<br />We reserve the right to review the contents of this box.',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    # la derivazione non è un errore, voglio riappropriarmi del vat_number
    class Meta(aforms.BillingData.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super(P3BillingDataCompany, self).__init__(*args, **kwargs)
        self.fields['card_name'].label = 'Company Name'
        self.fields['address'].required = True

    def clean_vat_number(self):
        # Posso verificare solo i codici europei tramite vies
        vat = self.cleaned_data['vat_number']
        country = self.instance.country
        if vat and country and country.vat_company_verify == 'v':
            from assopy.clients import vies
            try:
                check = vies.check_vat(country.pk, vat)
            except Exception:
                # il servizio VIES può fallire per motivi suoi, non voglio
                # perdermi un ordine a causa loro
                pass
            else:
                if not check:
                    raise forms.ValidationError('According to VIES, this is not a valid vat number')
        return vat

def cart(request):
    if request.user.is_authenticated():
        u = request.user
    else:
        u = None
    at = 'p'

    # user-cart serve alla pagina di conferma con i dati di fatturazione,
    # voglio essere sicuro che l'unico modo per impostarlo sia quando viene
    # fatta una POST valida
    request.session.pop('user-cart', None)
    if request.method == 'POST':
        form = p3forms.P3FormTickets(data=request.POST, user=u)
        if form.is_valid():
            request.session['user-cart'] = form.cleaned_data
            return redirect('p3-billing')
    else:
        form = p3forms.P3FormTickets(initial={
            'order_type': 'deductible' if at == 'c' else 'non-deductible',
        }, user=u)
    fares = {}
    for f in form.available_fares():
        if not f.code.startswith('_'):
            fares[f.code] = f
    fares_ordered = sorted(fares.values(), key=lambda x: x.name)
    ctx = {
        'form': form,
        'fares': fares,
        'fares_ordered': fares_ordered,
        'account_type': at,
    }
    return render(request, 'p3/cart.html', ctx)

@login_required
@render_to_json
def calculator(request):
    output = {
        'tickets': [],
        'coupon': 0,
        'total': 0,
    }
    if request.method == 'POST':
        form = p3forms.P3FormTickets(data=request.POST, user=request.user.assopy_user)
        if not form.is_valid():
            # se la form non valida a causa del coupon lo elimino dai dati per
            # dare cmq un feedback all'utente
            if 'coupon' in form.errors:
                qdata = request.POST.copy()
                del qdata['coupon']
                form = p3forms.P3FormTickets(data=qdata, user=request.user.assopy_user)

        if form.is_valid():
            data = form.cleaned_data
            coupons = []
            if data['coupon']:
                coupons.append(data['coupon'])
            totals = amodels.Order.calculator(items=data['tickets'], coupons=coupons, user=request.user.assopy_user)
            def _fmt(x):
                if x == 0:
                    # x è un Decimal e ottengo una rappresentazione diversa tra 0 e -0
                    return '0'
                else:
                    return '%.2f' % x

            grand_total = 0
            # per permettere al client di associare ad ogni biglietto il giusto
            # costo, riscrivo le informazioni nello stesso "formato" in cui mi
            # sono state inviate.
            tickets = []
            for row in totals['tickets']:
                fcode = row[0].code
                total = row[2]
                params = row[1]
                if 'period' in params:
                    start = settings.P3_HOTEL_RESERVATION['period'][0]
                    params['period'] = map(lambda x: (x-start).days, params['period'])
                tickets.append((fcode, params, _fmt(total)))
                grand_total += total
            output['tickets'] = tickets

            if data['coupon']:
                total = totals['coupons'][data['coupon'].code][0]
                output['coupon'] = _fmt(total)
                grand_total += total

            output['total'] = _fmt(grand_total)
        else:
            return form.errors

    return output

@login_required
def billing(request):
    try:
        tickets = request.session['user-cart']['tickets']
    except KeyError:
        # la sessione non ha più la chiave user-cart, invece che sollevare un
        # errore 500 rimando l'utente sul carrello
        return redirect('p3-cart')

    # non si possono comprare biglietti destinati ad entità diverse
    # (persone/ditte)
    recipients = set()
    for fare, foo in tickets:
        if fare.ticket_type != 'conference':
            continue
        recipients.add('c' if fare.recipient_type == 'c' else 'p')
    if len(recipients) > 1:
        raise ValueError('mismatched fares: %s' % ','.join(x[0].code for x in tickets))

    try:
        recipient = recipients.pop()
    except:
        recipient = 'p'

    if recipient == 'p':
        cform = P3BillingData
    else:
        cform = P3BillingDataCompany

    coupon = request.session['user-cart']['coupon']
    totals = amodels.Order.calculator(
        items=tickets, coupons=[coupon] if coupon else None, user=request.user.assopy_user)

    if request.method == 'POST':
        auser = request.user.assopy_user
        post_data = request.POST.copy()

        order_data = None
        if totals['total'] == 0:
            # free order, mi interessa solo sapere che l'utente ha accettato il
            # code of conduct
            if 'code_conduct' in request.POST:
                order_data = {
                    'payment': 'bank',
                }
            else:
                # se non lo ha accettato, preparo la form, e l'utente si
                # troverà la checkbox colorata in rosso
                form = cform(instance=auser, data=post_data)
                form.is_valid()
        else:
            form = cform(instance=auser, data=post_data)
            if form.is_valid():
                order_data = form.cleaned_data
                form.save()

        if order_data:
            coupon = request.session['user-cart']['coupon']
            o = amodels.Order.objects.create(
                user=auser, payment=order_data['payment'],
                billing_notes=order_data.get('billing_notes', ''),
                items=request.session['user-cart']['tickets'],
                coupons=[coupon] if coupon else None,
            )
            if totals['total'] == 0:
                return HttpResponseRedirectSeeOther(reverse('assopy-tickets'))

            if order_data['payment'] in ('paypal','cc'):
                urlname = 'assopy-paypal-redirect' if order_data['payment'] == 'paypal' else 'assopy-cc-paypal-redirect'
                return HttpResponseRedirectSeeOther(
                    reverse(
                        urlname,
                        kwargs={'code': unicode(o.code).replace('/', '-')}))
            elif o.payment_url:
                return HttpResponseRedirectSeeOther(o.payment_url)
            else:
                return HttpResponseRedirectSeeOther(
                    reverse(
                        'assopy-bank-feedback-ok',
                        kwargs={'code': o.code.replace('/', '-')}))
    else:
        auser = request.user.assopy_user
        if not auser.card_name:
            auser.card_name = '%s %s' % (request.user.first_name, request.user.last_name)
        form = cform(instance=auser)

    ctx = {
        'totals': totals,
        'form': form,
    }
    return render(request, 'p3/billing.html', ctx)
