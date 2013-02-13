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

import forms as p3forms
import p3
from p3 import dataaccess
from p3 import models
import assopy.models as amodels
from assopy.forms import BillingData
from assopy.views import render_to, render_to_json, HttpResponseRedirectSeeOther
from conference import forms as cforms
from conference import models as cmodels
from conference.views import profile_access, json_dumps
from conference.utils import TimeTable2
from email_template import utils

import datetime
import logging
import mimetypes
import os.path
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
    }

def _reset_ticket(ticket):
    # cancello il nome così il ticket compare nelle statistiche "biglietti non
    # compilati" fino a quando non viene modificato
    ticket.name = ''
    ticket.save()
    try:
        p3c = ticket.p3_conference
    except models.TicketConference.DoesNotExist:
        return
    # reimposto i default
    p3c.shirt_size = 'l'
    p3c.python_experience = 0
    p3c.diet = 'omnivorous'
    p3c.tagline = ''
    p3c.days = ''
    p3c.save()

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
            recipient = amodels.UserIdentity.objects.filter(email=email)[0].user.user
        except IndexError:
            recipient = None
    if recipient is None:
        from assopy.clients import genro
        rid = genro.users(email)['r0']
        if rid is not None:
            # l'email non è associata ad un utente django ma genropy la
            # conosce.  Se rid è assegnato ad un utente assopy riutilizzo
            # l'utente collegato.  Questo check funziona quando un biglietto
            # viene assegnato ad un utente, quest'ultimo cambia email ma poi il
            # biglietto viene riassegnato nuovamente all'email originale.
            try:
                recipient = amodels.User.objects.get(assopy_id=rid).user
            except amodels.User.DoesNotExist:
                pass
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
            # uff, ho un utente su django che non è un assopy user, sicuramente
            # strascichi prima dell'introduzione dell'app assopy
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
            if t.user == request.user and not data.get('assigned_to'):
                # vogliamo massimizzare il numero dei biglietti assegnati, e
                # per farlo scoraggiamo le persone nel compilare i biglietti di
                # altri. Se il biglietto non è assegnato lo forzo ad avere lo
                # stesso nome del profilo.
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
            # prima di tutto sistemo il ticket di conference...
            t.name = data['ticket_name'].strip()
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
                    _reset_ticket(t)

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

    # restituisco il rendering del nuovo biglietto, così il chiamante può
    # mostrarlo facilmente
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

@render_to('p3/cart.html')
def cart(request):
    try:
        u = request.user.assopy_user
        at = u.account_type
    except AttributeError:
        u = None
        at = None

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
    return {
        'form': form,
        'fares': fares,
        'fares_ordered': fares_ordered,
        'account_type': at,
    }

@login_required
@render_to('p3/billing.html')
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

    class P3BillingData(BillingData):
        card_name = forms.CharField(
            label='Your Name' if recipient != 'c' else 'Company Name',
            max_length=200,
        )
        payment = forms.ChoiceField(choices=amodels.ORDER_PAYMENT, initial='paypal')
        code_conduct = forms.BooleanField(label='I have read and accepted the <a class="trigger-overlay" href="/code-of-conduct" target="blank">code of conduct</a>.')

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

    coupon = request.session['user-cart']['coupon']
    totals = amodels.Order.calculator(items=tickets, coupons=[coupon] if coupon else None, user=request.user.assopy_user)

    if request.method == 'POST':
        # non voglio che attraverso questa view sia possibile cambiare il tipo
        # di account company/private
        auser = request.user.assopy_user
        post_data = request.POST.copy()
        post_data['account_type'] = auser.account_type

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
                form = P3BillingData(instance=auser, data=post_data)
                form.is_valid()
        else:
            form = P3BillingData(instance=auser, data=post_data)
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
                        kwargs={'code': o.code.replace('/', '-')}
                    )
                )
    else:
        if not request.user.assopy_user.card_name:
            request.user.assopy_user.card_name = request.user.assopy_user.name()
        form = P3BillingData(instance=request.user.assopy_user)

    return {
        'totals': totals,
        'form': form,
    }

def _conference_timetables(conference):
    """
    Restituisce le TimeTable relative alla conferenza.
    """
    # Le timetable devono contenere sia gli eventi presenti nel db sia degli
    # eventi "artificiali" del partner program

    sids = cmodels.Schedule.objects\
        .filter(conference=conference)\
        .values('id', 'date')

    from conference.templatetags.conference import fare_blob
    from conference.dataaccess import fares
    partner = defaultdict(list)
    for f in [ f for f in fares(conference) if f['ticket_type'] == 'partner' ]:
        d = datetime.datetime.strptime(fare_blob(f, 'date'), '%Y/%m/%d').date()
        t = datetime.datetime.strptime(fare_blob(f, 'departure'), '%H:%M').time()
        partner[d].append({
            'duration': int(fare_blob(f, 'duration')),
            'name': f['name'],
            'id': f['id'] * -1,
            'abstract': f['description'],
            'fare': f['code'],
            'schedule_id': None,
            'tags': set(['partner-program']),
            'time': datetime.datetime.combine(d, t),
            'tracks': ['partner0'],
        })
    tts = []
    for row in sids:
        tt = TimeTable2.fromSchedule(row['id'])
        for e in partner[row['date']]:
            e['schedule_id'] = row['id']
            tt.addEvents([e])
        tts.append((row['id'], tt))
    return tts

@render_to('p3/schedule.html')
def schedule(request, conference):
    tts = _conference_timetables(conference)
    return {
        'conference': conference,
        'sids': [ x[0] for x in tts ],
        'timetables': tts,
    }

def schedule_ics(request, conference, mode='conference'):
    if mode == 'my-schedule':
        if not request.user.is_authenticated():
            raise http.Http404()
        uid = request.user.id
    else:
        uid = None
    from p3.utils import conference2ical
    cal = conference2ical(conference, user=uid, abstract='abstract' in request.GET)
    return http.HttpResponse(list(cal.encode()), content_type='text/calendar')

@render_to('p3/schedule_list.html')
def schedule_list(request, conference):
    sids = cmodels.Schedule.objects\
        .filter(conference=conference)\
        .values_list('id', flat=True)
    return {
        'conference': conference,
        'sids': sids,
        'timetables': zip(sids, map(TimeTable2.fromSchedule, sids)),
    }

@login_required
def jump_to_my_schedule(request):
    return redirect('p3-schedule-my-schedule', conference=settings.CONFERENCE_CONFERENCE)

@login_required
@render_to('p3/my_schedule.html')
def my_schedule(request, conference):
    qs = cmodels.Event.objects\
        .filter(eventinterest__user=request.user, eventinterest__interest__gt=0)\
        .filter(schedule__conference=conference)\
        .values('id', 'schedule')

    events = defaultdict(list)
    for x in qs:
        events[x['schedule']].append(x['id'])

    sids = sorted(events.keys())
    timetables = [ TimeTable2.fromEvents(x, events[x]) for x in sids ]
    return {
        'conference': conference,
        'sids': sids,
        'timetables': zip(sids, timetables),
    }

@render_to_json
def schedule_search(request, conference):
    from haystack.query import SearchQuerySet
    sqs = SearchQuerySet().models(cmodels.Event).auto_query(request.GET.get('q')).filter(conference=conference)
    return [ { 'pk': x.pk, 'score': x.score, } for x in sqs ]

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

def secure_media(request, path):
    if not (request.user.is_superuser or request.user.groups.filter(name__in=('sim_report', 'hotel_report')).exists()):
        fname = os.path.splitext(os.path.basename(path))[0]
        if fname.rsplit('-', 1)[0] != request.user.username:
            return http.HttpResponseForbidden()
    fpath = settings.SECURE_STORAGE.path(path)
    guessed = mimetypes.guess_type(fpath)
    try:
        r = http.HttpResponse(file(fpath), mimetype=guessed[0])
        r['Content-Length'] = os.path.getsize(fpath)
        if guessed[1]:
            r['Content-Encoding'] = guessed[1]
        return r
    except IOError, e:
        if e.errno == 2:
            raise http.Http404()
        else:
            raise

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

@login_required
@render_to('p3/sim_report.html')
def sim_report(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='sim_report').exists()):
        return http.HttpResponseForbidden()
    tickets = cmodels.Ticket.objects.filter(
        orderitem__order___complete=True,
        fare__in=cmodels.Fare.objects.filter(
            code__startswith='SIM', conference=settings.CONFERENCE_CONFERENCE),
    ).order_by('orderitem__order').select_related('p3_conference_sim')
    if request.method == 'POST':
        t = tickets.get(id=request.POST['ticket'])
        t.frozen = not t.frozen
        t.save()
    compiled = dict(std=0, micro=0)
    for t in tickets:
        if t.p3_conference_sim and t.p3_conference_sim.document:
            compiled[t.p3_conference_sim.sim_type] += 1
    return {
        'tickets': tickets,
        'compiled': compiled,
    }

@login_required
@render_to('p3/hotel_report.html')
def hotel_report(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='hotel_report').exists()):
        return http.HttpResponseForbidden()
    tickets = models.TicketRoom.objects\
        .valid_tickets()\
        .select_related('ticket__fare', 'ticket__orderitem')\
        .order_by('ticket__orderitem__order')
    if request.method == 'POST':
        t = tickets.get(id=request.POST['ticket'])
        t.frozen = not t.frozen
        t.save()
    grouped = {
        'rooms': {},
        'beds': {},
    }
    omap = defaultdict(lambda: 0)
    for t in tickets:
        fcode = t.ticket.fare.code
        if fcode[2] == '1':
            key = '0single'
        elif fcode[2] == '2':
            key = '1double'
        elif fcode[2] == '3':
            key = '2triple'
        elif fcode[2] == '4':
            key = '3quadruple'
        if fcode[1] == 'R':
            g = grouped['rooms']
            if key not in g:
                g[key] = {}

            # oid/order_key servono solo a raggruppare graficamente i biglietti
            # per la stessa camera
            oid = '%s:%s' % (t.ticket.orderitem.order_id, fcode)
            order_key = oid + ('_%d' % (omap[oid] / int(fcode[2])))
            omap[oid] += 1
            if order_key not in g[key]:
                g[key][order_key] = []
            g[key][order_key].append(t)
        else:
            g = grouped['beds']
            if key not in g:
                g[key] = {}
            period = (t.checkin, t.checkout)
            if period not in g[key]:
                g[key][period] = []
            g[key][period].append(t)

    rooms = []
    for type, orders in sorted(grouped['rooms'].items()):
        rooms.append((type[1:], sorted(orders.items(), key=lambda x: (x[1][0].checkin, x[1][0].ticket.name))))

    beds = []
    for type, periods in sorted(grouped['beds'].items()):
        beds.append((type[1:], sorted(periods.items(), key=lambda x: x[0][0])))
    return {
        'rooms': rooms,
        'beds': beds,
    }

@profile_access
def p3_profile(request, slug, profile=None, full_access=False, format_='html'):
    if format_ == 'json':
        pdata = dataaccess.profile_data(profile.user_id)
        from conference.templatetags.conference import markdown2
        pdata['bio'] = markdown2(pdata['bio'], "smarty-pants,code-color")
        return http.HttpResponse(
            json_dumps(pdata),
            content_type='text/javascript')
    tpl = 'conference/profile_publicdata_form.html'
    if request.method == 'POST':
        section = request.POST.get('section')
        if section == 'public-data':
            fc = p3forms.P3ProfilePublicDataForm
            tpl = 'conference/profile_publicdata_form.html'
        elif section == 'bio':
            fc = p3forms.P3ProfileBioForm
            tpl = 'conference/profile_bio_form.html'
        elif section == 'visibility':
            fc = p3forms.P3ProfileVisibilityForm
            tpl = 'conference/profile_visibility_form.html'
        elif section == 'picture':
            fc = p3forms.P3ProfilePictureForm
            tpl = 'conference/profile_picture_form.html'
        else:
            fc = p3forms.P3ProfileForm
        form = fc(instance=profile, data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
    else:
        form = p3forms.P3ProfileForm(instance=profile)
    ctx = {
        'form': form,
        'full_access': full_access,
        'profile': profile,
    }
    return render(request, tpl, ctx)

def p3_profile_avatar(request, slug):
    p = get_object_or_404(cmodels.AttendeeProfile, slug=slug).p3_profile
    from urllib2 import urlopen
    try:
        img = urlopen(p.profile_image_url(anonymous=False))
    except Exception:
        path = os.path.join(os.path.dirname(p3.__file__), 'static', settings.P3_ANONYMOUS_AVATAR)
        img = file(path)
        ct = 'image/jpg'
    else:
        headers = img.info()
        ct = headers.get('content-type')
    return http.HttpResponse(img.read(), content_type=ct)

@login_required
@render_to_json
def p3_profile_message(request, slug):
    if request.method != 'POST':
        return http.HttpResponseNotAllowed(('POST',))

    class MessageForm(forms.Form):
        subject = forms.CharField()
        message = forms.CharField()

    f = MessageForm(data=request.POST)
    if f.is_valid():
        data = f.cleaned_data
        profile = get_object_or_404(cmodels.AttendeeProfile, slug=slug)
        try:
            profile.p3_profile.send_user_message(request.user, data['subject'], data['message'])
        except ValueError, e:
            return http.HttpResponseBadRequest(str(e))
        return "OK"
    return f.errors

@login_required
def p3_account_data(request):
    ctx = {}
    if request.method == 'POST':
        profile = cmodels.AttendeeProfile.objects.getOrCreateForUser(request.user)
        form = p3forms.P3ProfilePersonalDataForm(instance=profile, data=request.POST)
        ctx['pform'] = form
        if form.is_valid():
            form.save()
            data = form.cleaned_data
            request.user.first_name = data['first_name']
            request.user.last_name = data['last_name']
            request.user.save()
            if profile.slug[0] == '-':
                slug = cmodels.AttendeeProfile.objects.findSlugForUser(request.user)
                if slug and slug[0] != '-':
                    profile.slug = slug
                    profile.save()
    return render(request, "assopy/profile_personal_data.html", ctx)

@transaction.commit_on_success
def OTCHandler_E(request, token):
    user = token.user
    models.TicketConference.objects\
        .filter(assigned_to=user.email)\
        .update(assigned_to=token.payload)
    user.email = token.payload
    user.save()
    log.info('"%s" has verified the new email "%s"', user.username, user.email)
    return redirect('assopy-profile')

@login_required
def p3_account_email(request):
    ctx = {}
    if request.method == 'POST':
        form = p3forms.P3ProfileEmailContactForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            if email != request.user.email:
                log.info(
                    'requested an email change from "%s" to "%s" for the user "%s"',
                    request.user.email,
                    email,
                    request.user.username,)
                utils.email(
                    'verify-account',
                    ctx={
                        'user': request.user,
                        'token': amodels.Token.objects.create(ctype='e', user=request.user, payload=email),
                    },
                    to=[email]
                ).send()
    return render(request, "assopy/profile_email_contact.html", ctx)

@login_required
def p3_account_spam_control(request):
    ctx = {}
    if request.method == 'POST':
        profile = cmodels.AttendeeProfile.objects.getOrCreateForUser(request.user)
        form = p3forms.P3ProfileSpamControlForm(instance=profile.p3_profile, data=request.POST)
        if form.is_valid():
            form.save()
    return render(request, "assopy/profile_spam_control.html", ctx)

def whos_coming(request, conference=None):
    if conference is None:
        return redirect('p3-whos-coming-conference', conference=settings.CONFERENCE_CONFERENCE)
    # i profili possono essere o pubblici o accessibili solo ai partecipanti,
    # nel secondo caso li possono vedere solo chi ha un biglietto.
    access = ('p',)
    if request.user.is_authenticated():
        tickets = [ tid for tid, _, _, complete in dataaccess.all_user_tickets(request.user.id, conference) if complete ]
        if len(tickets):
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
        'all': qs[0]['total'] + qs[1]['total'],
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

def _live_conference():
    conf = cmodels.Conference.objects.current()
    if not conf.conference():
        if not settings.DEBUG:
            raise http.Http404()
        else:
            wday = datetime.date.today().weekday()
            date = conf.conference_start
            while date <= conf.conference_end:
                if date.weekday() == wday:
                    break
                date = date + datetime.timedelta(days=1)
    else:
        date = datetime.date.today()
    return conf, date

@render_to('p3/live.html')
def live(request):
    """
    What's up doc?
    """
    conf, date = _live_conference()

    tracks = cmodels.Track.objects\
        .filter(track__in=settings.P3_LIVE_TRACKS.keys(), schedule__date=date)\
        .order_by('order')
    return {
        'tracks': tracks,
    }

@render_to('p3/live_track.html')
def live_track(request, track):
    return {}

@render_to_json
def live_track_events(request, track):
    conf, date = _live_conference()

    tid = cmodels.Track.objects\
        .get(track=track, schedule__date=date).id
    tt = TimeTable2.fromTracks([tid])
    output = []
    for _, events in tt.iterOnTracks():
        for e in events:
            if e.get('talk'):
                speakers = ', '.join([ x['name'] for x in e['talk']['speakers']])
            else:
                speakers = None
            output.append({
                'name': e['name'],
                'time': e['time'],
                'duration': e['duration'],
                'tags': e['tags'],
                'speakers': speakers,
            })
    return output

@render_to_json
def live_events(request):
    conf, date = _live_conference()
    sid = cmodels.Schedule.objects\
        .values('id')\
        .get(conference=conf.code, date=date)

    tt = TimeTable2.fromSchedule(sid['id'])
    tt.removeEventsByTag('special')
    t0 = datetime.datetime.now().time()

    tracks = settings.P3_LIVE_TRACKS.keys()
    events = {}
    for track, tevts in tt.iterOnTracks(start=('current', t0)):
        curr = None
        try:
            curr = dict(tevts[0])
            curr['next'] = dict(tevts[1])
        except IndexError:
            pass
        # Ho eliminato gli eventi special, t0 potrebbe cadere su uno di questi
        if curr and (curr['time'] + datetime.timedelta(seconds=curr['duration']*60)).time() < t0:
            curr = None

        if track not in tracks:
            continue
        events[track] = curr

    def event_url(event):
        if event.get('talk'):
            return reverse('conference-talk', kwargs={'slug': event['talk']['slug']})
        else:
            return None

    output = {}
    for track, event in events.items():
        if event is None:
            output[track] = {
                'id': None,
                'embed': settings.P3_LIVE_EMBED(request, track=track),
            }
            continue
        url = event_url(event)
        if event.get('talk'):
            speakers = [
                (
                    reverse('conference-speaker', kwargs={'slug': s['slug']}),
                    s['name'],
                    dataaccess.profile_data(s['id'])['image']
                )
                for s in event['talk']['speakers']
            ]
        else:
            speakers = None
        if event.get('next'):
            next = {
                'name': event['next']['name'],
                'url': event_url(event['next']),
                'time': event['next']['time'],
            }
        else:
            next = None
        output[track] = {
            'id': event['id'],
            'name': event['name'],
            'url': url,
            'speakers': speakers,
            'start': event['time'],
            'end': event['time'] + datetime.timedelta(seconds=event['duration'] * 60),
            'tags': event['talk']['tags'] if event.get('talk') else [],
            'embed': settings.P3_LIVE_EMBED(request, event=event),
            'next': next,
        }
    return output

def genro_invoice_pdf(request, assopy_id):
    import urllib
    from assopy.clients import genro
    from assopy.models import OrderItem

    data = genro.invoice(assopy_id)

    try:
        item = OrderItem.objects\
            .filter(order__assopy_id=data['order_id'])\
            .select_related('ticket__fare')[0]
    except IndexError:
        raise http.Http404()

    conference = item.ticket.fare.conference

    fname = '[%s] invoice.pdf' % (conference,)
    f = urllib.urlopen(genro.invoice_url(assopy_id))
    response = http.HttpResponse(f, mimetype='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="%s"' % fname
    return response
