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
        exclude = aforms.BillingData.Meta.exclude + ('vat_number',)

    def clean(self):
        data = self.cleaned_data
        if 'cf_code' in self.cleaned_data:
            cf_code = self.cleaned_data['cf_code']
            vat = self.cleaned_data.get('vat_number', '')
            country = self.cleaned_data['country']
            if country and country.pk == 'IT':
               # the tax id is 16 characters for persons, for companies it can be shorter
               if not cf_code or (len(cf_code) != 16 and not vat):
                   # hack to tie the error to the cf_code field
                   e = forms.ValidationError('"Codice Fiscale" is required for Italian customers')
                   self._errors['cf_code'] = self.error_class(e.messages)
                   del self.cleaned_data['cf_code']
        return data

class P3BillingDataCompany(P3BillingData):
    billing_notes = forms.CharField(
        label='Additional billing information',
        help_text='If your company needs some information to appear on the invoice in addition to those provided above (eg. PO number, etc.), write them here.<br />We reserve the right to review the contents of this box.',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    # deriving is not an error, I need to get vat_number
    class Meta(aforms.BillingData.Meta):
        exclude = aforms.BillingData.Meta.exclude + ('cf_code',)

    def __init__(self, *args, **kwargs):
        super(P3BillingDataCompany, self).__init__(*args, **kwargs)
        self.fields['card_name'].label = 'Company Name'
        self.fields['address'].required = True

#    def clean_vat_number(self):
#        # I can verify only european ids using vies
#        vat = self.cleaned_data['vat_number']
#        country = self.instance.country
#        if vat and country and country.vat_company_verify == 'v':
#            from assopy.clients import vies
#            try:
#                check = vies.check_vat(country.pk, vat)
#            except Exception:
#                # VIES servicy may fail for unknown reasons, I don't want
#                # to lose an order because of that.
#                pass
#            else:
#                if not check:
#                    raise forms.ValidationError('According to VIES, this is not a valid vat number')
#        return vat

def cart(request):
    u = None
    if request.user.is_authenticated():
        try:
            u = request.user.assopy_user
        except AttributeError:
            pass
    at = 'p'

    # user-cart is needed for the confirmation page with invoce data,
    # I want to be suer that the only way to set it is when there is
    # a valid POST request
    request.session.pop('user-cart', None)
    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponseRedirectSeeOther(reverse('p3-cart'))
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
            # if the fom is not validate because of the coupon I'm deleting it
            # from the data to be able to give the user a feedback anyway
            if 'coupon' in form.errors:
                qdata = request.POST.copy()
                del qdata['coupon']
                form = p3forms.P3FormTickets(data=qdata, user=request.user.assopy_user)

        if form.is_valid():
            data = form.cleaned_data
            coupons = []
            if data['coupon']:
                coupons.append(data['coupon'])
            totals = amodels.Order\
                .calculator(items=data['tickets'], coupons=coupons, user=request.user.assopy_user)
            def _fmt(x):
                if x == 0:
                    # x is a Decimal and 0 and -0 are different
                    return '0'
                else:
                    return '%.2f' % x

            grand_total = 0
            # to allow the client to associate each ticket with the correct price
            # infos are rewritten inthe same "format" that has been used to send them.
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
        # the session is missing the user-cart key, instead of raising a
        # 500 error I'm sending back the user to the cart.
        return redirect('p3-cart')

    recipient = 'p'
    conference_recipients = set()
    for fare, foo in tickets:
        if fare.recipient_type == 'c':
            recipient = 'c'
        if fare.ticket_type == 'conference':
            # you cannot buy tickets for different entity types (user/company)
            conference_recipients.add('c' if fare.recipient_type == 'c' else 'p')
    if len(conference_recipients) > 1:
        raise ValueError('mismatched fares: %s' % ','.join(x[0].code for x in tickets))

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
            # free order, I'm only interested in knowing the user accepted the code of conduct.
            if 'code_conduct' in request.POST:
                order_data = {
                    'payment': 'bank',
                }
            else:
                # if it wasn't accepted the form is prepared and the user
                # will see the checkbox in red
                form = cform(instance=auser, data=post_data)
                form.is_valid()
        else:
            form = cform(instance=auser, data=post_data)
            if form.is_valid():
                order_data = form.cleaned_data
                form.save()

        if order_data:
            coupon = request.session['user-cart']['coupon']
            kw = dict(
                user=auser,
                payment=order_data['payment'],
                billing_notes=order_data.get('billing_notes', ''),
                items=request.session['user-cart']['tickets'],
                coupons=[coupon] if coupon else None,
            )
            if recipient == 'p':
                kw['cf_code'] = auser.cf_code
            else:
                kw['vat_number'] = auser.vat_number

            o = amodels.Order.objects.create(**kw)
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
