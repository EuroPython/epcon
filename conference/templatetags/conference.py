# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import mimetypes
import os
import os.path
import re
import httplib2
import simplejson
from django import template
from django.conf import settings as dsettings
from django.core.exceptions import ObjectDoesNotExist
from django.template import defaultfilters
from django.utils.html import escape
from django.utils.safestring import mark_safe

from conference import settings
from conference.settings import MIMETYPE_NAME_CONVERSION_DICT as mimetype_conversion_dict
from conference import models
from pages import models as PagesModels

from tagging.models import Tag, TaggedItem

mimetypes.init()

register = template.Library()

class LatestDeadlinesNode(template.Node):
    """
    Inserisce in una variabile di contesto le deadlines presenti.
    Opzionalmente e' possibile specificare quante deadline si vogliono.

    Le deadline vengono riportate nella lingua dell'utente con un fallback
    nella lingua di default.
    """
    def __init__(self, limit, var_name):
        self.limit = limit
        self.var_name = var_name

    def render(self, context):
        query = models.Deadline.objects.valid_news()
        if self.limit:
            query = query[:self.limit]

        dlang = dsettings.LANGUAGES[0][0]
        lang = context.get('LANGUAGE_CODE', dlang)
        # le preferenze per la lingua sono:
        #   1. lingua scelta dall'utente
        #   2. lingua di default
        #   3. lingue in cui e' tradotta la deadline
        #
        # Se la traduzione di una deadline è vuota viene scartata
        # e provo la lingua successiva.
        # Se la deadline non ha alcuna traduzione (!) la scarto.
        news = []
        for n in query:
            contents = dict((c.language, c) for c in n.deadlinecontent_set.all())

            lang_try = (lang, dlang) + tuple(contents.keys())
            for l in lang_try:
                try:
                    content = contents[l]
                except KeyError:
                    continue
                if content.body:
                    break
            else:
                continue
            news.append((n.date, content.body))
        context[self.var_name] = news
        return ""

@register.tag
def latest_deadlines(parser, token):
    contents = token.split_contents()
    tag_name = contents[0]
    limit = None
    try:
        if contents[1] != 'as':
            try:
                limit = int(contents[1])
            except (ValueError, TypeError):
                raise template.TemplateSyntaxError("%r tag's argument should be an integer" % tag_name)
        else:
            limit = None
        if contents[-2] != 'as':
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
        var_name = contents[-1]
    except IndexError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    return LatestDeadlinesNode(limit, var_name)

class NaviPages(template.Node):
    def __init__(self, page_type, var_name):
        self.page_type = page_type
        self.var_name = var_name

    def render(self, context):
        request = context['request']
        query = PagesModels.Page.objects.published().order_by('tree_id', 'lft')
        query = query.filter(tags__name__in=[self.page_type])
        context[self.var_name] = query
        return ''

def navi_pages(parser, token):
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    return NaviPages(tag_name.split('_')[1], var_name)

register.tag('navi_menu1_pages', navi_pages)
register.tag('navi_menu2_pages', navi_pages)
register.tag('navi_menu3_pages', navi_pages)

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
                fpath = os.path.join(settings.STUFF_DIR, fpath)
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
    from collections import defaultdict
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
        schedule = models.Schedule.objects.get(pk = schedule)
    elif isinstance(schedule, basestring):
        try:
            c, s = schedule.split('/')
        except ValueError:
            raise template.TemplateSyntaxError('%s is not in the form of conference/slug' % schedule)
        schedule = models.Schedule.objects.get(conference = c, slug = s)

    return {
        'schedule': schedule,
        'timetable': schedule_context(schedule),
        'SPONSOR_LOGO_URL': context['SPONSOR_LOGO_URL'],
    }

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
def split(value, arg):
    return value.split(arg)

@register.filter
def splitonspace(value):
    return value.split(' ')

@register.filter
def image_resized(value):
    return 'resized/' + os.path.splitext(str(value))[0] + '.jpg'

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

@register.tag
def conference_sponsor(parser, token):
    """
    {% conference_sponsor [conference [[exclude] tag]] as var %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    contents = contents[1:-2]

    conference = None
    include_tag = None
    exclude_tag = None

    lc = len(contents)
    if 0 < lc <= 3:
        conference = contents.pop(0)
        if lc == 2:
            include_tag = contents.pop(0)
        elif lc ==3:
            if contents[0] != 'exclude':
                raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
            else:
                contents.pop(0)
                exclude_tag = contents.pop(0)
    elif lc:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    class SponsorNode(TNode):
        def __init__(self, conference, include_tag, exclude_tag, var_name):
            self.var_name = var_name
            self.conference = self._set_var(conference)
            self.include_tag = self._set_var(include_tag)
            self.exclude_tag = self._set_var(exclude_tag)

        def render(self, context):
            sponsor = models.Sponsor.objects.all()
            conference = self._get_var(self.conference, context)
            if conference:
                sponsor = sponsor.filter(sponsorincome__conference = conference)
            include_tag = self._get_var(self.include_tag, context)
            if include_tag:
                q = TaggedItem.objects.get_by_model(models.SponsorIncome, include_tag)
                sponsor = sponsor.filter(sponsorincome__in = q)
            exclude_tag = self._get_var(self.exclude_tag, context)
            if exclude_tag:
                q = TaggedItem.objects.get_by_model(models.SponsorIncome, exclude_tag)
                sponsor = sponsor.exclude(sponsorincome__in = q)
            sponsor = sponsor.order_by('-sponsorincome__income', 'sponsor')
            context[self.var_name] = sponsor
            return ''
    return SponsorNode(conference, include_tag, exclude_tag, var_name)

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

@register.filter
def embed_video(value, args=None):
    """
    {{ talk|embed_video:"width,height" }}
    """
    tmap = {
        'viddler_oembed': ('oEmbed', 'http://lab.viddler.com/services/oembed/'),
        'download': ('download', None),
    }
    if args:
        w, h = map(int, args.split(','))
    else:
        w = h = None
    vtype, burl = tmap.get(value.video_type, tmap['download'])
    if vtype == 'oEmbed':
        http = httplib2.Http()
        url = burl + '?url=' + value.video_url + '&format=json'
        if w and h:
            url += '&width=%s&height=%s&maxwidth=%s&maxheight=%s' % (w, h, w, h)
        try:
            response, content = http.request(url)
            data = simplejson.loads(content)
        except:
            # Qualsiasi cosa succeda, che non riesca a connettermi a burl o che
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
        src = fpath = None
        if value.video_file or settings.VIDEO_DOWNLOAD_FALLBACK:
            if value.video_file:
                src = settings.STUFF_URL + 'videos/' + value.video_file.name
                fpath = os.path.join(settings.STUFF_DIR, 'videos', value.video_file.name)
            else:
                for ext in ('.avi', '.mp4'):
                    fpath = os.path.join(settings.STUFF_DIR, 'videos', value.slug + ext)
                    if os.path.exists(fpath):
                        src = settingsSTUFF_URL + 'videos/' + value.slug + ext
                        break
        if not src:
            html = ''
        else:
            try:
                stat = os.stat(fpath)
            except (AttributeError, OSError), e:
                finfo = ''
            else:
                fsize = stat.st_size
                ftype = mimetypes.guess_type(fpath)[0]
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
                'href': src,
                'info': finfo,
            }

            html = """
                <div>
                    <video %(attrs)s>
                        <source src="%(href)s" />
                    </video>
                    <a href="%(href)s">download video%(info)s</a>
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
