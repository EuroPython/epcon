# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import mimetypes
import os
import os.path
import re
import random
import sys
import urllib
import urllib2
from collections import defaultdict
from datetime import datetime
from itertools import groupby

from django import template
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.template import Context
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe

from conference import models as ConferenceModels
from conference.settings import STUFF_DIR, STUFF_URL
from p3 import models

import twitter
from fancy_tag import fancy_tag

mimetypes.init()

register = template.Library()

@register.inclusion_tag('p3/box_pycon_italia.html')
def box_pycon_italia():
    return {}

@register.inclusion_tag('p3/box_newsletter.html')
def box_newsletter():
    return {}

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

@register.inclusion_tag('p3/render_ticket.html', takes_context=True)
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
    else:
        form = forms.FormTicketPartner(instance=ticket, prefix='t%d' % (ticket.id,))
        blocked = False
    context.update({
        'ticket': ticket,
        'form': form,
        'user': user,
        'blocked': blocked,
    })
    return context

@register.inclusion_tag('p3/render_cart_row.html', takes_context=True)
def render_cart_row(context, subcode, form, fares):
    def g(code):
        try:
            return form[code]
        except KeyError:
            return None
    try:
        at = context['request'].user.assopy_user.account_type
    except AttributeError:
        at = None
    company = at == 'c'

    # Selezione le tariffe che devo mostrare: per ogni subcode passato ci sono
    # al più tre tariffe, ad esempio con TES (ticket early standard):
    # TESS -> student 
    # TESP -> private 
    # TESC -> company 
    subfares = [ fares.get(subcode + x) for x in ('S', 'P', 'C') ]

    # row a tre elementi: studente, privato, azienda
    #   ognuno di questi è una tupla con 3 elementi:
    #       1. Fare
    #       2. FormField
    #       3. Boolean che indica se la tariffa è utilizzabile dall'utente
    row = []
    for f in subfares:
        if f is None:
            row.append((None, None, None))
        else:
            # la tariffa è valida se passa il controllo temporale e se il tipo
            # dell'account è compatibile
            row.append((f, g(f.code), f.valid() and at and not (company ^ (f.code[-1] == 'C')),))
    return {
        'row': row,
    }

@register.inclusion_tag('p3/render_pp_cart_row.html', takes_context=True)
def render_pp_cart_row(context, fare):
    return {
        'f': fare,
    }

@register.inclusion_tag('p3/render_og_cart_row.html', takes_context=True)
def render_og_cart_row(context, fare):
    return {
        'f': fare,
    }

@register.inclusion_tag('p3/box_image_gallery.html', takes_context=True)
def box_image_gallery(context):
    request = context['request']
    images = []
    for f in os.listdir(STUFF_DIR):
        images.append('%s%s' % (STUFF_URL, f))
   
    context.update({
        'images': images,
    })
    return context

@register.filter
def eval_(x, code):
    try:
        return eval(code, {'x': x})
    except:
        return None

@register.filter
def attrib_(ob, attrib):
    try:
        iter(ob)
    except TypeError:
        return getattr(ob, attrib, None)
    else:
        return [ getattr(x, attrib, None) for x in ob ]

@register.filter
def contains_(it, key):
    return key in it

@register.inclusion_tag('p3/render_partner_program.html', takes_context=True)
def render_partner_program(context):
    from conference.templatetags.conference import fare_blob
    fares = list(ConferenceModels.Fare.objects.filter(ticket_type='partner'))

    def key(f):
        date = datetime.strptime(fare_blob(f, 'data').split(',')[0][:-2] + ' 2011', '%B %d %Y').date()
        return (slugify(f.name), date)
    fares.sort(key=key)
    return {
        'fares': [ (k, list(v)) for k, v in groupby(fares, key=lambda x: slugify(x.name)) ],
    }

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
    if user.token:
        u = reverse('p3-user', kwargs={'token': user.token})
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

