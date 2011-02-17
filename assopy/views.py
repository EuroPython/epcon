# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django import template
from django.conf import settings as dsettings
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core import mail
from django.core.urlresolvers import reverse
from django.forms.formsets import BaseFormSet, formset_factory
from django.db import transaction
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext as _

from assopy import forms as aforms
from assopy import janrain
from assopy import models
from assopy import settings
from assopy.utils import send_email

from conference import models as cmodels

import json
import logging
from itertools import izip_longest

log = logging.getLogger('assopy.views')

class HttpResponseRedirectSeeOther(http.HttpResponseRedirect):
    status_code = 303

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

@login_required
@render_to('assopy/profile.html')
def profile(request):
    user = request.user.assopy_user
    if request.method == 'POST':
        form = aforms.Profile(data=request.POST, files=request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            if data['photo']:
                user.photo = data['photo']
            user.www = data['www']
            user.twitter = data['twitter']
            user.phone = data['phone']
            user.save()
            user.setBilling(firstname=data['firstname'], lastname=data['lastname'])
            return HttpResponseRedirectSeeOther('.')
    else:
        data = user.billing()
        form = aforms.Profile({
            'firstname': data['firstname'],
            'lastname': data['lastname'],
            'phone': user.phone,
            'www': user.www,
            'twitter': user.twitter,
        })
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
        x.delete()
    if request.is_ajax():
        return http.HttpResponse('')
    else:
        return HttpResponseRedirectSeeOther(reverse('assopy-profile'))

@login_required
@render_to('assopy/billing.html')
def billing(request):
    user = request.user.assopy_user
    if request.method == 'POST':
        form = aforms.BillingData(data=request.POST, files=request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            user.setBilling(**data)
            return HttpResponseRedirectSeeOther('.')
    else:
        initial = user.billing()
        form = aforms.BillingData(initial=initial)
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
            user.is_active = False
            user.save()
            request.session['new-account-user'] = user.pk
            return HttpResponseRedirectSeeOther(reverse('assopy-new-account-feedback'))
    return {
        'form': form,
        'next': next,
    }

@render_to('assopy/new_account_feedback.html')
def new_account_feedback(request):
    try:
        user = models.User.objects.get(pk=request.session.pop('new-account-user'))
    except models.User.DoesNotExist:
        user = None
    return {
        'u': user,
    }

@transaction.commit_on_success
def otc_code(request, token):
    t = models.Token.objects.retrieve(token)
    if t is None:
        raise http.Http404()

    if t.ctype == 'v':
        auth.logout(request)
        user = t.user
        user.is_active = True
        user.save()
        user = auth.authenticate(uid=user.id)
        auth.login(request, user)
        return redirect('assopy-profile')
    elif t.ctype == 'j':
        payload = json.loads(t.payload)
        email = payload['email']
        profile = payload['profile']
        log.info('"%s" verified; link to "%s"', email, profile['identifier'])
        identity = _linkProfileToEmail(email, profile)
        duser = auth.authenticate(identifier=identity.identifier)
        auth.login(request, duser)
        return redirect('assopy-profile')

def _linkProfileToEmail(email, profile):
    try:
        current = auth.models.User.objects.get(email=email)
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
    redirect_to = request.session.get('jr_next', '/')
    try:
        token = request.POST['token']
    except KeyError:
        return http.HttpResponseBadRequest()
    profile = janrain.auth_info(settings.JANRAIN['secret'], token)
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
                # attivo.  Devo chiedere all'utente un email validae inviare a
                # quella email una mail con un link di conferma.
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
            ctx = {
                'name': name,
                'provider': p['providerName'],
                'token': token,
                'current': current,
            }
            body = template.loader.render_to_string('assopy/email/janrain_incomplete_profile.txt', ctx)
            mail.send_mail(_('Verify your email'), body, 'info@pycon.it', [ email ])
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
    class FormTickets(forms.Form):
        payment = forms.ChoiceField(choices=(('paypal', 'PayPal'),('bank', 'Bank')))

        def __init__(self, *args, **kwargs):
            super(FormTickets, self).__init__(*args, **kwargs)
            for t in self.available_fares():
                self.fields[t.code] = forms.IntegerField(label=t.name, min_value=0, required=False)

        def available_fares(self):
            return cmodels.Fare.objects.available()

        def clean(self):
            fares = dict( (x.code, x) for x in self.available_fares() )
            data = self.cleaned_data
            o = []
            for k, q in data.items():
                if k in ('payment',):
                    continue
                if not q:
                    continue
                if k not in fares:
                    raise forms.ValidationError('Invalid fare')
                f = fares[k]
                if not f.valid():
                    raise forms.ValidationError('Invalid fare')
                o.append((f, q))
            if not o:
                raise forms.ValidationError('no tickets')

            data['tickets'] = o
            return data

    if request.method == 'POST':
        if not request.user.is_authenticated():
            return http.HttpResponseBadRequest('unauthorized')
        form = FormTickets(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            o = models.Order.objects.create(user=request.user, payment=data['payment'], items=data['tickets'])
            rows = []
            for x in o.orderitem_set.order_by('ticket__fare__code'):
                rows.append('%-15s%6.2f' % (x.ticket.fare.code, x.ticket.fare.price))
            rows.append('-'*21)
            rows.append('%15s%6.2f' % ('', o.total()))
            send_email(
                subject='new order from "%s %s"' % (request.user.first_name, request.user.last_name),
                message='\n'.join(rows),
            )
            return HttpResponseRedirectSeeOther(reverse('assopy-tickets'))
    else:
        form = FormTickets()
        
    return {
        'form': form,
    }

@login_required
@render_to('assopy/tickets.html')
def tickets(request):
    if settings.TICKET_PAGE:
        return redirect(settings.TICKET_PAGE)
    return {}
