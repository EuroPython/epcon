# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import mimetypes
import os
import os.path
import re
import random
import sys
import urllib
from collections import defaultdict
from datetime import datetime
from itertools import groupby

from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from conference import dataaccess as cdataaccess
from conference import models as ConferenceModels
from conference.settings import STUFF_DIR, STUFF_URL

from assopy import models as amodels
from p3 import dataaccess
from p3 import forms as p3forms
from p3 import models

from fancy_tag import fancy_tag

mimetypes.init()

register = template.Library()

@register.inclusion_tag('p3/box_pycon_italia.html')
def box_pycon_italia():
    return {}

@register.inclusion_tag('p3/box_newsletter.html', takes_context=True)
def box_newsletter(context):
    return context

@register.inclusion_tag('p3/box_cal.html', takes_context = True)
def box_cal(context, limit=None):
    deadlines = ConferenceModels.Deadline.objects.valid_news()
    if limit:
        deadlines = deadlines[:int(limit)]
    return {
        'deadlines': [ (d, d.content(context['LANGUAGE_CODE'])) for d in deadlines ]
    }

@register.inclusion_tag('p3/render_cal.html', takes_context=True)
def render_cal(context):
    return context

@register.inclusion_tag('p3/box_download.html', takes_context = True)
def box_download(context, fname, label=None):
    if '..' in fname:
        raise template.TemplateSyntaxError("file path cannot contains ..")
    if fname.startswith('/'):
        raise template.TemplateSyntaxError("file path cannot starts with /")
    if label is None:
        label = os.path.basename(fname)
    try:
        fpath = os.path.join(settings.STUFF_DIR, fname)
        stat = os.stat(fpath)
    except (AttributeError, OSError), e:
        fsize = ftype = None
    else:
        fsize = stat.st_size
        ftype = mimetypes.guess_type(fpath)[0]

    return {
        'url': context['STUFF_URL'] + fname,
        'label': label,
        'fsize': fsize,
        'ftype': ftype,
    }

@register.inclusion_tag('p3/box_didyouknow.html', takes_context = True)
def box_didyouknow(context):
    try:
        d = ConferenceModels.DidYouKnow.objects.filter(visible = True).order_by('?')[0]
    except IndexError:
        d = None
    return {
        'd': d,
        'LANGUAGE_CODE': context.get('LANGUAGE_CODE'),
    }

@register.inclusion_tag('p3/box_googlemaps.html', takes_context = True)
def box_googlemaps(context, what='', zoom=13):
    what = ','.join([ "'%s'" % w for w in what.split(',') ])
    return {
        'rand': random.randint(0, sys.maxint - 1),
        'what': what,
        'zoom': zoom
    }

@register.inclusion_tag('p3/box_talks_conference.html', takes_context = True)
def box_talks_conference(context, talks):
    """
    mostra i talk passati raggruppati per conferenza
    """
    conf = defaultdict(list)
    for t in talks:
        conf[t.conference].append(t)

    talks = []
    for c in reversed(sorted(conf.keys())):
        talks.append((c, conf[c]))

    return { 'talks': talks }

@register.inclusion_tag('p3/box_latest_tweets.html', takes_context=True)
def box_latest_tweets(context):
    ctx = Context(context)
    ctx.update({
        'screen_name': settings.P3_TWITTER_USER,
    })
    return ctx

@register.filter
def render_time(tweet, args=None):
    time = tweet["timestamp"]
    time = datetime.datetime.fromtimestamp(time)
    return time.strftime("%d-%m-%y @ %H:%M") 

@register.filter
def check_map(page):
    """
    controlla se la pagina passata richiede o meno una mappa
    """
    if page:
        return '{% render_map' in page.expose_content()
    return False

@register.inclusion_tag('p3/render_map.html', takes_context=True)
def render_map(context):
    return {}

@register.inclusion_tag('p3/fragments/render_ticket.html', takes_context=True)
def render_ticket(context, ticket):
    from p3 import forms
    user = context['request'].user
    if ticket.fare.ticket_type == 'conference':
        try:
            inst = ticket.p3_conference
        except:
            inst = None
        form = forms.FormTicket(
            instance=inst,
            initial={
                'ticket_name': ticket.name,
            },
            prefix='t%d' % (ticket.id,),
            single_day=ticket.fare.code[2] == 'D',
        )
        if inst and inst.assigned_to:
            blocked = inst.assigned_to != user.email
        else:
            blocked = False
    elif ticket.fare.code in ('SIM01',):
        try:
            inst = ticket.p3_conference_sim
        except:
            inst = None
        form = forms.FormTicketSIM(
            instance=inst,
            initial={
                'ticket_name': ticket.name,
            },
            prefix='t%d' % (ticket.id,),
        )
        blocked = False
    elif ticket.fare.code.startswith('H'):
        # le instanze di TicketRoom devono esistere, ci pensa un listener a
        # crearle
        inst = ticket.p3_conference_room
        form = forms.FormTicketRoom(
            instance=inst,
            initial={
                'ticket_name': ticket.name,
            },
            prefix='t%d' % (ticket.id,),
        )
        blocked = False
    else:
        form = forms.FormTicketPartner(instance=ticket, prefix='t%d' % (ticket.id,))
        blocked = False
    ctx = Context(context)
    ctx.update({
        'ticket': ticket,
        'form': form,
        'user': user,
        'blocked': blocked,
    })
    return ctx

@register.assignment_tag
def fares_available(fare_type, sort=None):
    """
    Restituisce l'elenco delle tariffe attive in questo momento per la
    tipologia specificata.
    """
    assert fare_type in ('all', 'conference', 'goodies', 'partner', 'hotel-room', 'hotel-room-sharing', 'other')

    fares_list = filter(lambda f: f['valid'], cdataaccess.fares(settings.CONFERENCE_CONFERENCE))
    if fare_type == 'conference':
        fares = [ f for f in fares_list if f['code'][0] == 'T' and f['ticket_type'] == 'conference' ]
    elif fare_type == 'hotel-room-sharing':
        fares = [ f for f in fares_list if f['code'].startswith('HB') ]
    elif fare_type == 'hotel-room':
        fares = [ f for f in fares_list if f['code'].startswith('HR') ]
    elif fare_type == 'other':
        fares = [ f for f in fares_list if f['ticket_type'] in ('other', 'event') and f['code'][0] != 'H' ]
    elif fare_type == 'partner':
        fares = [ f for f in fares_list if f['ticket_type'] in 'partner' ]
    elif fare_type == 'all':
        fares = fares_list
    if sort == "price":
        fares.sort(key=lambda x: x['price'])
    return fares

@fancy_tag(register, takes_context=True)
def render_cart_rows(context, fare_type, form):
    assert fare_type in ('conference', 'goodies', 'partner', 'hotel-room', 'hotel-room-sharing', 'other')
    ctx = Context(context)
    request = ctx['request']
    try:
        company = request.user.assopy_user.account_type == 'c'
    except AttributeError:
        # utente anonimo o senza il profilo assopy (impossibile!)
        company = False

    ctx.update({
        'form': form,
        'company': company,
    })

    fares_list = filter(lambda f: f['valid'], cdataaccess.fares(settings.CONFERENCE_CONFERENCE))
    if fare_type == 'conference':
        tpl = 'p3/fragments/render_cart_conference_ticket_row.html'
        # il rendering dei biglietti "conference" è un po' particolare, ogni
        # riga del carrello corrisponde a più `fare` (student, private,
        # company)

        # Le tariffe devono essere ordinate secondo l'ordine temporale + il
        # tipo di biglietto + il destinatario:
        #   early
        #       full            [Student, Private, Company]
        #       lite (standard) [Student, Private, Company]
        #       daily           [Student, Private, Company]
        #   regular (late)
        #       ...
        #   on desk
        #       ...
        #
        # L'ordine temporale viene implicitamente garantito dall'aver escluso
        # le fare non più valide (non permettiamo overlap nel range di
        # validità)
        fares = dict((f['code'][2:], f) for f in fares_list if f['code'][0] == 'T')
        rows = []
        for t in ('S', 'L', 'D'):
            # Per semplificare il template impacchetto le fare a gruppi di tre:
            # studente, privato, azienda.
            # Ogni riha è una tupla con 3 elementi:
            #       1. Fare
            #       2. FormField
            #       3. Boolean che indica se la tariffa è utilizzabile dall'utente
            row = []
            for k in ('S', 'P', 'C'):
                try:
                    f = fares[t+k]
                except KeyError:
                    row.append((None, None, None))
                else:
                    # la tariffa è valida se passa il controllo temporale e se il tipo
                    # dell'account è compatibile
                    valid = not (company ^ (f['code'][-1] == 'C'))
                    row.append((f, form.__getitem__(f['code']), valid))
            rows.append(row)
        ctx['rows'] = rows
    elif fare_type == 'hotel-room-sharing':
        tpl = 'p3/fragments/render_cart_hotel_ticket_row.html'
        ctx['field'] = form['bed_reservations']
        ctx['field'].field.widget._errors = ctx['field'].errors
    elif fare_type == 'hotel-room':
        tpl = 'p3/fragments/render_cart_hotel_ticket_row.html'
        ctx['field'] = form['room_reservations']
        ctx['field'].field.widget._errors = ctx['field'].errors
    elif fare_type == 'other':
        tpl = 'p3/fragments/render_cart_og_ticket_row.html'
        fares = defaultdict(dict)
        order = ('p', 'c')
        columns = set()
        for f in fares_list:
            if f['ticket_type'] in ('other', 'event') and f['code'][0] != 'H':
                columns.add(f['recipient_type'])
                fares[f['name']][f['recipient_type']] = f
        ctx['fares'] = fares.values()
        ctx['recipient_types'] = sorted(columns, key=lambda v: order.index(v))
    elif fare_type == 'partner':
        tpl = 'p3/fragments/render_cart_partner_ticket_row.html'
        ctx['fares'] = [ f for f in fares_list if f['ticket_type'] in 'partner' ]

    return render_to_string(tpl, ctx)

@register.inclusion_tag('p3/box_image_gallery.html', takes_context=True)
def box_image_gallery(context):
    images = []
    for f in os.listdir(STUFF_DIR):
        images.append('%s%s' % (STUFF_URL, f))

    context.update({
        'images': images,
    })
    return context

@fancy_tag(register, takes_context=True)
def render_partner_program(context, conference=None):
    if conference is None:
        conference = settings.CONFERENCE_CONFERENCE

    from conference import dataaccess
    from conference.templatetags.conference import fare_blob
    fares = [ x for x in dataaccess.fares(conference) if x['ticket_type'] == 'partner' and x['valid'] ]
    fares.sort(key=lambda x: (slugify(x['name']), fare_blob(x, 'date')))
    ctx = Context(context)
    ctx.update({
        'fares': [ (k, list(v)) for k, v in groupby(fares, key=lambda x: slugify(x['name'])) ],
    })
    return render_to_string('p3/fragments/render_partner_program.html', ctx)

@fancy_tag(register, takes_context=True)
def event_partner_program(context, event):
    fare_id = re.search(r'f(\d+)', event.track)
    if fare_id is None:
        return ''
    from conference.templatetags.conference import _request_cache
    c = _request_cache(context['request'], 'fares')
    if not c:
        for f in ConferenceModels.Fare.objects.all():
            c[str(f.id)] = f
    fare = c[fare_id.group(1)]
    return mark_safe('<a href="/partner-program/#%s">%s</a>' % (slugify(fare.name), event.custom,))

@register.filter
def schedule_to_be_splitted(s):
    tracks = ConferenceModels.Track.objects.by_schedule(s)
    s = []
    for t in tracks:
        if t.track.startswith('partner') or t.track.startswith('sprint'):
            s.append(t)
    return len(tracks) != len(s)

@register.filter
def tickets_url(user):
    """
    ritorna la url più diretta per mandare l'utente sulla sua pagina ticket
    """
    if user.assopy_user.token:
        u = reverse('p3-user', kwargs={'token': user.assopy_user.token})
    else:
        u = reverse('p3-tickets')

    return settings.DEFAULT_URL_PREFIX + u

@register.filter
def ticket_user(ticket):
    try:
        p3c = ticket.p3_conference
    except models.TicketConference.DoesNotExist:
        p3c = None
    if p3c and p3c.assigned_to:
        from assopy.models import User
        return User.objects.get(user__email=p3c.assigned_to)
    else:
        return ticket.orderitem.order.user

@register.filter
def com_com_registration(user):
    url = 'https://hotspot.com-com.it/signup/?'
    name = user.name()
    try:
        fn, ln = name.split(' ', 1)
    except ValueError:
        fn = name
        ln = ''
    params = {
        'autofill': 'yes',
        'firstname': fn,
        'lastname': ln,
        'email': user.user.email,
    }
    if user.country:
        params['nationality'] = user.country.pk
    if user.phone and user.phone.startswith('+39'):
        params['ita_mobile'] = user.phone
    params['username'] = name.lower().replace(' ', '').replace('.', '')[:12]
    for k, v in params.items():
        params[k] = v.encode('utf-8')
    return url + urllib.urlencode(params)

@register.inclusion_tag('p3/box_next_events.html', takes_context=True)
def box_next_events(context):
    from conference.templatetags import conference as ctags
    t = datetime.now()
    try:
        sch = ConferenceModels.Schedule.objects.get(date=t.date())
    except ConferenceModels.Schedule.DoesNotExist:
        current = next = {}
    else:
        current = ctags.current_events(context, t)
        next = ctags.next_events(context, t)
    tracks = dict(
        (x, None)
        for x in ConferenceModels.Track.objects.by_schedule(sch)
        if x.outdoor == False
    )
    for track in tracks:
        c = current.get(track)
        if c:
            if hasattr(c, 'evt'):
                c = c.evt.ref
            else:
                c = c.ref
        n = next.get(track)
        if n:
            n_time = n.time
            if hasattr(n, 'evt'):
                n = n.evt.ref
            else:
                n = n.ref
        else:
            n_time = None
        tracks[track] = {
            'current': c,
            'next': (n, n_time),
        }
    events = sorted(tracks.items(), key=lambda x: x[0].order)
    ctx = Context(context)
    ctx.update({
        'events': events,
    })
    return ctx

@fancy_tag(register)
def p3_profile_data(uid):
    return dataaccess.profile_data(uid)

@fancy_tag(register)
def p3_profiles_data(uids):
    return dataaccess.profiles_data(uids)

@fancy_tag(register, takes_context=True)
def get_form(context, name, bound="auto", bound_field=None):
    if '.' in name:
        from conference.utils import dotted_import
        fc = dotted_import(name)
    else:
        fc = getattr(p3forms, name)
    request = context['request']
    if bound:
        if bound == 'auto':
            bound = request.method
        if bound == 'GET':
            data = request.GET
        elif bound == 'POST':
            data = request.POST
        else:
            from django.db.models import Model
            if isinstance(bound, Model):
                data = {}
                for name in fc.base_fields:
                    data[name] = getattr(bound, name)
            else:
                data = bound
        if bound_field and bound_field not in data:
            data = None
    else:
        data = None
    form = fc(data=data)
    if data:
        form.is_valid()
    return form

@fancy_tag(register)
def pending_email_change(user):
    try:
        t = amodels.Token.objects.get(ctype='e', user=user)
    except amodels.Token.DoesNotExist:
        return None
    return t.payload

@fancy_tag(register)
def admin_ticketroom_overall_status():
    status = models.TicketRoom.objects.overall_status()

    labels = dict(models.HOTELROOM_ROOM_TYPE)
    days = sorted(status.keys())
    rooms = {}
    for day in days:
        dst = status[day]
        for room_type, dst in status[day].items():
            try:
                r = rooms[room_type]
            except KeyError:
                r = rooms[room_type] = {
                    'type': room_type,
                    'label': labels.get(room_type, room_type),
                    'days': [],
                }
            r['days'].append(dst)
    return {
        'days': days,
        'rooms': rooms.values(),
    }

@fancy_tag(register)
def warmup_conference_cache(conference=None):
    """
    """
    if conference is None:
        conference = settings.CONFERENCE_CONFERENCE
    qs = ConferenceModels.TalkSpeaker.objects\
        .filter(talk__conference=conference)\
        .values_list('talk', 'speaker')

    talks = set()
    speakers = set()
    for row in qs:
        talks.add(row[0])
        speakers.add(row[1])

    return {
        'speakers': dict([ (x['id'], x) for x in dataaccess.profiles_data(speakers) ]),
        'talks': dict([ (x['id'], x) for x in cdataaccess.talks_data(talks) ]),
    }

@register.filter
def frozen_reason(ticket):
    if not ticket.frozen:
        return ''
    if amodels.RefundOrderItem.objects.filter(orderitem=ticket.orderitem).exists():
        return 'refund pending'
    else:
        return ''

@fancy_tag(register, takes_context=True)
def all_user_tickets(context, uid=None, conference=None, status="complete", fare_type="conference"):
    if uid is None:
        uid = context['request'].user.id
    if conference is None:
        conference = settings.CONFERENCE_CONFERENCE
    tickets = dataaccess.all_user_tickets(uid, conference)
    if status == 'complete':
        tickets = filter(lambda x: x[3], tickets)
    elif status == 'incomplete':
        tickets = filter(lambda x: not x[3], tickets)
    if fare_type != "all":
        tickets = filter(lambda x: x[1] == fare_type, tickets)
    return tickets

@fancy_tag(register)
def p3_tags():
    return dataaccess.tags()

@fancy_tag(register, takes_context=True)
def render_profile_box(context, profile, conference=None, user_message="auto"):
    if conference is None:
        conference = settings.CONFERENCE_CONFERENCE
    if isinstance(profile, int):
        profile = dataaccess.profile_data(profile)
    ctx = Context(context)
    ctx.update({
        'profile': profile,
        'conference': conference,
        'user_message': user_message if user_message in ('auto', 'always', 'none') else 'auto',
    })
    return render_to_string('p3/fragments/render_profile_box.html', ctx)

@register.inclusion_tag('p3/fragments/archive.html', takes_context=True)
def render_archive(context, conference):
    ctx = Context(context)

    def match(e, exclude_tags=set(('partner0', 'partner1', 'sprint1', 'sprint2', 'sprint3'))):
        if e['tags'] & exclude_tags:
            return False
        if not e['talk']:
            return False
        return True
    #events = { x['id']:x for x in filter(match, cdataaccess.events(conf=conference)) }
    events = { }
    talks = {}
    for e in events.values():
        t = e['talk']
        if t['id'] in talks:
            continue
        t['dates'] = sorted([ (events[x]['time'], events[x]['talk']['video_url']) for x in t['events_id'] ])
        talks[t['id']] = t

    ctx.update({
        'conference': conference,
        'talks': sorted(talks.values(), key=lambda x: x['title']),
    })
    return ctx

@register.filter
def timetable_remove_first(timetable, tag):
    if not tag:
        return timetable
    start = None
    for time, events in timetable.iterOnTimes():
        stop = False
        for e in events:
            if tag not in e['tags']:
                stop = True
                break
        start = time.time()
        if stop:
            break

    return timetable.slice(start=start)
