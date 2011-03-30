# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext, Template
from django.template.loader import render_to_string

from assopy.forms import BillingData
from assopy.models import Order, ORDER_PAYMENT, User, UserIdentity
from assopy.views import render_to, HttpResponseRedirectSeeOther

import forms as p3forms
import models
from conference.models import Fare, Ticket

import logging
import uuid

log = logging.getLogger('p3.views')

def map_js(request):
    return render_to_response(
        'p3/map.js', {}, context_instance=RequestContext(request), mimetype = 'text/javascript')

@login_required
@render_to('p3/tickets.html')
def tickets(request):
    tickets = models.TicketConference.objects.available(request.user, settings.CONFERENCE_CONFERENCE)
    # non mostro i biglietti associati ad ordini paypal che non risultano
    # ancora "completi"; poiché la notifica IPN è quasi contestuale al ritorno
    # dell'utente sul nostro sito, filtrando via gli ordini non confermati
    # elimino di fatto vecchi record rimasti nel db dapo che l'utente non ha
    # confermato il pagamento sul sito paypal o dopo che è tornato indietro
    # utilizzando il pulsante back
    from assopy.templatetags.assopy_tags import _get_cached_order_status
    tickets = list(tickets)
    for ix, t in list(enumerate(tickets))[::-1]:
        order = t.orderitem.order
        if order.method != 'bank' and not _get_cached_order_status(request, order.id):
            del tickets[ix]
    return {
        'tickets': tickets,
    }

def _assign_ticket(ticket, email):
    try:
        recipient = auth.models.User.objects.get(email=email)
    except auth.models.User.DoesNotExist:
        try:
            # qui uso filter + [0] invece che .get perchè potrebbe accadere,
            # anche se non dovrebbe, che due identità abbiano la stessa email
            # (ad esempio se una persona a usato la stessa mail su più servizi
            # remoti ma ha collegato questi servizi a due utenti locali
            # diversi). Non è un problema se più identità hanno la stessa email
            # (nota che il backend di autenticazione già verifica che la stessa
            # email non venga usata due volte per creare utenti django) perché
            # in ogni caso si tratta di email verificate da servizi esterni.
            recipient = UserIdentity.objects.filter(email=email)[0].user.user
        except IndexError:
            recipient = None
    if recipient is None:
        log.info('No user found for the email "%s"; time to create a new one', email)
        u = User.objects.create_user(email=email, token=True, send_mail=False)
        recipient = u.user
        name = email
    else:
        log.info('Found a local user (%s) for the email "%s"', recipient, email)
        try:
            auser = recipient.assopy_user
        except User.DoesNotExist:
            # uff, ho un utente su django che non è un assopy user, sicuramente
            # strascichi prima dell'introduzione dell'app assopy
            auser = User(user=recipient)
            auser.save()
        if not auser.token:
            recipient.assopy_user.token = str(uuid.uuid4())
            recipient.assopy_user.save()
        name = recipient.assopy_user.name()
    ctx = {
        'name': name,
        'ticket': ticket,
        'conference': 'Europython 2011',
        'link': settings.DEFAULT_URL_PREFIX + reverse('p3-user', kwargs={'token': recipient.assopy_user.token}),
    }
    body = render_to_string('p3/emails/ticket_assigned.txt', ctx)
    send_mail('Ticket assigned to you', body, 'info@pycon.it', [email])

@login_required
@transaction.commit_on_success
def ticket(request, tid):
    t = get_object_or_404(Ticket, pk=tid)
    try:
        p3c = t.p3_conference
    except models.TicketConference.DoesNotExist:
        p3c = None
        assigned_to = None
    else:
        assigned_to = p3c.assigned_to
    if t.user != request.user:
        if assigned_to is None or assigned_to != request.user.email:
            raise http.Http404()
    if request.method == 'POST':
        if t.fare.ticket_type == 'conference':
            form = p3forms.FormTicket(instance=p3c, data=request.POST, prefix='t%d' % (t.id,))
            if not form.is_valid():
                return http.HttpResponseBadRequest(str(form.errors))

            data = form.cleaned_data
            # prima di tutto sistemo il ticket di conference...
            t.name = data['ticket_name']
            t.save()
            # ...poi penso alle funzionalità aggiuntive dei biglietti p3
            x = form.save(commit=False)
            x.ticket = t
            if t.user != request.user:
                # solo il proprietario del biglietto può riassegnarlo
                x.assigned_to = assigned_to
            x.save()

            if t.user == request.user and assigned_to != x.assigned_to:
                if x.assigned_to:
                    log.info('ticket assigned to "%s"', x.assigned_to)
                    _assign_ticket(t, x.assigned_to)
                else:
                    log.info('ticket reclaimed (previously assigned to "%s")', assigned_to)

            if t.user != request.user and not request.user.first_name and not request.user.last_name and data['ticket_name']:
                # l'utente non ha, nel suo profilo, né il nome né il cognome (e
                # tra l'altro non è la persona che ha comprato il biglietto)
                # posso usare il nome che ha inserito per il biglietto nei dati
                # del profilo

                try:
                    f, l = data['ticket_name'].strip().split(' ', 1)
                except ValueError:
                    f = data['ticket_name'].strip()
                    l = ''
                request.user.first_name = f
                request.user.last_name = l
                request.user.save()
        else:
            form = p3forms.FormTicketPartner(instance=t, data=request.POST, prefix='t%d' % (t.id,))
            if not form.is_valid():
                return http.HttpResponseBadRequest(str(form.errors))
            form.save()
            
    if request.is_ajax():
        # restituisco il rendering del nuovo biglietto, così il chiamante può
        # mostrarlo facilmente
        tpl = Template('{% load p3 %}{% render_ticket t %}')
        return http.HttpResponse(tpl.render(RequestContext(request, {'t': t})))
    else:
        return HttpResponseRedirectSeeOther(reverse('p3-tickets'))

def user(request, token):
    """
    view che logga automaticamente un utente (se il token è valido) e lo
    ridirige alla pagine dei tickets 
    """
    u = get_object_or_404(User, token=token)
    log.info('autologin (via token url) for "%s"', u.user)
    if not u.user.is_active:
        u.user.is_active = True
        u.user.save()
        log.info('"%s" activated', u.user)
    user = auth.authenticate(uid=u.user.id)
    auth.login(request, user)
    return HttpResponseRedirectSeeOther(reverse('p3-tickets'))

@render_to('p3/cart.html')
def cart(request):
    from assopy.forms import FormTickets
    try:
        at = request.user.assopy_user.account_type
    except AttributeError:
        at = None
    class P3FormTickets(FormTickets):
        def __init__(self, *args, **kwargs):
            super(P3FormTickets, self).__init__(*args, **kwargs)
            del self.fields['payment']
        #def available_fares(self):
        #    return Fare.objects.all()
        def clean(self):
            data = super(P3FormTickets, self).clean()
            order_type = data['order_type']
            company = order_type == 'deductible'
            for ix, row in list(enumerate(data['tickets']))[::-1]:
                fare, quantity = row
                if (company ^ (fare.code[-1] == 'C')):
                    del data['tickets'][ix]
                    del data[fare.code]
            return data
    # user-cart serve alla pagina di conferma con i dati di fatturazione,
    # voglio essere sicuro che l'unico modo per impostarlo sia quando viene
    # fatta una POST valida
    request.session.pop('user-cart', None)
    if request.method == 'POST':
        form = P3FormTickets(data=request.POST)
        if form.is_valid():
            request.session['user-cart'] = form.cleaned_data
            return redirect('p3-billing')
    else:
        form = P3FormTickets(initial={
            'order_type': 'deductible' if at == 'c' else 'non-deductible',
        })
    fares = {}
    for f in form.available_fares():
        fares[f.code] = f
    return {
        'form': form,
        'fares': fares,
        'account_type': at,
    }

@login_required
@render_to('p3/billing.html')
def billing(request):
    tickets = []
    total = 0
    for fare, quantity in request.session['user-cart']['tickets']:
        t = fare.price * quantity
        tickets.append((fare, quantity, t))
        total += t

    # non si possono comprare biglietti destinati ad entità diverse
    # (persone/ditte)
    recipients = set()
    for fare, _, _ in tickets:
        recipients.add('c' if fare.recipient_type == 'c' else 'p')
    if len(recipients) != 1:
        raise ValueError('mismatched fares: %s' % ','.join(x[0].code for x in tickets))

    recipient = recipients.pop()
    class P3BillingData(BillingData):
        card_name = forms.CharField(
            label='Your Name' if recipient != 'c' else 'Company Name',
            max_length=200,
        )
        payment = forms.ChoiceField(choices=ORDER_PAYMENT, initial='paypal')
        code_conduct = forms.BooleanField(label='I have read and accepted the <a class="global-overlay" href="/code-of-conduct" target="blank">code of conduct</a>.')

        def __init__(self, *args, **kwargs):
            super(P3BillingData, self).__init__(*args, **kwargs)
            for f in self.fields.values():
                f.required = True
            if recipient == 'c':
                self.fields['billing_notes'] = forms.CharField(
                    label='Additional billing information',
                    help_text='If your company needs some information to appear on the invoice in addition to those provided above (eg. VAT number, PO number, etc.), write them here.<br />We reserve the right to review the contents of this box.',
                    required=False,
                    widget=forms.Textarea(attrs={'rows': 3}),
                )
        class Meta(BillingData.Meta):
            exclude = ('city', 'zip_code', 'state', 'vat_number', 'tin_number')

    if request.method == 'POST':
        # non voglio che attraverso questa view sia possibile cambiare il tipo
        # di account company/private
        auser = request.user.assopy_user
        post_data = request.POST.copy()
        post_data['account_type'] = auser.account_type
        form = P3BillingData(instance=auser, data=post_data)
        if form.is_valid():
            data = form.cleaned_data
            form.save()
            payment = data['payment']
            o = Order.objects.create(
                user=auser, payment=data['payment'],
                billing_notes=data.get('billing_notes', ''),
                items=request.session['user-cart']['tickets'],
            )
            if o.payment_url:
                return HttpResponseRedirectSeeOther(o.payment_url)
            else:
                return HttpResponseRedirectSeeOther(
                    reverse(
                        'assopy-bank-feedback-ok',
                        kwargs={'code': o.code.replace('/', '-')}
                    )
                )
    else:
        if not request.user.assopy_user.card_name:
            request.user.assopy_user.card_name = request.user.assopy_user.name()
        form = P3BillingData(instance=request.user.assopy_user)
        
    return {
        'tickets': tickets,
        'total': total,
        'form': form,
    }

