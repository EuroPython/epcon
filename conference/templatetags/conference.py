# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import mimetypes
import os
import os.path
import re
import httplib2
import random
import sys
import simplejson
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from django import template
from django.conf import settings as dsettings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.template import defaultfilters, Context
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe

from conference import dataaccess
from conference import models
from conference import utils
from conference import settings
from conference.settings import MIMETYPE_NAME_CONVERSION_DICT as mimetype_conversion_dict
from conference.signals import timetable_prepare
from conference.utils import TimeTable

from pages.settings import PAGE_DEFAULT_LANGUAGE

from tagging.models import Tag, TaggedItem
from tagging.utils import parse_tag_input

from fancy_tag import fancy_tag

mimetypes.init()

register = template.Library()

def _lang(ctx):
    try:
        return ctx['LANGUAGE_CODE']
    except KeyError:
        return PAGE_DEFAULT_LANGUAGE

def _request_cache(request, key):
    """
    ritorna (o crea) un dizionario collegato all'oggetto passato utilizzabile
    come cache con visibilità pari a quella della request.
    """
    try:
        return request._conf_cache[key]
    except KeyError:
        request._conf_cache[key] = {}
    except AttributeError:
        request._conf_cache = {key: {}}
    return request._conf_cache[key]

@fancy_tag(register, takes_context=True)
def get_deadlines(context, year=None, limit=None, not_expired=True):
    if year is None:
        year = date.today().year
    data = dataaccess.deadlines(_lang(context), year)
    output = []
    for d in data:
        if not_expired and d['expired']:
            continue
        output.append(d)
    if limit is not None:
        output = output[:limit]
    return output

@fancy_tag(register, takes_context=True)
def navigation(context, page_type):
    return dataaccess.navigation(_lang(context), page_type)

@register.tag
def stuff_info(parser, token):
    """
    {% stuff_info "file_path"|variable [as var] %}
    ritorna il mimetype e la dimensione del file specificato (il file deve
    risidere all'interno della dir "stuff")
    """
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        fpath = contents[1]
    except IndexError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    if len(contents) > 2:
        if len(contents) != 4 or contents[-2] != 'as':
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
        var_name = contents[-1]
    else:
        var_name = None

    class StuffInfoNode(template.Node):
        def __init__(self, fpath, var_name):
            if fpath.startswith('"') and fpath.endswith('"'):
                self.fpath = fpath[1:-1]
            else:
                self.fpath = template.Variable(fpath)
            self.var_name = var_name
        def render(self, context):
            try:
                fpath = self.fpath.resolve(context)
            except AttributeError:
                fpath = self.fpath
            try:
                fpath = fpath.path
            except AttributeError:
                fpath = os.path.join(settings.STUFF_DIR, 'conference', fpath)
            try:
                stat = os.stat(fpath)
            except (AttributeError, OSError), e:
                fsize = ftype = None
            else:
                fsize = stat.st_size
                ftype = mimetypes.guess_type(fpath)[0]
            ftype = mimetype_conversion_dict.get(ftype, ftype)
            if self.var_name:
                context[self.var_name] = (ftype, fsize)
                return ''
            else:
                return "(%s %s)" % (ftype, fsize)

    return StuffInfoNode(fpath, var_name)

@register.tag
def conference_speakers(parser, token):
    """
    {% conference_speakers [ conference ] [ limit num ] [ "random" ] as var %}
    inserisce in var l'elenco degli speaker (opzionalmente è possibile
    filtrare per conferenza).
    """
    contents = token.split_contents()
    tag_name = contents.pop(0)
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    contents = contents[:-2]

    conference = None
    limit = None
    random = False
    while contents:
        item = contents.pop(0)
        if item == 'limit':
            limit = int(contents.pop(0))
        elif item == '"random"':
            random = True
        elif conference is None:
            conference = item
        else:
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    class SpeakersNode(TNode):
        def __init__(self, conference, limit, random, var_name):
            self.var_name = var_name
            if conference:
                self.conference = self._set_var(conference)
            else:
                self.conference = None
            self.limit = limit
            self.random = random
        def render(self, context):
            speakers = models.Speaker.objects.all()
            conference = self._get_var(self.conference, context)
            if self.conference:
                speakers = speakers.filter(talk__conference=conference)
            if self.random:
                speakers = speakers.order_by('?')
            if self.limit:
                speakers = speakers[:self.limit]
            context[self.var_name] = list(speakers)
            return ''
    return SpeakersNode(conference, limit, random, var_name)

class TNode(template.Node):
    def _set_var(self, v):
        if not v:
            return v
        if v.startswith('"') and v.endswith('"'):
            return v[1:-1]
        else:
            return template.Variable(v)

    def _get_var(self, v, context):
        try:
            return v.resolve(context)
        except AttributeError:
            return v

@register.tag
def conference_talks(parser, token):
    """
    {% conference_talks [ speaker ] [ conference ] [ "random" ] [ tags ] as var %}
    inserisce in var l'elenco dei talk (opzionalmente è possibile
    filtrare per speaker e conferenza).
    """
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    contents = contents[1:-2]

    speaker = conference = tags = None
    random = False

    if contents:
        speaker = contents.pop(0)
    if contents:
        conference = contents.pop(0)
    if contents and 'random' in contents[0]:
        contents.pop(0)
        random = True
    if contents:
        tags = contents.pop(0)

    class TalksNode(TNode):
        def __init__(self, speaker, conference, tags, random, var_name):
            self.var_name = var_name
            self.speaker = self._set_var(speaker)
            self.conference = self._set_var(conference)
            self.tags = self._set_var(tags)
            self.random = random

        def render(self, context):
            talks = models.Talk.objects.all()
            speaker = self._get_var(self.speaker, context)
            tags = self._get_var(self.tags, context)
            conference = self._get_var(self.conference, context)
            if speaker:
                talks = talks.filter(speakers = speaker)
            if conference:
                if not isinstance(conference, (list, tuple)):
                    conference = [ conference ]
                talks = talks.filter(conference__in = conference)
            if tags:
                talks = TaggedItem.objects.get_by_model(talks, tags)
            if self.random:
                talks = list(talks.order_by('?'))
            context[self.var_name] = talks
            return ''

    return TalksNode(speaker, conference, tags, random, var_name)

@register.inclusion_tag('conference/render_talk_report.html', takes_context=True)
def render_talk_report(context, speaker, conference, tags):
    context.update({
        'speaker': speaker,
        'conference': conference,
        'tags': tags,
    })
    return context

def schedule_context(schedule):
    from datetime import time

    TIME_STEP = 15
    dbtracks = dict((t.track, (ix, t)) for ix, t in enumerate(schedule.track_set.all()))
    _itracks = dict(dbtracks.values())
    dbevents = defaultdict(list)
    for e in schedule.event_set.select_related('talk', 'sponsor__sponsorincome_set'):
        dbevents[e.start_time].append(e)

    eevent = lambda t: { 'time': t, 'title': '', 'track_slots': 1, 'time_slots': 1, 'talk': None, 'tags': [], 'sponsor': None }

    # riorganizzo in timetable la struttra degli evento dello schedule passato
    # per renderli semplici da maneggiare al template. Ogni entry di timetable
    # rappresenta una riga della tabella HTML
    timetable = defaultdict(lambda: { 'class': [], 'events': [ None ] * len(dbtracks)} )
    prow = [ None ] * len(dbtracks)
    for rtime, events in sorted(dbevents.items()):
        row = timetable[rtime]['events']
        end = False
        for e in events:
            event = eevent(e.start_time)
            if e.talk:
                event['title'] = e.talk.title
                event['time_slots'] = e.talk.duration / TIME_STEP
                event['talk'] = e.talk
                if e.sponsor:
                    event['sponsor'] = e.sponsor
            else:
                event['title'] = e.custom
            # row ha tanti elementi quante sono le track dello schedule
            # devo inserire event nel punto giusto
            tags = set( t.name for t in Tag.objects.get_for_object(e) )
            if 'end' in tags:
                end = True
                tags.remove('end')

            # tracks è una lista, ordinata, con gli indici numerici (riferiti a
            # dbtracks) delle track interessate dall'evento.
            tracks = sorted([ dbtracks.get(t, [None])[0] for t in tags ])
            if None in tracks:
                # l'evento fa riferimento a delle track speciali (come il
                # coffee break o la registrazione), per adesso tratto tutte gli
                # eventi speciali nello stesso modo (lo spalmo tutte le track
                # disponibili) un estensione utile potrebbe essere quella di
                # dare significati diversi alle varie track speciali e cambiare
                # il comportamento di conseguenza.
                event['track_slots'] = len(dbtracks)
                event['tags'] = [ t for t in tags if t not in dbtracks ]
                row[0] = event
            else:
                # per il momento non supporto il caso di un evento associato a
                # track non adiacenti.
                event['track_slots'] = len(tracks)
                ex = tracks[0]
                event['tags'] = [ _itracks[ex].track ]
                row[ex] = event

        # ho inserito una nuova riga nella timetable, ho abbastanza
        # informazioni per controllare la riga precedente (prow) e allungare i
        # tempi degli eventi che non hanno un indicazione della durata
        minutes = lambda t: t.hour * 60 + t.minute
        def m2time(m):
            nh = m / 60
            nm = m - nh * 60
            return time(hour = nh, minute = nm)
        for ix, t in enumerate(zip(prow, row)):
            p, c = t
            if not p:
                continue
            diff = minutes(rtime) - minutes(p['time'])
            slots = diff / TIME_STEP
            if not p['talk']:
                p['time_slots'] = slots
            elif p['time_slots'] < slots:
                # se time_slots è minore del previsto "paddo" con un evento vuoto
                premature_end = minutes(p['time']) + p['talk'].duration
                new_start = m2time(premature_end)
                empty = timetable[new_start]['events']
                empty[ix] = prow[ix] = eevent(new_start)
            elif c:
                # qui devo gestire il caso in cui gli event nella riga superiore abbiano
                # allocati più slot temporali di quelli individuati
                for x in range(c['track_slots']):
                    pc = prow[ix+x]
                    if pc and pc['time_slots'] > slots:
                        overlap_needed = ix + x
                        break
                else:
                    overlap_needed = None
                if overlap_needed is not None:
                    # se time_slots è maggiore ho due possibilità:
                    # 1. se l'evento corrente è marcato come "overlap" lo inserisco
                    # in mezzo a p, spostando parte di p dopo c
                    # 2. se c non è "overlap" lascio le cose come stanno, l'html
                    # che ne risulterà sarà senza dubbio incasinato e l'operatore
                    # gestirà a mano la situazione
                    overlap = None
                    for t in c['tags']:
                        if t.startswith('overlap'):
                            try:
                                overlap = int(t.split('-', 1)[1])
                            except IndexError:
                                overlap = 15
                            except ValueError:
                                pass
                            else:
                                c['tags'].remove(t)
                            break
                    if overlap:
                        pix = overlap_needed
                        pc = prow[pix]
                        dslots = pc['time_slots'] - slots
                        pc['time_slots'] = slots
                        # devo calcolare il tempo di inizio della seconda parte del talk,
                        # che equivale a: inizio_overlap + tempo_overlap
                        c_end = minutes(c['time']) + overlap
                        new_start = m2time(c_end)
                        empty = timetable[new_start]['events']
                        n = dict(pc)
                        n['time'] = new_start
                        n['time_slots'] = dslots
                        n['title'] = '<strong>%s</strong><br/>(seconda parte)' % (escape(pc['title']),)
                        n['talk'] = None
                        empty[pix] = n
                        row = list(row)
                        row[pix] = empty[pix]

            # c può essere None perché suo fratello copre più track oppure
            # perché c'è un buco nello schedule.
            if not c and ix and row[ix-1] and row[ix-1]['track_slots'] == 1:
                # *potrebbe* essere un buco nello schedule, per esserne certo
                # devo verificare che il corrispondente evento in prow non
                # abbia un time_slots maggiore di slots
                brother = row[ix-1]
                if not p or p['time_slots'] <= slots:
                    row[ix] = eevent(rtime)
                    row[ix]['time_slots'] = brother['time_slots']
        if end:
            timetable[rtime]['class'].append('end')
            prow = [ None ] * len(dbtracks)
        else:
            prow = list(row)
    if timetable:
        timetable[rtime]['class'].append('end')

    # trasformo il dizionario in una lista ordinata, più semplice da gestire
    # per il template e la riempio di "filler" per proporzionare le varie fasce
    # di eventi (altro lavoro in meno per il template).
    timetable = sorted(timetable.items())
    offset = 0
    for ix, v in list(enumerate(timetable[:-1])):
        t, row = v
        if 'end' in row['class']:
            # padding arbitrario
            steps = 4
        else:
            next = timetable[ix+1+offset][0]
            if next:
                delta = next.hour * 60 + next.minute - (t.hour * 60 + t.minute)
                steps = delta / TIME_STEP
            else:
                steps = 1
        for x in range(steps - 1):
            timetable.insert(ix+1+offset, (None, None))
        offset += steps - 1

    return timetable

@register.inclusion_tag('conference/render_schedule.html', takes_context = True)
def render_schedule(context, schedule):
    """
    {% render_schedule schedule %}
    """
    if isinstance(schedule, int):
        sid = schedule
    elif isinstance(schedule, basestring):
        try:
            c, s = schedule.split('/')
        except ValueError:
            raise template.TemplateSyntaxError('%s is not in the form of conference/slug' % schedule)
        sid = models.Schedule.objects.values('id').get(conference=c, slug=s)['id']

    return {
        'sid': sid,
        'timetable': utils.TimeTable2.fromSchedule(sid),
    }

@fancy_tag(register, takes_context=True)
def timetable_slice(context, timetable, start=None, end=None):
    if start:
        start = datetime.strptime(start, '%H:%M').time()

    if end:
        end = datetime.strptime(end, '%H:%M').time()

    return timetable.slice(start=start, end=end)

@fancy_tag(register, takes_context=True)
def schedule_timetable(context, schedule, start=None, end=None):
    if start:
        start = datetime.strptime(start, '%H:%M').time()
    else:
        start = None

    if end:
        end = datetime.strptime(end, '%H:%M').time()
    else:
        end = None

    tracks = models.Track.objects.by_schedule(schedule)
    request = context.get('request')
    if request:
        for ix, t in list(enumerate(tracks))[::-1]:
            if request.GET.get('show-%s' % t.track) == '0':
                del tracks[ix]

    if not tracks:
        return None
    timetable_prepare.send(schedule, tracks=tracks)

    events = list(models.Event.objects.filter(schedule=schedule).select_related('talk'))
    timetable_prepare.send(schedule, events=events, tracks=tracks)

    ts = [time(8,00), time(18,30)]
    if events:
        events.sort(key=lambda x: x.start_time)
        if events[0].start_time < ts[0]:
            ts[0] = events[0].start_time
        if events[-1].start_time >= ts[1]:
            if events[-1].talk:
                td = timedelta(seconds=60*events[-1].talk.duration)
            else:
                td = timedelta(seconds=3600)
            ts[1] = TimeTable.sumTime(events[-1].start_time, td)

    tt = TimeTable(time_spans=ts, rows=tracks)
    for e in events:
        if e.duration:
            duration = e.duration
        else:
            duration = e.talk.duration if e.talk else None
        event_tracks = set(parse_tag_input(e.track))
        rows = [ x for x in tracks if x.track in event_tracks ]
        if ('break' in event_tracks or 'special' in event_tracks) and not rows:
            rows = list(t for t in tracks if not t.outdoor)
        if not rows:
            continue
        if 'teaser' in event_tracks:
            duration = 30
        tt.setEvent(e.start_time, e, duration, rows=rows)

    timetable_prepare.send(schedule, timetable=tt)

    if start or end:
        tt = tt.slice(start, end)

    return tt

@fancy_tag(register, takes_context=True)
def render_schedule_timetable(context, schedule, timetable, start=None, end=None, collapse='auto'):
    if start:
        start = datetime.strptime(start, '%H:%M').time()
    else:
        start = None
    if end:
        end = datetime.strptime(end, '%H:%M').time()
    else:
        end = None
    if start or end:
        timetable = timetable.slice(start, end)
    ctx = Context(context)
    ctx.update({
        'schedule': schedule,
        'timetable': timetable,
        'collapse': collapse,
    })
    return render_to_string('conference/render_schedule_timetable.html', ctx)

@fancy_tag(register, takes_context=True)
def render_schedule_timetable_as_list(context, schedule, timetable, start=None, end=None):
    if start:
        start = datetime.strptime(start, '%H:%M').time()
    else:
        start = None
    if end:
        end = datetime.strptime(end, '%H:%M').time()
    else:
        end = None
    if start or end:
        timetable = timetable.slice(start, end)
    ctx = Context(context)
    ctx.update({
        'schedule': schedule,
        'timetable': timetable,
    })
    return render_to_string('conference/render_schedule_timetable_as_list.html', ctx)

@fancy_tag(register, takes_context=True)
def overbooked_events(context, conference):
    """
    restituisce l'elenco degli eventi per i quali è prevista un affluenza
    maggiore della capienza della track.  la previsione viene fatta utilizzando
    gli EventInterest.
    """
    c = _request_cache(context['request'], 'schedules_overbook')
    if not c:
        data = models.Schedule.objects.expected_attendance(conference)
        for k, v in data.items():
            if not v['overbook']:
                del data[k]
        c['items'] = data
    return c['items']

@fancy_tag(register, takes_context=True)
def get_event_track(context, event):
    """
    ritorna la prima istanza di track tra quelle specificate dall'evento o None
    se è di tipo speciale
    """
    dbtracks = dict((t.track, t) for t in models.Track.objects.by_schedule(event.schedule))
    for t in set(parse_tag_input(event.track)):
        if t in dbtracks:
            return dbtracks[t]

@register.filter
def event_has_track(event, track):
    return track in set(parse_tag_input(event.track))

@fancy_tag(register)
def event_row_span(timetable, event):
    ix = timetable.rows.index(event.row)
    return timetable.rows[ix:ix+event.rows]

@fancy_tag(register)
def event_time_span(timetable, event, time_slot=15):
    start = datetime.combine(date.today(), event.time)
    end = start + timedelta(minutes=time_slot * event.columns)
    return start.time(), end.time()

@register.tag
def conference_schedule(parser, token):
    """
    {% conference_schedule conference schedule as var %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        conference = contents[1]
        schedule = contents[2]
        var_name = contents[4]
    except IndexError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    class ScheduleNode(TNode):
        def __init__(self, conference, schedule, var_name):
            self.var_name = var_name
            self.conference = self._set_var(conference)
            self.schedule = self._set_var(schedule)

        def render(self, context):
            schedule = models.Schedule.objects.get(
                conference = self._get_var(self.conference, context),
                slug = self._get_var(self.schedule, context),
            )
            context[self.var_name] = schedule_context(schedule)
            return ''

    return ScheduleNode(conference, schedule, var_name)

@register.inclusion_tag('conference/render_talk_report.html', takes_context=True)
def render_talk_report(context, speaker, conference, tags):
    context.update({
        'speaker': speaker,
        'conference': conference,
        'tags': tags,
    })
    return context

@register.filter
def add_number(value, arg):
    return value + float(arg)

@register.filter
def split(value, arg):
    return value.split(arg)

@register.filter
def splitonspace(value):
    return value.split(' ')

@register.filter
def image_resized(value, size='resized'):
    if isinstance(value, basestring):
        url = value
        if not url.startswith(dsettings.DEFAULT_URL_PREFIX + dsettings.MEDIA_URL):
            return url
    else:
        url = value.url
    try:
        dirname, basename = os.path.split(url)
    except:
        return ''
    else:
        return dirname + '/%s/%s' % (size, os.path.splitext(basename)[0] + '.jpg')

@register.filter
def intersected(value, arg):
    if not isinstance(arg, (list, tuple)):
        arg = [ arg ]
    return set(value) & set(arg)

@register.filter
def splitbysize(value, arg):
    from itertools import izip
    def grouper(n, iterable, fillvalue=None):
        "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return list(izip(*args))
    arg = int(arg)
    value = list(value)
    if len(value) % arg:
        value += [ None ] * (arg - (len(value) % arg))
    return grouper(arg, value)

@fancy_tag(register)
def conference_sponsor(conference=None, only_tags=None, exclude_tags=None):
    if conference is None:
        conference = settings.CONFERENCE
    data = dataaccess.sponsor(conference)
    if only_tags:
        t = set(only_tags)
        data = filter(lambda x: x['tags'] & t, data)
    if exclude_tags:
        t = set(exclude_tags)
        data = filter(lambda x: not (x['tags'] & t), data)
    return data

@register.tag
def conference_mediapartner(parser, token):
    """
    {% conference_mediapartner [ conference ] as var %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    contents = contents[1:-2]

    conference = None
    if contents:
        conference = contents.pop(0)

    class MediaPartnerNode(TNode):
        def __init__(self, conference, var_name):
            self.var_name = var_name
            self.conference = self._set_var(conference)

        def render(self, context):
            partner = models.MediaPartner.objects.all()
            conference = self._get_var(self.conference, context)
            if conference:
                partner = partner.filter(mediapartnerconference__conference = conference)
            partner = partner.order_by('partner')
            context[self.var_name] = partner
            return ''
    return MediaPartnerNode(conference, var_name)

@register.tag
def render_page_template(parser, token):
    contents = token.split_contents()
    try:
        tag_name, arg = contents[0:2]
    except ValueError:
        raise template.TemplateSyntaxError("%r tag needs at least two arguments" % contents[0])
    if len(contents) > 2:
        if contents[-2] != 'as':
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % contents[0])
        var_name = contents[-1]
    else:
        var_name = None

    class TemplateRenderer(template.Node):
        def __init__(self, arg, var_name):
            self.arg = template.Variable(arg)
            self.var_name = var_name

        def render(self, context):
            try:
                tpl = self.arg.resolve(context)
                t = template.Template(tpl)
                data = t.render(context)
                if self.var_name:
                    context[self.var_name] = data
                    return ''
                else:
                    return data
            except template.VariableDoesNotExist:
                return ''

    return TemplateRenderer(arg, var_name)

@register.tag
def conference_multilingual_attribute(parser, token):
    """
    {% conference_multilingual_attribute object attribute [as var] [fallback lang|any] %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        instance, attribute = contents[1:3]
    except ValueError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    contents = contents[3:]
    if contents and contents[0] == 'as':
        var_name = contents[1]
        contents = contents[2:]
    else:
        var_name = None

    if contents and contents[0] == 'fallback':
        fallback = contents[1]
        contents = contents[2:]
    else:
        fallback = None

    if contents:
        raise template.TemplateSyntaxError("%r had too many arguments" % tag_name)

    class AttributeNode(TNode):
        def __init__(self, instance, attribute, var_name, fallback):
            self.var_name = var_name
            self.instance = self._set_var(instance)
            self.attribute = self._set_var(attribute)
            self.fallback = self._set_var(fallback)

        def render(self, context):
            instance = self._get_var(self.instance, context)
            attribute = self._get_var(self.attribute, context)
            fallback = self._get_var(self.fallback, context)
            try:
                query = getattr(instance, attribute)
            except AttributeError:
                return ''

            contents = dict((c.language, c) for c in query.all() if (c.body and c.content == attribute))
            try:
                value = contents[context['LANGUAGE_CODE']]
            except KeyError:
                if fallback is None or not contents:
                    value = None
                elif fallback != 'any':
                    value = contents.get(fallback)
                else:
                    dlang = dsettings.LANGUAGES[0][0]
                    if dlang in contents:
                        value = contents[dlang]
                    else:
                        value = contents.values()[0]
            if self.var_name:
                context[self.var_name] = value
                return ''
            else:
                return value.body if value else ''

    return AttributeNode(instance, attribute, var_name, fallback)

@register.tag
def conference_hotels(parser, token):
    """
    {% conference_hotels as var %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        if contents[1] != 'as':
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
        var_name = contents[2]
    except IndexError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    class HotelsNode(TNode):
        def __init__(self, var_name):
            self.var_name = var_name

        def render(self, context):
            query = models.Hotel.objects.filter(visible = True).order_by('-modified', 'name')
            if self.var_name:
                context[self.var_name] = query
                return ''
            else:
                return value
    return HotelsNode(var_name)

@register.inclusion_tag('conference/render_hotels.html')
def render_hotels(hotels):
    """
    {% render_hotels hotels %}
    """
    return {
        'hotels': hotels,
    }

@fancy_tag(register, takes_context=True)
def embed_video(context, value, args=""):
    """
    {{ talk|embed_video:"source=[youtube, viddler, download, url.to.oembed.endpoint],width=XXX,height=XXX" }}
    """
    args = dict( map(lambda _: _.strip(), x.split('=')) for x in args.split(',') if '=' in x )
    providers = {
        'viddler': ('oEmbed', 'http://lab.viddler.com/services/oembed/'),
        'youtube': ('oEmbed', 'https://www.youtube.com/oembed'),
        'download': ('download', None),
    }
    source = None
    video_url = None
    video_path = None
    if isinstance(value, models.Talk):
        if not settings.TALK_VIDEO_ACCESS(context['request'], value):
            return ''
        if not value.video_type or value.video_type == 'download':
            video_url = reverse('conference-talk-video-mp4', kwargs={'slug': value.slug })
            if value.video_file:
                video_path = os.path.join(dsettings.MEDIA_ROOT, 'conference/videos', video_url.name)
            elif settings.VIDEO_DOWNLOAD_FALLBACK:
                for ext in ('.avi', '.mp4'):
                    fpath = os.path.join(dsettings.MEDIA_ROOT, 'conference/videos', value.slug + ext)
                    if os.path.exists(fpath):
                        video_path = fpath
                        break
            source = 'download'
        else:
            video_url = value.video_url
#        if not value.video_type or value.video_type == 'download':
#            if value.video_file:
#                video_url = dsettings.MEDIA_URL + 'conference/videos/' + video_url.name
#                video_path = os.path.join(dsettings.MEDIA_ROOT, 'conference/videos', video_url.name)
#            elif settings.VIDEO_DOWNLOAD_FALLBACK:
#                for ext in ('.avi', '.mp4'):
#                    fpath = os.path.join(dsettings.MEDIA_ROOT, 'conference/videos', value.slug + ext)
#                    if os.path.exists(fpath):
#                        video_url = dsettings.MEDIA_URL + 'conference/videos/' + value.slug + ext
#                        video_path = fpath
#                        break
#            source = 'download'
#        else:
#            video_url = value.video_url
    else:
        video_url = value
    if not video_url:
        return ''

    if source is None:
        try:
            source = args['source']
        except KeyError:
            if 'viddler' in video_url:
                source = 'viddler'
            elif 'youtube' in video_url:
                source = 'youtube'
            else:
                source = 'download'
    try:
        vtype = providers[source]
    except KeyError:
        if source.startswith('http'):
            vtype = ('oEmbed', source)
        else:
            raise

    w = h = None
    if 'width' in args:
        w = int(args['width'])
    if 'height' in args:
        h = int(args['height'])

    if vtype[0] == 'oEmbed':
        http = httplib2.Http()
        url = vtype[1] + '?url=' + video_url + '&format=json'
        if w and h:
            url += '&width=%s&height=%s&maxwidth=%s&maxheight=%s' % (w, h, w, h)
        # rasky: youtube supports this but there's no standard way for querying the SSL
        # embed. We can assume that others will ignore the extra query argument.
        url += '&scheme=https'
        try:
            response, content = http.request(url)
            data = simplejson.loads(content)
        except:
            # Qualsiasi cosa succeda, che non riesca a connettermi a vtype[1] o che
            # non possa decodificare content preferisco non mostrare il video
            # che causare un error 500.
            # Per la cronaca .loads solleva TypeError se content non è né un
            # stringa né un buffer e ValueError se content non è un json
            # valido.
            return ""

        html = data['html']
        # Se voglio forzare la larghezza e l'altezza a w e h posso usare queste
        # regexp; viddler ad esempio utilizza i valori richiesti via url come
        # hint (ne onora uno ma l'altro viene modificato per non deformare il
        # video).
        #if w and h:
        #    html = re.sub('width=\W*"\d+"', 'width="%s"' % w, html)
        #    html = re.sub('height=\W*"\d+"', 'height="%s"' % h, html)
    else:
        try:
            stat = os.stat(video_path)
        except (TypeError, AttributeError, OSError), e:
            finfo = ''
        else:
            fsize = stat.st_size
            ftype = mimetypes.guess_type(video_path)[0]
            finfo = ' (%s %s)' % (ftype, defaultfilters.filesizeformat(fsize))

        opts = {
            'controls': 'controls',
            'class': 'projekktor',
        }
        if w and h:
            opts['width'] = w
            opts['height'] = h

        data = {
            'attrs': ' '.join('%s="%s"' % x for x in opts.items()),
            'href': video_url,
            'info': finfo,
        }

        data['attrs'] += ' src="%s"' % data['href']
        html = """
            <div>
                <video %(attrs)s>
                    <_source src="%(href)s" />
                </video>
                <a href="%(href)s">download video%(info)s</a>
            </div>
            """ % data
        html = """
            <div>
                <a href="%(href)s">download video%(info)s via BitTorrent</a>
            </div>
        """ % data
    return mark_safe(html)

@register.tag
def conference_quotes(parser, token):
    """
    {% conference_quotes [ limit num ] as var %}
    """
    contents = token.split_contents()
    tag_name = contents.pop(0)
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    contents = contents[:-2]

    if contents:
        contents.pop(0)
        limit = int(contents.pop(0))

    class QuotesNode(TNode):
        def __init__(self, limit, var_name):
            self.var_name = var_name
            self.limit = limit
        def render(self, context):
            quotes = models.Quote.objects.order_by('?')
            if self.limit:
                quotes = quotes[:self.limit]
            context[self.var_name] = list(quotes)
            return ''
    return QuotesNode(limit, var_name)

@fancy_tag(register, takes_context=True)
def talk_vote(context, talk, user=None):
    """
    {% talk_vote talk [ user ] as var %}
    Restituisce il voto che l'utente, se manca viene recuperato dalla request,
    ha dato al talk.
    """
    request = context.get('request')
    if user is None:
        if not request:
            raise ValueError('request not found')
        else:
            user = request.user

    try:
        cached = request._user__talks_votes
    except AttributeError:
        cached = dict((x.talk_id, x) for x in models.VotoTalk.objects.filter(user=user))
        request._user__talks_votes = cached

    return cached.get(talk.id)

@register.filter
def full_url(url):
    if not url.startswith(dsettings.DEFAULT_URL_PREFIX):
        url = dsettings.DEFAULT_URL_PREFIX + url
    return url

@register.filter
def fare_blob(fare, field):
    match = re.search(r'%s\s*=\s*(.*)$' % field, fare.blob, re.M)
    if match:
        return match.group(1).strip()
    return ''

@fancy_tag(register)
def voting_data(conference):
    qs = models.VotoTalk.objects\
        .filter(talk__conference=conference)\
        .values('user')
    votes = qs.count()
    users = qs.distinct().count()
    groups = defaultdict(lambda: defaultdict(list))
    results = utils.voting_results()
    if results is not None:
        for tid, type, language in results:
            groups[type][language].append(tid)

    for k, v in groups.items():
        groups[k] = dict(v)

    return {
        'votes': votes,
        'users': users,
        'groups': dict(groups),
    }

@fancy_tag(register)
def latest_tweets(screen_name, count=1):
    if settings.LATEST_TWEETS_FILE:
        data = simplejson.loads(file(settings.LATEST_TWEETS_FILE).read())[:count]
    else:
        data = utils.latest_tweets(screen_name, count)
    return data

@register.filter
def convert_twitter_links(text, args=None):
    text = re.sub(r'(https?://[^\s]*)', r'<a href="\1">\1</a>', text)
    text = re.sub(r'@([^\s]*)', r'@<a href="http://twitter.com/\1">\1</a>', text)
    text = re.sub(r'([^&])#([^\s]*)', r'\1<a href="http://twitter.com/search?q=%23\2">#\2</a>', text)
    return mark_safe(text)

@register.filter
def user_interest(event, user):
    if not user.is_authenticated():
        return 0
    return models.EventInterest.objects.get_for_user(event, user)

@fancy_tag(register, takes_context=True)
def user_interest(context, event, user=None):
    """
    {% user_interest event [ user ] as var %}
    Restituisce l'interesse di un utente, se manca viene recuperato dalla
    request, per l'evento passato.
    """
    request = context.get('request')
    if user is None:
        if not request:
            raise ValueError('request not found')
        else:
            user = request.user

    if not user.is_authenticated():
        return 0

    try:
        cached = request._user__events_interests
    except AttributeError:
        cached = dict((x['event_id'], x) for x in models.EventInterest.objects.filter(user=user).values())
        request._user__events_interests = cached

    try:
        return cached[event.id]['interest']
    except KeyError:
        return 0

@fancy_tag(register)
def randint():
    return random.randint(0, sys.maxint)

@register.filter
def truncate_chars(text, length):
    if len(text) > length:
        return text[:length-3] + '...'
    else:
        return text

@register.filter
def timetable_columns(timetable):
    """
    Restituisce le colonne di una timetable, ogni elemento ha questo formato:
        (columns, events, collapse)

    events è il numero di TimeTable.Event associati alla colonna
    collapse (True/False) indica se la colonna può essere collassata graficamente
    """
    output = []
    for c in timetable.columns():
        cells = events = flex_times = 0
        for evt in timetable.eventsAtTime(c, include_reference=True):
            cells += 1
            if isinstance(evt, utils.TimeTable.Event):
                events += 1
            elif isinstance(evt, utils.TimeTable.Reference) and evt.flex:
                flex_times += 1
        collapse = cells == flex_times
        output.append((c, events, collapse))
    return output

@fancy_tag(register)
def timetable_cells(timetable, width, height, outer_width=None, outer_height=None, collapse='auto'):
    if outer_width is None:
        outer_width = width
    if outer_height is None:
        outer_height = height
    extra_width = outer_width - width
    extra_height = outer_height - height

    compress_width = 10
    def calc_width(col):
        if not col['collapse']:
            return width
        elif col['events'] == 0:
            return 0
        else:
            return 10

    columns = list(timetable.columns())
    col_pos = [{'time': None, 'pos': 0, 'collapse': False,}]
    next_pos = outer_width
    for c in columns:
        events = {
            'total': 0,
            'reference': 0,
            'flex': 0,
            'special': 0,
            'fixed': 0,
        }
        cells = flex_times = 0
        for evt in timetable.eventsAtTime(c, include_reference=True):
            events['total'] += 1
            if isinstance(evt, utils.TimeTable.Reference):
                if evt.flex:
                    events['flex'] += 1
                if 'break' in evt.evt.ref.track or 'special' in evt.evt.ref.track:
                    events['special'] += 1
                events['reference'] += 1
            else:
                events['fixed'] += 1
        if collapse == 'auto':
            collapse_flag = (events['fixed'] == 0 and events['special'] > 0) or (events['total'] == 0)
        elif collapse == 'always':
            collapse_flag = events['fixed'] == 0
        else:
            collapse_flag = False
        col_pos.append({'time': c, 'pos': next_pos, 'collapse': collapse_flag, 'events': events['total'], })
        next_pos = next_pos + calc_width(col_pos[-1])

    max_size = [0, 0]
    def size(time, row, cols=1, rows=1):
        for ix, _ in enumerate(col_pos):
            if _['time'] == time:
                break
        l = col_pos[ix]['pos']
        t = row * outer_height
        w = 0
        for _ in col_pos[ix:ix+cols]:
            w += calc_width(_)
        w += extra_width * (cols-1)
        h = rows * height
        h += extra_height * (rows-1)
        max_size[0] = max(max_size[0], l+w)
        max_size[1] = max(max_size[1], t+h)
        return "left: %dpx; top: %dpx; width: %dpx; height: %dpx" % (l, t, w, h)

    cells = [{
        'type': '',
        'size': size(None, 0),
    }]
    add = cells.append
    for c in columns:
        add({
            'type': 'hhmm',
            'time': c,
            'size': size(c, 0),
            'events': len(timetable.changesAtTime(c)),
        })

    for irow, _ in enumerate(timetable.byRows()):
        row, cols = _
        add({
            'type': 'track',
            'track': row,
            'size': size(None, irow+1),
        })
        for c in cols:
            evt = {
                'type': 'event',
                'time': c['time'],
                'row': c['row'],
            }
            if c['data'] is None:
                evt['event'] = None
                evt['size'] = size(c['time'], irow+1)
            elif isinstance(c['data'], utils.TimeTable.Event):
                evt['event'] = c['data']
                evt['size'] = size(c['time'], irow+1, cols=c['data'].columns, rows=c['data'].rows)
            else:
                continue
            add(evt)
    return {
        'cells': cells,
        'schedule_size': 'width: %dpx; height: %dpx' % (max_size[0], max_size[1]),
    }

@fancy_tag(register, takes_context=True)
def render_fb_like(context, href=None, ref="", show_faces="true", width="100%", action="recommend", font="", colorscheme="light"):
    if not href:
        href = context['CURRENT_URL']
    data = dict(locals())
    data.pop('context')
    ctx = Context(context)
    ctx.update(data)
    return render_to_string('conference/render_fb_like.html', ctx)

@register.filter
def name_abbrv(name):
    whitelist = set(('de', 'di', 'van', 'mc', 'mac', 'le', 'cotta'))

    splitted = name.split(' ')
    if len(splitted) == 1:
        return name

    last_name = splitted[-1]
    if splitted[-2].lower() in whitelist:
        last_name = splitted[-2] + ' ' + last_name

    return '%s. %s' % (name[0], last_name)

@register.filter
def main_event(events):
    for e in events:
        if not 'teaser' in e.tags:
            return e

@register.filter
def teaser_event(events):
    for e in events:
        if event_has_track(e, 'teaser'):
            return e

@fancy_tag(register, takes_context=True)
def get_talk_speakers(context, talk):
    c = _request_cache(context['request'], 'talk_speakers_%s' % talk.conference)
    if not c:
        c['items'] = models.TalkSpeaker.objects.speakers_by_talks(talk.conference)
    return c['items'].get(talk.id, [])


@fancy_tag(register, takes_context=True)
def current_events(context, time=None):
    if time is None:
        time = datetime.now()
    try:
        schedule = models.Schedule.objects.get(date=time.date())
    except Schedule.DoesNotExist:
        return {}
    output = {}
    tt = schedule_timetable(context, schedule)
    for col in tt.byTimes():
        if col[0] > time.time():
            break
        output = dict(
            (r['row'], r['data']) for r in col[1]
        )
    else:
        output = {}
    return output

@fancy_tag(register, takes_context=True)
def next_events(context, time=None):
    if time is None:
        time = datetime.now()
    try:
        schedule = models.Schedule.objects.get(date=time.date())
    except Schedule.DoesNotExist:
        return {}
    found = {}
    output = {}
    tt = schedule_timetable(context, schedule)
    for col in tt.byTimes():
        if col[0] >= time.time():
            for item in col[1]:
                row = item['row']
                data = item['data']
                if row in found and found[row] is None:
                    continue
                if data:
                    if hasattr(data, 'evt'):
                        data = data.evt.ref
                    else:
                        data = data.ref
                if data != found.get(row):
                    output[row] = item['data']
                    found[row] = None
            if not any(found.values()):
                break
        else:
            found = {}
            for item in col[1]:
                row = item['row']
                data = item['data']
                if data:
                    if hasattr(data, 'evt'):
                        data = data.evt.ref
                    else:
                        data = data.ref
                found[row] = data

    return output

@fancy_tag(register)
def current_conference():
    return models.Conference.objects.current()

@fancy_tag(register, takes_context=True)
def render_schedule_list(context, conference, exclude_tags=None, exclude_tracks=None):
    ctx = Context(context)

    events = dataaccess.events(conf=conference)
    if exclude_tags:
        exclude = set(exclude_tags.split(','))
        events = filter(lambda x: len(x['tags'] & exclude) == 0, events)

    if exclude_tracks:
        exclude = set(exclude_tracks.split(','))
        events = filter(lambda x: len(set(x['tracks']) & exclude) == 0, events)

    grouped = defaultdict(list)
    for e in events:
        grouped[e['time'].date()].append(e)
    ctx.update({
        'conference': conference,
        'events': sorted(grouped.items()),
    })
    return render_to_string('conference/render_schedule_list.html', ctx)

@register.filter
def markdown2(text, arg=''):
    from markdown2 import markdown
    extensions = [e for e in arg.split(",") if e]
    if len(extensions) > 0 and extensions[0] == "nosafe":
        extensions = extensions[1:]
        safe_mode = None
    else:
        safe_mode = "escape"

    return mark_safe(markdown(text, safe_mode=safe_mode, extras=extensions))

@fancy_tag(register, takes_context=True)
def tagged_items(context, tag):
    return dataaccess.tags().get(tag, {})

@fancy_tag(register)
def talk_data(tid):
    return dataaccess.talk_data(tid)

@fancy_tag(register)
def talks_data(tids):
    return dataaccess.talks_data(tids)

@fancy_tag(register)
def schedule_data(sid):
    return dataaccess.schedule_data(sid)

@fancy_tag(register)
def schedules_data(sids):
    return dataaccess.schedules_data(sids)

@register.filter
def content_type(id):
    return ContentType.objects.get(id=id)

@register.filter
def field_label(value, fieldpath):
    mname, fname = fieldpath.split('.')
    model = getattr(models, mname)
    field = model._meta.get_field_by_name(fname)[0]
    for k, v in field.choices:
        if k == value:
            return v
    return None

@fancy_tag(register)
def admin_urlname_fromct(ct, action, id=None):
    r = 'admin:%s_%s_%s' % (ct.app_label, ct.model, action)
    if id is None:
        args = ()
    else:
        args = (str(id),)
    try:
        return reverse(r, args=args)
    except:
        return None

@fancy_tag(register)
def profile_data(uid):
    return dataaccess.profile_data(uid)

@fancy_tag(register)
def profiles_data(uids):
    return dataaccess.profiles_data(uids)

@register.filter
def beautify_url(url):
    """
    Elimina il protocollo dalla url e nel caso sia solo un hostname anche lo /
    finale
    """
    try:
        ix = url.index('://')
    except ValueError:
        pass
    else:
        url = url[ix+3:]
    if url.endswith('/') and url.index('/') == len(url)-1:
        url = url[:-1]
    return url

@register.filter
def ordered_talks(talks, criteria="conference"):
    """
    raggruppa i talk per conferenza
    """
    if not talks:
        return []
    if isinstance(talks[0], int):
        talks = dataaccess.talks_data(talks)
    grouped = defaultdict(list)
    for t in talks:
        grouped[t['conference']].append(t)
    return sorted(grouped.items(), reverse=True)

@fancy_tag(register)
def visible_talks(talks, filter_="all"):
    """
    Filtra l'elenco di talk in base a filter_:
        * "all" ritorna tutti i talk
        * "accepted" ritorna solo i talk accettati
        * "conference" ritorna tutti i talk presentati alla conferenza corrente
          (oltre a quelli accettati presentati nelle conferenze precedenti)
    """
    if not talks or filter_=="all":
        return talks
    if isinstance(talks[0], int):
        talks = dataaccess.talks_data(talks)
    if filter_ == "accepted":
        return filter(lambda x: x['status'] == 'accepted', talks)
    else:
        return  filter(lambda x: x['status'] == 'accepted' or x['conference'] == settings.CONFERENCE, talks)

@fancy_tag(register, takes_context=True)
def olark_chat(context):
    # se non esiste il settaggio scoppio felice
    key = dsettings.CONFERENCE_OLARK_KEY
    # blob from: https://www.olark.com/install
    blob = """
<!-- begin olark code --><script type='text/javascript'>/*{literal}<![CDATA[*/
window.olark||(function(c){var f=window,d=document,l=f.location.protocol=="https:"?"https:":"http:",z=c.name,r="load";var nt=function(){f[z]=function(){(a.s=a.s||[]).push(arguments)};var a=f[z]._={},q=c.methods.length;while(q--){(function(n){f[z][n]=function(){f[z]("call",n,arguments)}})(c.methods[q])}a.l=c.loader;a.i=nt;a.p={0:+new Date};a.P=function(u){a.p[u]=new Date-a.p[0]};function s(){a.P(r);f[z](r)}f.addEventListener?f.addEventListener(r,s,false):f.attachEvent("on"+r,s);var ld=function(){function p(hd){hd="head";return["<",hd,"></",hd,"><",i,' onl' + 'oad="var d=',g,";d.getElementsByTagName('head')[0].",j,"(d.",h,"('script')).",k,"='",l,"//",a.l,"'",'"',"></",i,">"].join("")}var i="body",m=d[i];if(!m){return setTimeout(ld,100)}a.P(1);var j="appendChild",h="createElement",k="src",n=d[h]("div"),v=n[j](d[h](z)),b=d[h]("iframe"),g="document",e="domain",o;n.style.display="none";m.insertBefore(n,m.firstChild).id=z;b.frameBorder="0";b.id=z+"-loader";if(/MSIE[ ]+6/.test(navigator.userAgent)){b.src="javascript:false"}b.allowTransparency="true";v[j](b);try{b.contentWindow[g].open()}catch(w){c[e]=d[e];o="javascript:var d="+g+".open();d.domain='"+d.domain+"';";b[k]=o+"void(0);"}try{var t=b.contentWindow[g];t.write(p());t.close()}catch(x){b[k]=o+'d.write("'+p().replace(/"/g,String.fromCharCode(92)+'"')+'");d.close();'}a.P(2)};ld()};nt()})({loader: "static.olark.com/jsclient/loader0.js",name:"olark",methods:["configure","extend","declare","identify"]});
/* custom configuration goes here (www.olark.com/documentation) */
olark.identify('%s');/*]]>{/literal}*/</script>
<!-- end olark code -->
    """ % key
    user = context['request'].user
    if user.is_authenticated():
        from django.template.defaultfilters import escapejs
        name = '%s %s' % (user.first_name, user.last_name)
        blob += '''
<script type="text/javascript">
    olark('api.chat.updateVisitorNickname', {snippet: '%s'})</script>
''' % (escapejs(name),)

    return blob

@register.filter
def json_(val):
    from conference.views import json_dumps
    return mark_safe(json_dumps(val))
