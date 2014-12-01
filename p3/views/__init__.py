# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render_to_response, render
from django.template import RequestContext, Template

import p3.forms as p3forms
from p3 import dataaccess
from p3 import models
import assopy.models as amodels
from assopy.forms import RefundItemForm
from assopy.views import render_to, HttpResponseRedirectSeeOther
from conference import forms as cforms
from conference import models as cmodels
from email_template import utils

import logging
import uuid
from collections import defaultdict

log = logging.getLogger('p3.views')

def map_js(request):
    return render_to_response(
        'p3/map.js', {}, context_instance=RequestContext(request), mimetype = 'text/javascript')

@login_required
@render_to('p3/tickets.html')
def tickets(request):
    tickets = dataaccess.user_tickets(request.user, settings.CONFERENCE_CONFERENCE, only_complete=True)
    return {
        'tickets': tickets,
        'refund_form': RefundItemForm(None),
    }

def _reset_ticket(ticket):
    # deleting the name so the ticket will be in the "unfilled tickets" until
    # it's modified.
    ticket.name = ''
    ticket.save()
    try:
        p3c = ticket.p3_conference
    except models.TicketConference.DoesNotExist:
        return
    # resetting default
    p3c.shirt_size = 'l'
    p3c.python_experience = 0
    p3c.diet = 'omnivorous'
    p3c.tagline = ''
    p3c.days = ''
    p3c.save()

def _assign_ticket(ticket, email):
    email = email.strip()
    try:
        recipient = auth.models.User.objects.get(email__iexact=email)
    except auth.models.User.DoesNotExist:
        try:
            # Here I'm using filter + [0] instead of .get because it could happen,
            # even if it shouldn't, that two identities have the same email
            # (e.g. if someone used the same email on multiple remote services
            # but connected these services to two local users).
            # It's not a problem if more identities have the same email (note
            # that the authentication backend already checks that the same email
            # won't be used twice to create django users) because anway they're
            # email validated by external services.
            recipient = amodels.UserIdentity.objects.filter(email__iexact=email)[0].user.user
        except IndexError:
            recipient = None
    if recipient is None:
        from assopy.clients import genro
        rid = genro.users(email)['r0']
        if rid is not None:
            # the email it's not associated to a django user, but genropy
            # knows it. If rid is assigned to an assopy user I'll reuse the
            # connected user. This check works when the ticket is assigned
            # to a user, the user modifies its email but later the ticket
            # is reassigned to the original email.
            try:
                recipient = amodels.User.objects.get(assopy_id=rid).user
            except amodels.User.DoesNotExist:
                pass
            else:
                if recipient.email != email:
                    log.info(
                            'email "%s" found on genropy; but user (%s) have a different email: "%s"',
                        email.encode('utf-8'), unicode(recipient).encode('utf-8'), recipient.email.encode('utf-8'))
                    email = recipient.email
                else:
                    log.info(
                        'email "%s" found on genropy; user (%s)',
                        email.encode('utf-8'), unicode(recipient).encode('utf-8'))

    if recipient is None:
        log.info('No user found for the email "%s"; time to create a new one', email)
        just_created = True
        u = amodels.User.objects.create_user(email=email, token=True, send_mail=False)
        recipient = u.user
        name = email
    else:
        log.info('Found a local user (%s) for the email "%s"', unicode(recipient).encode('utf-8'), email.encode('utf-8'))
        just_created = False
        try:
            auser = recipient.assopy_user
        except amodels.User.DoesNotExist:
            # doh... this django user is not an assopy user, surely something
            # coming from before the introduction of assopy app.
            auser = amodels.User(user=recipient)
            auser.save()
        if not auser.token:
            recipient.assopy_user.token = str(uuid.uuid4())
            recipient.assopy_user.save()
        name = '%s %s' % (recipient.first_name, recipient.last_name)

    _reset_ticket(ticket)

    utils.email(
        'ticket-assigned',
        ctx={
            'name': name,
            'just_created': just_created,
            'ticket': ticket,
            'link': settings.DEFAULT_URL_PREFIX + reverse('p3-user', kwargs={'token': recipient.assopy_user.token}),
        },
        to=[email]
    ).send()
    return email

@login_required
@transaction.commit_on_success
def ticket(request, tid):
    t = get_object_or_404(cmodels.Ticket, pk=tid)
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
        if t.frozen:
            return http.HttpResponseForbidden()

        if 'refund' in request.POST:
            r = amodels.Refund.objects.create_from_orderitem(
                t.orderitem, reason=request.POST['refund'][:200])
            t = cmodels.Ticket.objects.get(id=t.id)
        elif t.fare.ticket_type == 'conference':
            data = request.POST.copy()
            # We want to maximize the number of assigned tickets, and to do
            # this we discurage users from filling in tickets for others.
            # If the ticket is unassigned I'm forcing the name to be the same
            # of the profile.
            #
            # If the user is the one that bought the ticket and it's not assigning
            # it then for this POST I'll use the name of current user.
            if t.user == request.user and not data.get('assigned_to'):
                data['t%d-ticket_name' % t.id] = '%s %s' % (t.user.first_name, t.user.last_name)
            form = p3forms.FormTicket(
                instance=p3c,
                data=data,
                prefix='t%d' % (t.id,),
                single_day=t.fare.code[2] == 'D',
            )
            if not form.is_valid():
                return http.HttpResponseBadRequest(str(form.errors))

            data = form.cleaned_data
            # first of all I'm fixing conference tickets...
            t.name = data['ticket_name'].strip()
            t.save()
            # ...later I take care of extras of tickets p3
            x = form.save(commit=False)
            x.ticket = t
            if t.user != request.user:
                # only the owner can reassign a ticket
                x.assigned_to = assigned_to
            x.save()

            if t.user == request.user:
                old = assigned_to or ''
                new = x.assigned_to or ''
                if old != new:
                    if x.assigned_to:
                        changed = _assign_ticket(t, x.assigned_to)
                        if changed != x.assigned_to:
                            log.info('ticket assigned to "%s" instead of "%s"', changed, x.assigned_to)
                            x.assigned_to = changed
                            x.save()
                        else:
                            log.info('ticket assigned to "%s"', x.assigned_to)
                    else:
                        log.info('ticket reclaimed (previously assigned to "%s")', assigned_to)
                        _reset_ticket(t)

            if t.user != request.user and not request.user.first_name and not request.user.last_name and data['ticket_name']:
                # the user has neither first or last name inthe progle (and also
                # it's not the person who bought the ticket). I can use the name
                # used for the ticket to fill the profile.

                try:
                    f, l = data['ticket_name'].strip().split(' ', 1)
                except ValueError:
                    f = data['ticket_name'].strip()
                    l = ''
                request.user.first_name = f
                request.user.last_name = l
                request.user.save()
        elif t.fare.code in ('SIM01',):
            try:
                sim_ticket = t.p3_conference_sim
            except models.TicketSIM.DoesNotExist:
                sim_ticket = None
            form = p3forms.FormTicketSIM(instance=sim_ticket, data=request.POST, files=request.FILES, prefix='t%d' % (t.id,))
            if not form.is_valid():
                return http.HttpResponseBadRequest(str(form.errors))
            else:
                data = form.cleaned_data
                t.name = data['ticket_name']
                t.save()
                x = form.save(commit=False)
                x.ticket = t
                x.save()
        elif t.fare.code.startswith('H'):
            room_ticket = t.p3_conference_room
            form = p3forms.FormTicketRoom(instance=room_ticket, data=request.POST, files=request.FILES, prefix='t%d' % (t.id,))
            if not form.is_valid():
                return http.HttpResponseBadRequest(str(form.errors))
            else:
                data = form.cleaned_data
                t.name = data['ticket_name']
                t.save()
                x = form.save(commit=False)
                x.ticket = t
                x.save()
        else:
            form = p3forms.FormTicketPartner(instance=t, data=request.POST, prefix='t%d' % (t.id,))
            if not form.is_valid():
                return http.HttpResponseBadRequest(str(form.errors))
            form.save()

    # returning the rendering of the new ticket, so the caller can easily show it
    tpl = Template('{% load p3 %}{% render_ticket t %}')
    return http.HttpResponse(tpl.render(RequestContext(request, {'t': t})))

def user(request, token):
    """
    view che logga automaticamente un utente (se il token è valido) e lo
    ridirige alla pagine dei tickets
    """
    u = get_object_or_404(amodels.User, token=token)
    log.info('autologin (via token url) for "%s"', u.user)
    if not u.user.is_active:
        u.user.is_active = True
        u.user.save()
        log.info('"%s" activated', u.user)
    user = auth.authenticate(uid=u.user.id)
    auth.login(request, user)
    return HttpResponseRedirectSeeOther(reverse('p3-tickets'))

@login_required
@render_to('p3/sprint_submission.html')
def sprint_submission(request):
    if request.method == 'POST':
        form = p3forms.FormSprint(data=request.POST)
        if form.is_valid():
            s = form.save(commit=False)
            s.user = request.user.assopy_user
            s.conference_id = settings.CONFERENCE_CONFERENCE
            s.save()
            messages.info(request, 'Your sprint has been submitted, thank you!')
            return HttpResponseRedirectSeeOther(reverse('p3-sprint-submission'))

    else:
        form = p3forms.FormSprint()
    return {
        'form': form,
    }

@render_to('p3/sprints.html')
def sprints(request):
    events = []
    attendees = defaultdict(list)
    for sp in models.SprintPresence.objects\
                .filter(sprint__conference=settings.CONFERENCE_CONFERENCE)\
                .select_related('user__user'):
        attendees[sp.sprint_id].append(sp.user)
    if request.user.is_authenticated():
        user_attends = set(
           x['sprint'] for x in
           models.SprintPresence.objects\
                .filter(sprint__conference=settings.CONFERENCE_CONFERENCE)\
                .values('sprint')\
                .filter(user=request.user)\
        )
    else:
        user_attends = set()
    for e in models.Sprint.objects.filter(conference=settings.CONFERENCE_CONFERENCE).order_by('title'):
        if request.user.is_superuser or request.user == e.user:
            form = p3forms.FormSprint(instance=e, prefix='f%d' % e.id)
        else:
            form = None
        events.append({
            'object': e,
            'form': form,
            'attendees': attendees.get(e.id, []),
            'user_attend': e.id in user_attends,
        })
    return {
        'events': events,
    }

@login_required
@render_to('p3/render_single_sprint.html')
def sprint(request, sid):
    e = get_object_or_404(models.Sprint, pk=sid)
    if request.method == 'POST':
        if 'user-attend' in request.POST:
            try:
                p = models.SprintPresence.objects.get(sprint=e, user=request.user.assopy_user)
            except models.SprintPresence.DoesNotExist:
                models.SprintPresence(sprint=e, user=request.user.assopy_user).save()
            else:
                p.delete()
        else:
            if request.user != e.user and not request.user.is_superuser:
                return http.HttpResponseForbidden()

            form = p3forms.FormSprint(instance=e, data=request.POST, prefix='f%d' % (e.id,))
            if form.is_valid():
                form.save()
            else:
                return http.HttpResponseBadRequest(repr(form.errors))

    if request.user.is_superuser or request.user == e.user:
        form = p3forms.FormSprint(instance=e, prefix='f%d' % e.id)
    else:
        form = None
    attendees = list(x.user for x in models.SprintPresence.objects.filter(sprint=e).select_related('user__user'))
    return {
        'data': {
            'object': e,
            'form': form,
            'attendees': attendees,
            'user_attend': request.user.id in set(x.user.id for x in attendees),
        },
    }

def whos_coming(request, conference=None):
    if conference is None:
        return redirect('p3-whos-coming-conference', conference=settings.CONFERENCE_CONFERENCE)
    # profiles can be public or only visible for partecipants, in the second
    # case only who has a ticket can see them
    access = ('p',)
    if request.user.is_authenticated():
        t = dataaccess.all_user_tickets(request.user.id, conference)
        if any(tid for tid, _, _, complete in t if complete):
            access = ('m', 'p')

    countries = [('', 'All')] + list(amodels.Country.objects\
        .filter(iso__in=models.P3Profile.objects\
            .filter(profile__visibility__in=access)\
            .exclude(country='')\
            .values('country')
        )\
        .values_list('iso', 'name')\
        .distinct()
    )

    class FormWhosFilter(forms.Form):
        country = forms.ChoiceField(choices=countries, required=False)
        speaker = forms.BooleanField(label="Only speakers", required=False)
        tags = cforms.TagField(
            required=False,
            widget=cforms.ReadonlyTagWidget(),
        )

    qs = cmodels.AttendeeProfile.objects\
        .filter(visibility__in=('m', 'p'))\
        .filter(user__in=dataaccess.conference_users(conference))\
        .values('visibility')\
        .annotate(total=Count('visibility'))
    profiles = {
        'all': sum([ row['total'] for row in qs ]),
        'visible': 0,
    }
    for row in qs:
        if row['visibility'] in access:
            profiles['visible'] += row['total']

    people = cmodels.AttendeeProfile.objects\
        .filter(visibility__in=access)\
        .filter(user__in=dataaccess.conference_users(conference))\
        .values_list('user', flat=True)\
        .order_by('user__first_name', 'user__last_name')

    form = FormWhosFilter(data=request.GET)
    if form.is_valid():
        data = form.cleaned_data
        if data.get('country'):
            people = people.filter(p3_profile__country=data['country'])
        if data.get('tags'):
            qs = cmodels.ConferenceTaggedItem.objects\
                .filter(
                    content_type__app_label='p3', content_type__model='p3profile',
                    tag__name__in=data['tags'])\
                .values('object_id')
            people = people.filter(user__in=qs)
        if data.get('speaker'):
            speakers = cmodels.TalkSpeaker.objects\
                .filter(talk__conference=conference, talk__status='accepted')\
                .values('speaker')
            people = people.filter(user__speaker__in=speakers)

    try:
        ix = max(int(request.GET.get('counter', 0)), 0)
    except:
        ix = 0
    pids = people[ix:ix+10]
    ctx = {
        'profiles': profiles,
        'pids': pids,
        'form': form,
        'conference': conference,
    }
    if request.is_ajax():
        tpl = 'p3/ajax/whos_coming.html'
    else:
        tpl = 'p3/whos_coming.html'
    return render(request, tpl, ctx)

def genro_invoice_pdf(request, assopy_id):
    import urllib
    from assopy.clients import genro
    from assopy.models import OrderItem

    data = genro.invoice(assopy_id)

    conferences = OrderItem.objects\
        .filter(order__assopy_id=data['order_id'])\
        .values_list('ticket__fare__conference', flat=True)\
        .distinct()

    try:
        conference = filter(None, conferences)[0]
    except IndexError:
        raise http.Http404()

    fname = '[%s] invoice.pdf' % (conference,)
    f = urllib.urlopen(genro.invoice_url(assopy_id))
    response = http.HttpResponse(f, mimetype='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="%s"' % fname
    return response

from p3.views.cart import *
from p3.views.live import *
from p3.views.profile import *
from p3.views.schedule import *
from p3.views.reports import *
