# -*- coding: UTF-8 -*-
from django import http
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string

from assopy.models import User, UserIdentity
from assopy.views import render_to, HttpResponseRedirectSeeOther

import forms
import models
from conference.models import Ticket

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
    return {
        'tickets': tickets,
    }

def _assign_ticket(ticket, email):
    try:
        recipient = auth.models.User.objects.get(email=email)
    except auth.models.User.DoesNotExist:
        try:
            # qui uso filter + [0] invece che .get perchè potrebbe accadere
            # anche se non dovrebbe che due identità abbiano la stessa email
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
        if not recipient.assopy_user.token:
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
    t = get_object_or_404(Ticket, user=request.user, pk=tid)
    if request.method == 'POST':
        if t.fare.ticket_type == 'conference':
            try:
                p3c = t.p3_conference
                assigned_to = p3c.assigned_to
            except models.TicketConference.DoesNotExist:
                p3c = None
                assigned_to = None
        form = forms.FormTicket(instance=p3c, data=request.POST, prefix='t%d' % (t.id,))
        if not form.is_valid():
            return http.HttpResponseBadRequest()
        data = form.cleaned_data
        t.name = data['ticket_name']
        t.save()
        x = form.save(commit=False)
        x.ticket = t
        if assigned_to != x.assigned_to:
            if x.assigned_to:
                log.info('ticket assigned to "%s"', x.assigned_to)
                _assign_ticket(t, x.assigned_to)
            else:
                log.info('ticket reclaimed (previously assigned to "%s")', assigned_to)
        x.save()
    return HttpResponseRedirectSeeOther(reverse('p3-tickets'))

def user(request, token):
    """
    view che logga automaticamente un utente (se il token è valido) e lo
    ridirige alla pagine dei tickets 
    """
    u = get_object_or_404(User, token=token)
    if not u.verified:
        u.verified = True
        u.save()
    user = auth.authenticate(uid=u.user.id)
    auth.login(request, user)
    return HttpResponseRedirectSeeOther(reverse('p3-tickets'))
