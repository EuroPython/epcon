# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import mimetypes
import os
import os.path
import re
from django import template
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils.html import escape

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

        dlang = settings.LANGUAGES[0][0]
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
        query = PagesModels.Page.objects.navigation().order_by('tree_id', 'lft')
        query = query.filter(tags__contains = self.page_type)
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
            if self.var_name:
                context[self.var_name] = (ftype, fsize)
                return ''
            else:
                return "(%s %s)" % (ftype, fsize)
            
    return StuffInfoNode(fpath, var_name)

@register.tag
def conference_speakers(parser, token):
    """
    {% conference_speakers [ conference ] as var %}
    inserisce in var l'elenco degli speaker (opzionalmente è possibile
    filtrare per conferenza).
    """
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    if len(contents) > 3:
        conference = contents[1]
        raise template.TemplateSyntaxError("conference params not yet supported")
    else:
        conference = None
    
    class SpeakersNode(template.Node):
        def __init__(self, conference, var_name):
            self.var_name = var_name
            if conference:
                if conference.startswith('"') and conference.endswith('"'):
                    self.conference = conference[1:-1]
                else:
                    self.conference = template.Variable(conference)
            else:
                self.conference = None
        def render(self, context):
            speakers = models.Speaker.objects.all()
            context[self.var_name] = speakers
            return ''
    return SpeakersNode(conference, var_name)

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
    {% conference_talks [ speaker ] [ conference ] as var %}
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
    if contents:
        speaker = contents.pop(0)
    if contents:
        conference = contents.pop(0)
    if contents:
        tags = contents.pop(0)

    
    class TalksNode(TNode):
        def __init__(self, speaker, conference, tags, var_name):
            self.var_name = var_name
            self.speaker = self._set_var(speaker)
            self.conference = self._set_var(conference)
            self.tags = self._set_var(tags)
        
        def render(self, context):
            talks = models.Talk.objects.all()
            speaker = self._get_var(self.speaker, context)
            tags = self._get_var(self.tags, context)
            conference = self._get_var(self.conference, context)
            if speaker:
                talks = talks.filter(speakers = speaker)
            if tags:
                talks = TaggedItem.objects.get_by_model(talks, tags)
            context[self.var_name] = talks
            return ''
    return TalksNode(speaker, conference, tags, var_name)

@register.inclusion_tag('conference/render_schedule.html')
def render_schedule(schedule):
    """
    {% render_schedule schedule %}
    """
    from collections import defaultdict
    from datetime import time

    if isinstance(schedule, int):
        schedule = models.Schedule.objects.get(pk = schedule)
    elif isinstance(schedule, basestring):
        try:
            c, s = schedule.split('/') 
        except ValueError:
            raise template.TemplateSyntaxError('%s is not in the form of conference/slug' % schedule)
        schedule = models.Schedule.objects.get(conference = c, slug = s)

    TIME_STEP = 15
    dbtracks = dict((t.track, (ix, t)) for ix, t in enumerate(schedule.track_set.all()))
    _itracks = dict(dbtracks.values())
    dbevents = defaultdict(list)
    for e in schedule.event_set.all():
        dbevents[e.start_time].append(e)

    eevent = lambda t: { 'time': t, 'title': '', 'track_slots': 1, 'time_slots': 1, 'talk': None, 'tags': [] }

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
                # allocati più solt temporali di quelli individuati
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
            delta = next.hour * 60 + next.minute - (t.hour * 60 + t.minute)
            steps = delta / TIME_STEP
        for x in range(steps - 1):
            timetable.insert(ix+1+offset, (None, None))
        offset += steps - 1
        
    return {
        'schedule': schedule,
        'timetable': timetable,
    }

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
    {% conference_sponsor [ conference ] as var %}
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

    class SponsorNode(TNode):
        def __init__(self, conference, var_name):
            self.var_name = var_name
            self.conference = self._set_var(conference)

        def render(self, context):
            sponsor = models.Sponsor.objects.all()
            conference = self._get_var(self.conference, context)
            if conference:
                sponsor = sponsor.filter(sponsorincome__conference = conference)
                sponsor = sponsor.order_by('-sponsorincome__income', 'sponsor')
            context[self.var_name] = sponsor
            return ''
    return SponsorNode(conference, var_name)

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
            tpl = self.arg.resolve(context)
            t = template.Template(tpl)
            data = t.render(context)
            if self.var_name:
                context[self.var_name] = data
                return ''
            else:
                return data
            
    return TemplateRenderer(arg, var_name)

@register.tag
def conference_multilingual_attribute(parser, token):
    """
    {% conference_multilingual_attribute object attribute [as var] %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        instance, attribute = contents[1:3]
    except ValueError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    if contents[-2] == 'as':
        var_name = contents[-1]
    else:
        var_name = None

    class AttributeNode(TNode):
        def __init__(self, instance, attribute, var_name):
            self.var_name = var_name
            self.instance = self._set_var(instance)
            self.attribute = self._set_var(attribute)
        
        def render(self, context):
            instance = self._get_var(self.instance, context)
            attribute = self._get_var(self.attribute, context)
            try:
                query = getattr(instance, attribute)
            except AttributeError:
                return ''

            try:
                value = query.get(language = context['LANGUAGE_CODE'])
            except ObjectDoesNotExist:
                value = None
            if self.var_name:
                context[self.var_name] = value
                return ''
            else:
                return value
    return AttributeNode(instance, attribute, var_name)

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
    {% render_schedule hotels %}
    """
    return {
        'hotels': hotels,
    }
