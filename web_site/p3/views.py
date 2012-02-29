# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render_to_response, render
from django.template import RequestContext, Template

import forms as p3forms
import models
import assopy.models as amodels
from assopy.forms import BillingData
from assopy.views import render_to, render_to_json, HttpResponseRedirectSeeOther
from conference.models import Fare, Event, Ticket, Schedule, Speaker, AttendeeProfile
from conference.views import profile_access
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
        if order.method not in ('bank', 'admin') and not _get_cached_order_status(request, order.id):
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
            recipient = amodels.UserIdentity.objects.filter(email=email)[0].user.user
        except IndexError:
            recipient = None
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
        name = recipient.assopy_user.name()
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
        if t.frozen:
            return http.HttpResponseForbidden()

        if t.fare.ticket_type == 'conference':
            form = p3forms.FormTicket(
                instance=p3c,
                data=request.POST,
                prefix='t%d' % (t.id,),
                single_day=t.fare.code[2] == 'D',
            )
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

from assopy.forms import FormTickets
class P3FormTickets(FormTickets):
    coupon = forms.CharField(
        label='Insert your discount code and save money!',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'size': 10}),
    )
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(P3FormTickets, self).__init__(*args, **kwargs)
        del self.fields['payment']

    def clean_coupon(self):
        data = self.cleaned_data.get('coupon', '').strip()
        if not data:
            return None
        if data[0] == '_':
            raise forms.ValidationError('invalid coupon')
        try:
            coupon = amodels.Coupon.objects.get(code__iexact=data)
        except amodels.Coupon.DoesNotExist:
            raise forms.ValidationError('invalid coupon')
        if not coupon.valid(self.user):
            raise forms.ValidationError('invalid coupon')
        return coupon

    def clean(self):
        data = super(P3FormTickets, self).clean()
        order_type = data['order_type']
        company = order_type == 'deductible'
        for ix, row in list(enumerate(data['tickets']))[::-1]:
            fare, quantity = row
            if fare.ticket_type != 'company':
                continue
            if (company ^ (fare.code[-1] == 'C')):
                del data['tickets'][ix]
                del data[fare.code]
        return data

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
        form = P3FormTickets(data=request.POST, user=u)
        if form.is_valid():
            request.session['user-cart'] = form.cleaned_data
            return redirect('p3-billing')
    else:
        form = P3FormTickets(initial={
            'order_type': 'deductible' if at == 'c' else 'non-deductible',
        })
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
        'totals': totals,
        'form': form,
    }

@render_to('p3/schedule.html')
def schedule(request, conference):
    from conference.forms import EventForm
    schedules = Schedule.objects.filter(conference=conference)
    try:
        form = EventForm(schedule=schedules[0])
    except IndexError:
        raise http.Http404()
    return {
        'conference': conference,
        'schedules': schedules,
        'form': form,
    }

@render_to('p3/schedule_list.html')
def schedule_list(request, conference):
    qs = Event.objects\
        .filter(schedule__conference=conference)\
        .select_related('schedule', 'talk')

    events = []
    for e in qs:
        if 'partner' not in e.track:
            events.append({
                'time': datetime.datetime.combine(e.schedule.date, e.start_time),
                'event': e,
            })
    return {
        'conference': conference,
        'events': events,
    }

@render_to('p3/schedule_speakers.html')
def schedule_speakers(request, conference):
    events = Event.objects\
        .filter(schedule__conference=settings.CONFERENCE_CONFERENCE)\
        .exclude(talk=None)\
        .select_related('schedule', 'track', 'talk')
    tmap = defaultdict(list)
    for x in events:
        tmap[x.talk_id].append(x)

    speakers = Speaker.objects\
                .filter(talkspeaker__talk__in=tmap.keys())\
                .select_related('user')\
                .extra(select={'talk_id': 'conference_talkspeaker.talk_id'})

    data = {}
    for s in speakers:
        if s.id not in data:
            data[s.id] = {
                'speaker': s,
                'events': [],
            }
        data[s.id]['events'].extend(tmap[s.talk_id])

    speakers_sorted = sorted(
        data.values(),
        key=lambda x: '%s %s' % (x['speaker'].user.first_name, x['speaker'].user.last_name)
    )
    return {
        'speakers': speakers_sorted,
    }

@login_required
@render_to('p3/my_schedule.html')
def my_schedule(request):
    qs = Event.objects\
        .filter(eventinterest__user=request.user, eventinterest__interest__gt=0)\
        .filter(schedule__conference=settings.CONFERENCE_CONFERENCE)\
        .select_related('schedule', 'talk')

    events = []
    for e in qs:
        events.append({
            'time': datetime.datetime.combine(e.schedule.date, e.start_time),
            'event': e,
        })
    return {
        'conference': settings.CONFERENCE_CONFERENCE,
        'events': events,
    }

@render_to_json
def schedule_search(request, conference):
    from haystack.query import SearchQuerySet
    sqs = SearchQuerySet().models(Event).auto_query(request.GET.get('q')).filter(conference=conference)
    return [ { 'pk': x.pk, 'score': x.score, } for x in sqs ]

@login_required
@render_to_json
def calculator(request):
    output = {
        'tickets': 0,
        'coupon': 0,
    }
    if request.method == 'POST':
        form = P3FormTickets(data=request.POST, user=request.user.assopy_user)
        if not form.is_valid():
            # se la form non valida a causa del coupon lo elimino dai dati per
            # dare cmq un feedback all'utente
            if 'coupon' in form.errors:
                qdata = request.POST.copy()
                del qdata['coupon']
                form = P3FormTickets(data=qdata, user=request.user.assopy_user)
        if form.is_valid():
            data = form.cleaned_data
            coupons = []
            if data['coupon']:
                coupons.append(data['coupon'])
            totals = amodels.Order.calculator(items=data['tickets'], coupons=coupons, user=request.user.assopy_user)
            output['tickets'] = sum(x[0] for x in totals['tickets'].values())
            if data['coupon']:
                output['coupon'] = totals['coupons'][data['coupon'].code][0]
        else:
            # report form.errors ?
            pass

    output['total'] = sum(output.values())
    for k, v in output.items():
        if v == 0:
            # v è un Decimal e ottengo una rappresentazione diversa tra 0 e -0
            output[k] = '0'
        else:
            output[k] = '%.2f' % v
    return output

def secure_media(request, path):
    if not (request.user.is_superuser or request.user.groups.filter(name='sim_report').exists()):
        fname = os.path.splitext(os.path.basename(path))[0]
        if fname.rsplit('-', 1)[0] != request.user.username:
            return http.HttpResponseForbidden()
    fpath = settings.SECURE_STORAGE.path(path)
    try:
        return http.HttpResponse(file(fpath), mimetype=mimetypes.guess_type(fpath))
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
    tickets = Ticket.objects.filter(
        orderitem__order___complete=True,
        fare__in=Fare.objects.filter(code__startswith='SIM'),
    ).order_by('orderitem__order').select_related('p3_conference_sim')
    if request.method == 'POST':
        t = tickets.get(id=request.POST['ticket'])
        t.frozen = not t.frozen
        t.save()
    return {
        'tickets': tickets,
    }

@profile_access
def p3_profile(request, slug, profile=None, full_access=False):
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
    }
    return render(request, tpl, ctx)

@login_required
def p3_account_data(request):
    ctx = {}
    if request.method == 'POST':
        profile = AttendeeProfile.objects.getOrCreateForUser(request.user)
        form = p3forms.P3ProfilePersonalDataForm(instance=profile, data=request.POST)
        ctx['pform'] = form
        if form.is_valid():
            form.save()
            data = form.cleaned_data
            request.user.first_name = data['first_name']
            request.user.last_name = data['last_name']
            request.user.save()
    return render(request, "assopy/profile_personal_data.html", ctx)

def OTCHandler_E(request, token):
    user = token.user
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
                utils.email(
                    'verify-account',
                    ctx={
                        'user': request.user,
                        'token': amodels.Token.objects.create(ctype='e', user=request.user, payload=email),
                    },
                    to=[email]
                ).send()
    return render(request, "assopy/profile_email_contact.html", ctx)
