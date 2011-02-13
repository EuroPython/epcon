# -*- coding: UTF-8 -*-
from django import http
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from assopy.models import UserIdentity
from assopy.views import render_to, HttpResponseRedirectSeeOther

import forms
import models
from conference.models import Ticket

import logging

log = logging.getLogger('p3.views')

def map_js(request):
    return render_to_response(
        'p3/map.js', {}, context_instance=RequestContext(request), mimetype = 'text/javascript')

@login_required
@render_to('p3/tickets.html')
def tickets(request):
    tickets = request.user.ticket_set.conference(settings.CONFERENCE_CONFERENCE)
    return {
        'tickets': tickets,
    }

def _assign_ticket(attendee, email):
    try:
        recipient = auth.models.User.objects(email=email)
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
            recipient = UserIdentity.objects.filter(email=email)[0]
        except IndexError:
            recipient = None
    if recipient is None:
        log.info('No user found for the email "%s"; time to create a new one', email)
    else:
        log.info('Found a local user (%s) for the email "%s"', user, email)
    ctx = {
        'recipient': recipient,
        'attendee': attendee,
        'conference': 'Europython 2011',
    }
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
